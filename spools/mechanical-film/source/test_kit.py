"""Regression tests for admission and stale-output rejection."""

import copy
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import kit


class Gates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        payloads = {
            "scene": b"fixture",
            "meshes": json.dumps({"part": {}}).encode(),
            "poses": json.dumps([{"transforms": {"part": []}}] * 2).encode(),
        }
        for name, data in payloads.items():
            (self.root / name).write_bytes(data)
        kit.write(
            self.root / "report",
            {
                "passed": True,
                "delivery_sha256": {
                    name + ".json": kit.digest(self.root / name)
                    for name in ("meshes", "poses")
                },
            },
        )
        self.config = {
            "schema": "mechanical-film-kit/v1",
            "tools": {"blender": "/Applications/Blender.app/Contents/MacOS/Blender"},
            "inputs": {
                name: {
                    "path": str(self.root / name),
                    "sha256": kit.digest(self.root / name),
                }
                for name in ("scene", "meshes", "poses", "report")
            },
            "image_bindings": {},
            "render": {
                "frames": 2,
                "fps": 12,
                "width": 64,
                "height": 64,
                "start_pose": 0,
                "preview_frames": [1],
                "tolerance": 0.0001,
            },
            "export": {"fps": 24, "crf": 17, "prores": False},
        }
        self.config["output"] = str(self.root / "runs")

    def load(self, config):
        path = self.root / "config.json"
        kit.write(path, config)
        return kit.load(path)

    def test_changed_input_rejected(self):
        self.config["inputs"]["scene"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Input hash mismatch"):
            self.load(self.config)

    def test_failed_mechanical_report_rejected(self):
        report = json.loads(Path(self.config["inputs"]["report"]["path"]).read_text())
        report["passed"] = False
        path = self.root / "report.json"
        kit.write(path, report)
        self.config["inputs"]["report"] = {
            "path": str(path),
            "sha256": kit.digest(path),
        }
        with self.assertRaisesRegex(ValueError, "Mechanical source report rejected"):
            self.load(self.config)

    def test_unrelated_report_rejected(self):
        report = json.loads(Path(self.config["inputs"]["report"]["path"]).read_text())
        report["delivery_sha256"]["poses.json"] = "0" * 64
        path = self.root / "report.json"
        kit.write(path, report)
        self.config["inputs"]["report"] = {
            "path": str(path),
            "sha256": kit.digest(path),
        }
        with self.assertRaisesRegex(ValueError, "Report does not certify"):
            self.load(self.config)

    def test_fractional_frame_holds_rejected(self):
        self.config["export"]["fps"] = 25
        with self.assertRaisesRegex(ValueError, "integer multiple"):
            self.load(self.config)

    def test_modified_render_rejected(self):
        frame = self.root / "frame.png"
        frame.write_bytes(b"approved")
        kit.write(
            self.root / "render-receipt.json",
            {"passed": True, "artifacts": {"frame.png": kit.digest(frame)}},
        )
        kit.verified(self.root)
        frame.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "Stale or modified"):
            kit.verified(self.root)

    @patch("kit.subprocess.check_output", return_value="Blender test-version\n")
    def test_encoding_change_reuses_render_identity(self, _):
        _, first = self.load(self.config)
        changed = copy.deepcopy(self.config)
        changed["export"]["crf"] = 20
        _, second = self.load(changed)
        self.assertEqual(first, second)

    @patch("kit.subprocess.check_output", return_value="Blender test-version\n")
    def test_pose_change_invalidates_render_identity(self, _):
        _, first = self.load(self.config)
        changed = copy.deepcopy(self.config)
        changed["render"]["start_pose"] = 1
        _, second = self.load(changed)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
