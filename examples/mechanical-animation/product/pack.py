"""Build native envelopes from immutable teaching releases; never grant execution."""

import argparse
import hashlib
import json
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def build(output):
    output.mkdir(exist_ok=False)
    releases = json.loads((ROOT / "teaching-releases.json").read_text())["releases"]
    for item in releases:
        name = item["name"]
        archive = ROOT / item["distribution"]
        if (
            hashlib.sha256(archive.read_bytes()).hexdigest()
            != item["distribution_sha256"]
        ):
            raise ValueError("Teaching release distribution changed")
        folder = output / name
        silk = folder / "silk"
        silk.mkdir(parents=True)
        with tarfile.open(archive) as release:
            payload = {
                entry.name: release.extractfile(entry).read()
                for entry in release
                if entry.isfile()
            }
        (silk / "AGENTS.md").write_bytes(payload["AGENTS.md"])
        (silk / "run.py").write_bytes(payload["source/run.py"])
        if name == "mechanism":
            shutil.copy2(archive, silk / "source.tar.gz")
            body = "sys.argv = ['run.py', str(code/'source.tar.gz'), json.loads(Path(os.environ['AN_SPOOL_INPUT']).read_text())['case']]"
            outputs = ["geometry.zip", "report.json"]
            dependencies = ["numpy"]
        elif name == "appearance":
            body = "sys.argv = ['run.py', os.environ['AN_SPOOL_INPUT'], *[os.environ[f'AN_SPOOL_AUX_{i}'] for i in range(4)]]"
            outputs = ["appearance.zip", "report.json"]
            dependencies = []
        else:
            for part in ["kit.py", "blender_worker.py"]:
                (silk / part).write_bytes(payload["source/" + part])
            cad = ROOT / "spools/cad-paint/releases/an-loom-cad-paint-spool-0.1.0.tgz"
            if (
                hashlib.sha256(cad.read_bytes()).hexdigest()
                != "e1664cb91fceabc6049396509c3a01c17f81fd3b245a180e3b115dee33cf3144"
            ):
                raise ValueError("Selected CAD OpenRaster release changed")
            with tarfile.open(cad) as release:
                (silk / "ora.py").write_bytes(
                    release.extractfile("package/silk/ora.py").read()
                )
            body = "sys.argv = ['run.py', os.environ['AN_SPOOL_INPUT']]"
            outputs = ["film.mp4", "editable.blend", "report.json", "painting.ora"]
            dependencies = ["numpy", "pillow"]
        code = (
            "import os, sys, json, runpy\nfrom pathlib import Path\ncode = Path(__file__).resolve().parent\n"
            + body
            + "\nrunpy.run_path(str(code/'run.py'), run_name='__main__')\n"
        )
        if name == "mechanical-film":
            code += """
import subprocess
from PIL import Image
from ora import pack
config = json.loads(Path('config.json').read_text())
subprocess.run([config['tools']['ffmpeg'], '-v', 'error', '-i', 'film.mp4', '-frames:v', '1', 'beauty.png'], check=True)
image = Image.open('beauty.png')
Image.new('RGB', image.size, (1, 2, 3)).save('ids.png')
Path('scene.json').write_text(json.dumps({'scope':'film-first-frame-reference', 'editable_parts':False}))
pack(Path('.'), {'title':'Mechanical film reference', 'ids':{'film-reference':(1,2,3)}})
"""
        (silk / "main.py").write_text(code)
        (silk / "origin.json").write_text(
            json.dumps(
                {
                    "source_release": item,
                    "ora_source": "spools/cad-paint/silk/ora.py"
                    if name == "mechanical-film"
                    else None,
                },
                indent=2,
            )
            + "\n"
        )
        manifest = {
            "schema": "an-native-spool-v3",
            "name": name,
            "version": "0.2.0",
            "entry": "silk/main.py",
            "files": {
                f"silk/{p.name}": hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(silk.iterdir())
            },
            "events": {
                "consumes": ["artifact.accepted"],
                "produces": ["artifact.accepted"],
            },
            "outputs": outputs,
            "binary_outputs": [n for n in outputs if n != "report.json"],
            "requirements": {
                "runtime": "macos-native-python-v1",
                "os": "macos",
                "arch": "portable-source",
                "interaction": "headless",
                "gpu": "metal" if name == "mechanical-film" else "none",
                "inputs": ["input.bin"],
                "editable": [],
                "dependencies": dependencies,
                "capabilities": ["read-input", "write-declared-outputs"],
            },
        }
        (folder / "native-spool.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    build(parser.parse_args().output)
