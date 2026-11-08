"""Finite real-host qualification of the three reviewed mechanical source packages."""

import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--host", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
parser.add_argument("--fixtures", type=Path, required=True)
parser.add_argument("--python-runtime", type=Path, required=True)
parser.add_argument("--python-site", type=Path, required=True)
parser.add_argument(
    "cases", nargs="*", choices=["steam", "inline4"], default=["steam", "inline4"]
)
options = parser.parse_args()
HOST = options.host.resolve(strict=True)
EVIDENCE = options.evidence.resolve()
EVIDENCE.mkdir(exist_ok=False)
JOURNAL = []


def call(*args):
    p = subprocess.run([str(HOST), *map(str, args)], capture_output=True, text=True)
    JOURNAL.append(
        {
            "args": list(map(str, args)),
            "exit": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
        }
    )
    (EVIDENCE / "commands.local.json").write_text(json.dumps(JOURNAL, indent=2))
    if p.returncode:
        raise RuntimeError(p.stderr or p.stdout)
    return json.loads(p.stdout)


def approved(*args):
    preview = call(*args)
    return call(*args, "--approve", preview["approval_sha256"])


def stage(case, name, inputs, args, outputs, pins=(), graphics=False):
    folder = EVIDENCE / (case + "-" + name)
    profile = {
        "schema": "an-workspace-job-v2",
        "executable": str(Path("/opt/homebrew/bin/python3").resolve()),
        "args": args,
        "environment": {},
        "readonly": [
            "/opt/homebrew",
            "/Applications/FreeCAD.app",
            "/Applications/Blender.app",
        ],
        "inputs": list(map(str, inputs)),
        "outputs": outputs,
        "binary_outputs": [n for n in outputs if n != "report.json"],
        "wall_seconds": 900 if graphics else 300,
        "trusted_process_group": True,
    }
    if name == "mechanism":
        profile["executable"] = str(options.python_runtime.resolve(strict=True))
        profile["readonly"].append(str(options.python_site.resolve(strict=True)))
        profile["environment"]["PYTHONPATH"] = str(
            options.python_site.resolve(strict=True)
        )
    if graphics:
        profile["graphics"] = "macos-agx-metal-v1"
    if pins:
        profile["artifact_inputs"] = list(pins)
    path = EVIDENCE / (case + "-" + name + ".profile.local.json")
    path.write_text(json.dumps(profile))
    receipt = approved("workspace-run", path, folder)
    assert receipt["termination_confirmed"] and receipt["reaped"]
    acceptance = approved("workspace-accept", folder, receipt["attempt"])
    (EVIDENCE / (case + "-" + name + ".accepted.json")).write_text(
        json.dumps(acceptance, indent=2)
    )
    return folder, acceptance


def checkout(job, acceptance, name, target):
    item = next(item for item in acceptance["outputs"] if item["path"] == name)
    revision = item["binding"]["revision"]
    catalog = job / "artifacts"
    call("artifact-checkout", catalog, revision, target)
    return {"path": str(target), "catalog": str(catalog), "revision": revision}


for case in options.cases:
    source = ROOT / "spools/mechanism"
    archive = max(
        (source / "dist/artifacts").glob("*.tar.gz"), key=lambda p: p.stat().st_mtime
    )
    job, accepted = stage(
        case,
        "mechanism",
        [source / "source/run.py", archive],
        ["{input:0}", "{input:1}", case],
        ["geometry.zip", "report.json"],
    )
    geometry = EVIDENCE / (case + "-geometry.zip")
    pin = checkout(job, accepted, "geometry.zip", geometry)
    inputs = options.fixtures.resolve() / (case + "-inputs")
    job, accepted = stage(
        case,
        "appearance",
        [
            ROOT / "spools/appearance/source/run.py",
            geometry,
            inputs / "config.json",
            inputs / "scene.blend",
            inputs / "atlas.png",
            inputs / "background.png",
        ],
        ["{input:0}", *["{input:" + str(i) + "}" for i in range(1, 6)]],
        ["appearance.zip", "report.json"],
        [pin],
    )
    appearance = EVIDENCE / (case + "-appearance.zip")
    pin = checkout(job, accepted, "appearance.zip", appearance)
    code = ROOT / "spools/mechanical-film/source"
    job, accepted = stage(
        case,
        "film",
        [code / "run.py", appearance, code / "kit.py", code / "blender_worker.py"],
        ["{input:0}", "{input:1}"],
        ["film.mp4", "editable.blend", "report.json"],
        [pin],
        True,
    )
    print(case, "THREE_SPOOL_CHAIN_ACCEPTED", flush=True)
