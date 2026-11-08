"""Generate the selected mechanical case from retained source."""

import json, os, subprocess, sys, tarfile, zipfile
from pathlib import Path

archive, case = Path(sys.argv[1]), sys.argv[2]
assert case in ("steam", "inline4")
with tarfile.open(archive) as source:
    source.extractall("package", filter="data")
root = Path("package/source").resolve()
if case == "steam":
    subprocess.run(
        [sys.executable, str(root / "production-mechanics-v2/tools/build_delivery.py")],
        check=True,
    )
    delivery = root / "production-mechanics-v2/delivery"
else:
    delivery = root / "inline4"
    python = "/Applications/FreeCAD.app/Contents/Resources/bin/python"
    subprocess.run([python, str(delivery / "build_engine.py")], check=True)
    subprocess.run([python, str(delivery / "check_cad_clearance.py")], check=True)
report = json.loads((delivery / "report.json").read_text())
assert report["passed"]
with zipfile.ZipFile("geometry.zip", "w", zipfile.ZIP_DEFLATED) as output:
    for name in ("meshes.json", "poses.json", "report.json"):
        output.write(delivery / name, name)
Path("report.json").write_text(json.dumps({"case": case, "source_report": report}))
