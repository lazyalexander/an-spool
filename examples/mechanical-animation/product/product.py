"""Teaching example only: domain sequencing over the existing daemon client."""

import argparse
import hashlib
import json
import secrets
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pack import build
from support.daemon_client import DaemonClient
from support.local_page import serve_application

HERE = Path(__file__).resolve().parent
STAGES = ["mechanism", "appearance", "mechanical-film"]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def invoke(host, *args):
    result = subprocess.run(
        [str(host), *map(str, args)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return json.loads(result.stdout)


def inventory(site):
    files = {}
    for p in sorted(site.rglob("*")):
        if p.is_symlink():
            raise ValueError("Runtime site must contain no symbolic links")
        if p.is_file():
            files[p.relative_to(site).as_posix()] = hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
    return hashlib.sha256(
        json.dumps(
            files, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode()
    ).hexdigest()


def prepare(args):
    root = args.root.resolve()
    root.mkdir(mode=0o700, exist_ok=False)
    packages = build(root / "packages")
    host, python, site, stdlib = [
        p.resolve(strict=True) for p in (args.host, args.python, args.site, args.stdlib)
    ]
    config = {
        "host": str(host),
        "service": str(root / "service"),
        "cases": {},
        "node": str(args.node.resolve(strict=True)),
        "shuttle": str(args.shuttle.resolve(strict=True)),
        "shuttle_sha256": hashlib.sha256(args.shuttle.read_bytes()).hexdigest(),
    }
    invoke(host, "daemon", "init", root / "service", 1)
    invoke(host, "daemon", "launchd", root / "service", root / "agent.plist")
    site_hash = inventory(site)
    for case in args.cases:
        config["cases"][case] = {}
        for name in STAGES:
            base = root / f"{case}-{name}"
            fixture = args.fixtures.resolve(strict=True) / f"{case}-inputs"
            runtime = {
                "schema": "an-native-python-runtime-v1",
                "executable": str(python),
                "executable_sha256": hashlib.sha256(python.read_bytes()).hexdigest(),
                "stdlib": str(stdlib),
                "site": str(site),
                "site_sha256": site_hash,
                "dependencies": json.loads(
                    (packages / name / "native-spool.json").read_text()
                )["requirements"]["dependencies"],
                "readonly": [
                    str(Path(p).resolve(strict=True))
                    for p in [
                        "/opt/homebrew",
                        "/Applications/FreeCAD.app",
                        "/Applications/Blender.app",
                    ]
                ],
                "inputs": [
                    str((fixture / f).resolve(strict=True))
                    for f in [
                        "config.json",
                        "scene.blend",
                        "atlas.png",
                        "background.png",
                    ]
                ]
                if name == "appearance"
                else [],
            }
            if name == "mechanical-film":
                runtime["graphics"] = "macos-agx-metal-v1"
            runtime_path = root / f"{case}-{name}.runtime.json"
            runtime_path.write_text(json.dumps(runtime))
            invoke(host, "spool-load", packages / name, base, "--runtime", runtime_path)
            config["cases"][case][name] = {
                "instance": str(base),
                "run": f"{case}-{name}",
                "seconds": 900 if name == "mechanical-film" else 300,
            }
        (root / f"{case}.json").write_text(json.dumps({"case": case}))
    (root / "application.json").write_text(json.dumps(config, indent=2))
    print(
        json.dumps(
            {
                "prepared": str(root),
                "service": config["service"],
                "automatic_start": False,
            }
        )
    )


class Application(DaemonClient):
    def __init__(self, root):
        self.root = root.resolve(strict=True)
        if self.root.stat().st_mode & 0o077:
            raise ValueError("Application root must be private")
        self.config = json.loads((root / "application.json").read_text())
        self.host = Path(self.config["host"])
        for stages in self.config["cases"].values():
            for stage in stages.values():
                self.request({"op": "register", "instance": stage["instance"]})

    def view(self):
        snapshot = self.request({"op": "show"})
        return {
            "cases": self.config["cases"],
            "snapshot": snapshot,
            "observation_url": json.loads(
                (Path(self.config["service"]) / "endpoint.json").read_text()
            )["url"],
        }

    def plan(self, case, name, operation):
        stage = self.config["cases"][case][name]
        common = {"instance": stage["instance"], "run": stage["run"]}
        if operation == "start":
            req = dict(op="submit", **common, seconds=stage["seconds"])
            index = STAGES.index(name)
            if index:
                prev = self.config["cases"][case][STAGES[index - 1]]
                output = "geometry.zip" if index == 1 else "appearance.zip"
                source = invoke(
                    self.host,
                    "spool-artifacts",
                    prev["instance"],
                    prev["run"],
                    "--output",
                    output,
                )
                binding = source["output"]["binding"]
                catalog = Path(source["catalog"])
                req["artifact"] = {
                    "catalog": str(catalog),
                    "revision": binding["revision"],
                }

            else:
                req["input"] = str(self.root / f"{case}.json")
            permission = {
                "kind": "run",
                **common,
                "seconds": stage["seconds"],
            }
            if index:
                permission.update(kind="run-artifact", **req["artifact"])
            else:
                permission["input"] = req["input"]
        elif operation == "accept":
            req = {"op": "accept", **common}
            permission = {"kind": "accept", **common}
        elif operation in ("pause", "resume", "unload"):
            req = {"op": operation, "instance": stage["instance"]}
            return {"request": req, "native": self.request(req)}
        elif operation == "cancel":
            tasks = self.request({"op": "show"})["tasks"]
            task = next(
                t
                for t in tasks
                if t.get("instance") == stage["instance"]
                and t.get("run") == stage["run"]
            )
            req = {"op": "cancel", "id": task["id"]}
            return {"request": req, "native": self.request(req)}
        elif operation == "krita" and name == "mechanical-film":
            selected = invoke(
                self.host,
                "spool-artifacts",
                stage["instance"],
                stage["run"],
                "--output",
                "painting.ora",
            )
            return {
                "delivery": selected,
                "case": case,
                "stage": stage,
                "shuttle_sha256": self.config["shuttle_sha256"],
            }
        else:
            raise ValueError("Unsupported teaching action")
        # Expiry chosen only at execution so a read preview does not age the digest.
        scope = {
            "task": f"teaching-{case}",
            "subject": name,
            "delegate": False,
            "permissions": [permission],
        }
        return {"request": req, "scope": scope, "native": self.request(req)}

    def act(self, request):
        plan = self.plan(request["case"], request["stage"], request["operation"])
        identity = digest(plan)
        if "approve" not in request:
            return {"approval_sha256": identity, "plan": plan}
        if request["approve"] != identity:
            raise ValueError("Inputs or authority changed; review a new preview")
        if "delivery" in plan:
            cli = Path(self.config["shuttle"])
            if (
                hashlib.sha256(cli.read_bytes()).hexdigest()
                != self.config["shuttle_sha256"]
            ):
                raise ValueError("Selected Shuttle entry changed")
            target = (
                self.root / f"{request['case']}-reference-{secrets.token_hex(6)}.ora"
            )
            return invoke(
                self.config["node"],
                cli,
                self.host,
                plan["stage"]["instance"],
                plan["stage"]["run"],
                target,
            )
        return self.execute_plan(plan)


def serve(root):
    serve_application(Application(root), root, HERE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    for key in [
        "root",
        "host",
        "python",
        "site",
        "stdlib",
        "fixtures",
        "node",
        "shuttle",
    ]:
        p.add_argument("--" + key, type=Path, required=True)
    p.add_argument(
        "--cases", nargs="+", choices=["steam", "inline4"], default=["steam", "inline4"]
    )
    p = sub.add_parser("serve")
    p.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args)
    else:
        serve(args.root)
