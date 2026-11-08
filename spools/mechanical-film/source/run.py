"""Render an accepted appearance bundle with the retained film worker."""

import json, subprocess, sys, zipfile, shutil
from pathlib import Path

bundle = Path(sys.argv[1])
code = Path(__file__).resolve().parent
with zipfile.ZipFile(bundle) as z:
    for info in z.infolist():
        if Path(info.filename).name != info.filename:
            raise ValueError("flat bundle required")
        Path(info.filename).write_bytes(z.read(info))
c = json.loads(Path("config.json").read_text())
for item in c["inputs"].values():
    item["path"] = str(Path(item["path"]).resolve())
c["output"] = "runs"
Path("config.json").write_text(json.dumps(c))
subprocess.run(
    [
        sys.executable,
        str(code / "kit.py"),
        "run",
        "--config",
        str(Path("config.json").resolve()),
    ],
    check=True,
)
run = next(Path("runs").glob("*/render-receipt.json")).parent
shutil.copy2(next(run.glob("export-*/film.mp4")), "film.mp4")
shutil.copy2(run / "editable.blend", "editable.blend")
shutil.copy2(run / "verify-check.json", "report.json")
shutil.rmtree(run)
