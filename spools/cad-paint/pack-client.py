"""Package a verified Loom release for npm clients without running package hooks."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import tarfile
import tomllib

PROJECT = Path(__file__).resolve().parent


def result(*command, cwd=None):
    return json.loads(subprocess.check_output(command, cwd=cwd, text=True))


def payload(archive):
    with tarfile.open(archive) as release:
        files = {}
        for entry in release:
            if not entry.isfile() or entry.name in files:
                raise ValueError(f"Unexpected client member: {entry.name}")
            files[entry.name] = (entry.mode, release.extractfile(entry).read())
        return files


def build(loom, tsc, output, check):
    archive = Path(result(loom, "pack", PROJECT)["archive"])
    bundle = result(loom, "verify", archive)
    metadata = (PROJECT / "package.json").read_bytes()
    if json.loads(metadata)["version"] != bundle["package"]["version"]:
        raise ValueError("npm and Loom package versions must match")
    if subprocess.check_output([tsc, "--version"], text=True).strip() != "Version 5.9.3":
        raise ValueError("Use TypeScript 5.9.3 to reproduce this distribution")
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.resolve() if not check else None) as tmp:
        root = Path(tmp) / "package"
        root.mkdir()
        with tarfile.open(archive) as release:
            release.extractall(root, filter="data")
        (root / "package.json").write_bytes(metadata)
        dist = root / "dist"
        dist.mkdir()
        shutil.copyfile(archive, dist / "cad-paint.loom.tar.gz")
        pins = tomllib.loads((root / "native-spool.toml").read_text())["dependencies"]
        (dist / "requirements.txt").write_text("".join("==".join(pin.rsplit("-", 1)) + "\n" for pin in pins))
        subprocess.run([tsc, "--target", "ES2022", "--module", "NodeNext", "--strict",
                        "--declaration", "--outDir", dist, "agent.ts"], cwd=root, check=True)
        filename = result("npm", "pack", "--json", "--ignore-scripts", "--pack-destination", tmp, cwd=root)[0]["filename"]
        candidate = Path(tmp) / filename
        target = output / filename
        if check:
            if not target.is_file() or payload(target) != payload(candidate):
                raise ValueError(f"Published client files differ from the verified source: {target.name}")
        else:
            try:
                os.link(candidate, target)
            except FileExistsError:
                if target.read_bytes() != candidate.read_bytes():
                    raise ValueError(f"Existing version differs: {target.name}")
        print(f"{target.name}  Loom release {bundle['releaseDigest']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loom", required=True, type=Path)
    parser.add_argument("--tsc", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="Compare the existing distribution without writing it")
    args = parser.parse_args()
    build(args.loom.resolve(strict=True), args.tsc.resolve(strict=True), args.output, args.check)
