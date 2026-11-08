"""Verify a completed real product run from original host evidence and HTTP boundaries."""

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

from product import STAGES, invoke

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--root", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
root = args.root.resolve(strict=True)
config = json.loads((root / "application.json").read_text())
endpoint = json.loads((root / "application-endpoint.json").read_text())["url"]
origin, token = endpoint.split("/#")


def request(path, auth=True, data=None, origin_header=None):
    headers = {"Authorization": "Bearer " + token} if auth else {}
    if origin_header:
        headers["Origin"] = origin_header
    return urllib.request.urlopen(
        urllib.request.Request(origin + path, data=data, headers=headers), timeout=30
    )


for auth, data, origin_header in [
    (False, None, None),
    (True, b"{}", None),
    (True, b"{}", "http://unrelated.invalid"),
]:
    try:
        request("/view" if data is None else "/action", auth, data, origin_header)
        raise AssertionError("Unauthorized application surface accepted")
    except urllib.error.HTTPError as error:
        assert error.code == 403
with request("/view") as response:
    view = json.load(response)
assert len(view["snapshot"]["instances"]) == 6
result = {
    "passed": True,
    "transport_refusals": 3,
    "execution": "original-native-daemon",
    "cases": {},
}
for case, stages in config["cases"].items():
    previous = None
    summary = {}
    for name in STAGES:
        stage = stages[name]
        task = next(
            t
            for t in view["snapshot"]["tasks"]
            if t.get("instance") == stage["instance"] and t.get("run") == stage["run"]
        )
        assert task["state"] == "settled" and task["outcome"] == "succeeded"
        assert task["native"]["artifact_status"] == "accepted"
        assert task["authorization"]["grant"]
        inventory = invoke(
            config["host"], "spool-artifacts", stage["instance"], stage["run"]
        )
        # Source lineage is retained by the original input-reference machinery.
        if previous:
            refs = invoke(
                config["host"],
                "spool-input-references",
                stage["instance"],
                stage["run"],
            )
            assert any(
                c["reference"]["binding"]["revision"] == previous
                for c in refs["claims"]
            )
        output = (
            "geometry.zip"
            if name == "mechanism"
            else "appearance.zip"
            if name == "appearance"
            else "painting.ora"
        )
        selected = invoke(
            config["host"],
            "spool-artifacts",
            stage["instance"],
            stage["run"],
            "--output",
            output,
        )
        previous = selected["output"]["binding"]["revision"]
        summary[name] = {
            "accepted": True,
            "revision": previous,
            "native_manifest": json.loads(
                (Path(stage["instance"]) / "instance.json").read_text()
            )["release"],
        }
    result["cases"][case] = summary
args.output.write_text(json.dumps(result, indent=2) + "\n")
print(
    "Both teaching cases are accepted through the original service; transport and revision lineage passed."
)
