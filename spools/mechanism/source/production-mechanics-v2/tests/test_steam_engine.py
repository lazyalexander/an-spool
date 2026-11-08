"""Tests for the corrected steam engine and its delivery.

Covers: the copied originals (hash-pinned, rejection gate untouched), the
known-bad v1 provider failing the assembly checks it is diagnosed with,
the corrected provider passing analytic and sampled checks, and the
delivered meshes.json / poses.json / report.json conforming to the
handoff format.

Run from the package root (after tools/build_delivery.py):

    PYTHONPATH=src:/private/tmp/steam-ink-deps python3 -m unittest discover -s tests -v
"""
import hashlib
import itertools
import json
import math
import unittest
from pathlib import Path

import numpy as np

from mechflow import audit, meshcheck
from mechflow.cases import make_provider as make_original
from mechflow.steam_engine import SteamEngineProvider

ROOT = Path(__file__).resolve().parent.parent
DELIVERY = ROOT / "delivery"
ORIGINAL_CASES_SHA256 = "554fb3b484d91a322f21ede5ade2b185d45b7fa354d9273a200b772035d1ec15"
PIPELINE = ROOT.parent / "mechanical-pipeline-v1"

# Keep the test sweep cheaper than the delivered 72-phase one; the
# generator runs the full sweep and its results are checked separately.
TEST_PHASES = [i / 13 for i in range(13)]
STATIC_MOUNT_PAIRS = {frozenset(("frame", "base")), frozenset(("guides", "base"))}
ZONES = {
    frozenset(("crank", "rod")): ("crank_pin", 6.0, 7.5),
    frozenset(("rod", "piston")): ("crosshead", 5.5, 8.0),
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pair_at(provider, a, b, phase, zones=()):
    frame = provider.frame(phase)
    parts = {p.id: p for p in frame.parts}
    return meshcheck.pair_clearance(
        parts[a].world_vertices(), parts[a].mesh.faces,
        parts[b].world_vertices(), parts[b].mesh.faces, zones)


class CopiedOriginalsTests(unittest.TestCase):
    def test_cases_py_is_the_pinned_known_bad_original(self):
        self.assertEqual(sha256(ROOT / "src/mechflow/cases.py"), ORIGINAL_CASES_SHA256)

    def test_copied_modules_byte_identical_to_pipeline(self):
        for name in ("__init__.py", "types.py", "mesh.py", "audit.py", "cases.py"):
            self.assertEqual(sha256(ROOT / "src/mechflow" / name),
                             sha256(PIPELINE / "src/mechflow" / name),
                             f"{name} must be a verbatim copy (rejection gate untouched)")


class KnownBadOriginalTests(unittest.TestCase):
    """The v1 provider must FAIL the assembly checks it is diagnosed with."""

    @classmethod
    def setUpClass(cls):
        spec = json.loads((PIPELINE / "examples/slider-crank.json").read_text())
        cls.provider = make_original(spec["source"])

    def test_legacy_audit_still_passes(self):
        # The kinematics were never the problem; the assembly was.
        audit.audit(self.provider, samples=73)

    def test_axial_separation_collapsed(self):
        frame = self.provider.frame(0.0)
        parts = {p.id: p for p in frame.parts}
        separation = abs(float(parts["flywheel"].transform[1, 3]
                               - parts["crank"].transform[1, 3]))
        self.assertAlmostEqual(separation, 0.0, places=12,
                               msg="defect premise: flywheel shares the crank transform")
        self.assertNotAlmostEqual(separation, 34.0, places=6,
                                  msg="the reference separation of 34 is gone")

    def test_rod_flywheel_spoke_interpenetration(self):
        # Witness pair from intersection-evidence.json, phase 0.
        results = [pair_at(self.provider, "rod", "flywheel", p) for p in TEST_PHASES]
        self.assertTrue(any(i for _, i in results),
                        "rod and flywheel must interpenetrate in the known-bad scene")
        self.assertLess(min(d for d, _ in results), 0.0 + 1e-9)

    def test_shaft_inside_solid_bearing_boss(self):
        # Witness 3: bosses have no shaft bores.
        _, inter = pair_at(self.provider, "crank", "frame", 0.0)
        self.assertTrue(inter, "shaft must intersect the unbored boss")

    def test_crosshead_enters_flywheel_rim(self):
        # Witness pair from intersection-evidence.json, phase 0.5.
        _, inter = pair_at(self.provider, "piston", "flywheel", 0.5)
        self.assertTrue(inter, "crosshead must enter the rim in the known-bad scene")


class CorrectedProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider = SteamEngineProvider()

    def test_audit_gate_passes_unmodified(self):
        report = audit.audit(self.provider, samples=181)
        self.assertLess(max(report["maximum_residuals"].values()), 1e-9)
        self.assertEqual(report["parts"], 8)

    def test_stable_part_identity(self):
        ids = [p.id for p in self.provider.frame(0.0).parts]
        self.assertEqual(ids, ["base", "frame", "guides", "cylinder",
                               "piston", "crank", "flywheel", "rod"])
        for phase in (0.2, 0.55, 0.8):
            other = self.provider.frame(phase)
            self.assertEqual([p.id for p in other.parts], ids)
            for a, b in zip(self.provider.frame(0.0).parts, other.parts):
                self.assertIs(a.mesh, b.mesh)

    def test_axial_separation_restored(self):
        self.assertEqual(self.provider.axial_separation, 34.0)
        for phase in TEST_PHASES:
            frame = self.provider.frame(phase)
            parts = {p.id: p for p in frame.parts}
            self.assertAlmostEqual(float(parts["flywheel"].transform[1, 3]), 34.0, places=12)
            self.assertAlmostEqual(float(parts["crank"].transform[1, 3]), 0.0, places=12)
            np.testing.assert_allclose(parts["flywheel"].transform[:3, :3],
                                       parts["crank"].transform[:3, :3], atol=1e-12)

    def test_shaft_reaches_bosses_hub_and_nut(self):
        p = self.provider
        for span in p.boss_spans:
            covered = (p.shaft_neg_span[0] <= span[0] and span[1] <= p.shaft_neg_span[1]) or \
                      (p.shaft_pos_span[0] <= span[0] and span[1] <= p.shaft_pos_span[1])
            self.assertTrue(covered, f"bearing boss span {span} not covered by a shaft stub")
        self.assertLessEqual(p.shaft_pos_span[0], p.hub_span[0])
        self.assertGreaterEqual(p.shaft_pos_span[1], p.nut_span[1])

    def test_modeled_fits_have_positive_clearance(self):
        p = self.provider
        self.assertGreaterEqual(p.boss_bore - p.shaft_radius, 0.1)
        self.assertGreaterEqual(p.hub_bore - p.shaft_radius, 0.1)
        self.assertGreaterEqual(p.nut_bore - p.shaft_radius, 0.1)
        self.assertGreaterEqual(p.big_end_bore - p.pin_radius, 0.1)
        self.assertGreaterEqual(p.small_end_bore - p.wrist_pin_radius, 0.1)
        self.assertGreaterEqual(p.cylinder_bore - p.head_radius, 0.1)

    def test_shaft_does_not_cross_rod_plane(self):
        p = self.provider
        # No shaft material between the web slabs: the rod sweep never
        # meets a shaft segment (the v1 defect was a through-shaft).
        self.assertGreater(p.shaft_pos_span[0], p.web_y - p.web_radius)
        self.assertLess(p.shaft_neg_span[1], -(p.web_y - p.web_radius))
        self.assertGreater(p.web_y - p.web_radius, p.big_end_span[1])

    def test_all_pair_clearances_sampled(self):
        provider = self.provider
        ids = [p.id for p in provider.frame(0.0).parts]
        pairs = [pq for pq in itertools.combinations(ids, 2)
                 if frozenset(pq) not in STATIC_MOUNT_PAIRS]
        self.assertEqual(len(pairs), 26)
        for phase in TEST_PHASES:
            frame = provider.frame(phase)
            parts = {p.id: p for p in frame.parts}
            world = {pid: (pt.world_vertices(), pt.mesh.faces)
                     for pid, pt in parts.items()}
            for a, b in pairs:
                zones = []
                key = frozenset((a, b))
                if key in ZONES:
                    joint, radius, y_half = ZONES[key]
                    zones = [(frame.joints[joint], radius, y_half)]
                d, inter = meshcheck.pair_clearance(*world[a], *world[b], zones)
                self.assertGreater(d, 0.0, f"{a} x {b} touch at phase {phase:.4f}")
                self.assertFalse(inter, f"{a} x {b} interpenetrate at phase {phase:.4f}")

    def test_rod_endpoints_pin_coincident(self):
        L = self.provider.rod_length
        for phase in TEST_PHASES:
            frame = self.provider.frame(phase)
            rod = [p for p in frame.parts if p.id == "rod"][0]
            big = rod.transform[:3, 3]
            small = rod.transform[:3, :3] @ np.array([-L, 0.0, 0.0]) + rod.transform[:3, 3]
            np.testing.assert_allclose(big, frame.joints["crank_pin"], atol=1e-9)
            np.testing.assert_allclose(small, frame.joints["crosshead"], atol=1e-9)

    def test_cycle_closure(self):
        a = self.provider.frame(0.0)
        b = self.provider.frame(1.0)
        for pa, pb in zip(a.parts, b.parts):
            np.testing.assert_allclose(pa.transform, pb.transform, atol=1e-9,
                                       err_msg=pa.id)

    def test_static_mounts_embed_within_allowance(self):
        p = self.provider
        frame = p.frame(0.0)
        parts = {pt.id: pt for pt in frame.parts}
        for pid in ("frame", "guides"):
            V = parts[pid].world_vertices()
            below = V[V[:, 2] < p.base_top_z - 1e-9]
            self.assertTrue(len(below), f"{pid} must contact the base")
            depth = float(p.base_top_z - below[:, 2].min())
            self.assertLessEqual(depth, 0.5 + 1e-9)


class DeliveryTests(unittest.TestCase):
    """The generated handoff files must exist and match the provider."""

    @classmethod
    def setUpClass(cls):
        for name in ("meshes.json", "poses.json", "report.json"):
            if not (DELIVERY / name).exists():
                raise unittest.SkipTest(f"run tools/build_delivery.py first ({name} missing)")
        cls.meshes = json.loads((DELIVERY / "meshes.json").read_text())
        cls.poses = json.loads((DELIVERY / "poses.json").read_text())
        cls.report = json.loads((DELIVERY / "report.json").read_text())
        cls.provider = SteamEngineProvider()

    def test_meshes_schema_and_identity(self):
        frame = self.provider.frame(0.0)
        self.assertEqual(set(self.meshes), {p.id for p in frame.parts})
        for part in frame.parts:
            entry = self.meshes[part.id]
            self.assertEqual(entry["label"], part.label)
            self.assertEqual(entry["material"], part.material)
            np.testing.assert_allclose(entry["vertices"], part.mesh.vertices, atol=1e-6)
            self.assertEqual(np.asarray(entry["faces"]).tolist(),
                             np.asarray(part.mesh.faces).tolist())

    def test_poses_format_and_phases(self):
        self.assertEqual(len(self.poses), 72)
        for i, pose in enumerate(self.poses):
            self.assertAlmostEqual(pose["phase"], i / 72, places=12)
            self.assertEqual(set(pose), {"phase", "transforms", "joints", "residuals"})
        phases = [p["phase"] for p in self.poses]
        self.assertEqual(len(set(phases)), 72, "no duplicate endpoint")

    def test_poses_match_provider_and_are_rigid(self):
        for i in (0, 7, 23, 41, 71):
            pose = self.poses[i]
            frame = self.provider.frame(pose["phase"])
            for part in frame.parts:
                T = np.asarray(pose["transforms"][part.id])
                self.assertEqual(T.shape, (4, 4))
                np.testing.assert_allclose(T, part.transform, atol=1e-8, err_msg=part.id)
                R = T[:3, :3]
                np.testing.assert_allclose(R.T @ R, np.eye(3), atol=1e-8)
                self.assertAlmostEqual(float(np.linalg.det(R)), 1.0, places=8)

    def test_delivered_rod_endpoints_and_closure(self):
        L = self.provider.rod_length
        for pose in self.poses:
            T = np.asarray(pose["transforms"]["rod"])
            big = T[:3, 3]
            small = T[:3, :3] @ np.array([-L, 0.0, 0.0]) + T[:3, 3]
            np.testing.assert_allclose(big, pose["joints"]["crank_pin"], atol=1e-8)
            np.testing.assert_allclose(small, pose["joints"]["crosshead"], atol=1e-8)
        last = self.provider.frame(1.0)
        first = {p.id: p for p in self.provider.frame(0.0).parts}
        for part in last.parts:
            np.testing.assert_allclose(
                np.asarray(self.poses[0]["transforms"][part.id]),
                first[part.id].transform, atol=1e-8)
            np.testing.assert_allclose(part.transform, first[part.id].transform, atol=1e-9)

    def test_report_is_machine_readable_and_passing(self):
        report = self.report
        self.assertEqual(report["schema"], "production-mechanics.report/v1")
        self.assertTrue(report["passed"])
        self.assertTrue(all(c["pass"] for c in report["checks"]))
        methods = {c["method"] for c in report["checks"]}
        self.assertEqual(methods, {"analytic", "sampled"})
        self.assertEqual(report["timeline"],
                         {"fps": 24, "duration_seconds": 3.0, "samples": 72,
                          "endpoint_duplicated": False})
        self.assertEqual(report["source_hashes"]["original_cases_py_sha256"],
                         ORIGINAL_CASES_SHA256)
        self.assertEqual(report["source_hashes"]["original_cases_py_sha256"],
                         report["source_hashes"]["original_cases_py_expected"])
        self.assertTrue(report["known_bad_original_fails"])
        kb = report["known_bad_original"]
        self.assertLess(kb["axial_separation"], 1e-9)
        self.assertTrue(kb["rod_x_flywheel"]["interpenetrating_somewhere"])
        self.assertTrue(kb["crank_x_frame_solid_boss"]["interpenetrating"])
        self.assertTrue(kb["piston_crosshead_x_flywheel_rim_phase_0.5"]["interpenetrating"])
        self.assertTrue(report["scope"], "scope/limitation notes must be present")


if __name__ == "__main__":
    unittest.main()
