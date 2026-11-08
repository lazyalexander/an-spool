"""Bind accepted geometry to selected approved appearance assets."""

import hashlib, json, sys, zipfile
from pathlib import Path

geometry, config, scene, atlas, background = map(Path, sys.argv[1:])
with zipfile.ZipFile(geometry) as z:
    payload = {
        name: z.read(name) for name in ("meshes.json", "poses.json", "report.json")
    }
report = json.loads(payload["report.json"])
assert report["passed"]
for name in ("meshes.json", "poses.json"):
    assert hashlib.sha256(payload[name]).hexdigest() == report["delivery_sha256"][name]
c = json.loads(config.read_text())
for key, path in [("scene", scene), ("atlas", atlas), ("background", background)]:
    assert hashlib.sha256(path.read_bytes()).hexdigest() == c["inputs"][key]["sha256"]
    payload[key + path.suffix] = path.read_bytes()
for key, item in c["inputs"].items():
    if key in ("cad_source", "cad_clearance"):
        continue
    name = key + Path(item["path"]).suffix
    if key in ("meshes", "poses", "report"):
        name = key + ".json"
    item["path"] = name
    item["sha256"] = hashlib.sha256(payload[name]).hexdigest()
c["inputs"] = {
    key: value
    for key, value in c["inputs"].items()
    if key not in ("cad_source", "cad_clearance")
}
c["export"]["prores"] = False
payload["config.json"] = json.dumps(c).encode()
with zipfile.ZipFile("appearance.zip", "w", zipfile.ZIP_DEFLATED) as output:
    for name, data in payload.items():
        output.writestr(name, data)
Path("report.json").write_text(
    json.dumps(
        {
            "passed": True,
            "geometry_sha256": hashlib.sha256(geometry.read_bytes()).hexdigest(),
            "mode": "retained-approved-assets",
            "new_model_calls": 0,
        }
    )
)
