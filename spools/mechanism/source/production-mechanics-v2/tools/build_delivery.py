#!/usr/bin/env python3
"""Build the production-mechanics-v1 delivery: meshes.json, poses.json, report.json.

Run from the package root:

    PYTHONPATH=src:/private/tmp/steam-ink-deps python3 tools/build_delivery.py

Writes into delivery/. The report mixes analytic results (layout
arithmetic, coaxial fits, Y-slab arguments valid for every phase because
all rotation is about Y) with sampled results (mesh-level pair clearances
at 72 phases). Sampled clearance is finite evidence, not a
continuous-time collision proof; the report says so in its scope notes.
"""
import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mechflow import audit, meshcheck                          # noqa: E402
from mechflow.cases import make_provider as make_original      # noqa: E402
from mechflow.steam_engine import SteamEngineProvider          # noqa: E402

ORIGINAL_CASES_SHA256 = "554fb3b484d91a322f21ede5ade2b185d45b7fa354d9273a200b772035d1ec15"
SOURCE_SCENE = Path(__file__).resolve().parents[2] / "mechanical-pipeline-v1/examples/slider-crank.json"

PHASES = 72
FPS = 24
DURATION = 3.0

# Declared joint allowances: pin housings (moving zones, evaluated per
# phase) and static mounts (feet embedded 0.5 into the base top).
BIG_END_ZONE = {"radius": 6.0, "y_half": 7.5}     # about the crank pin
SMALL_END_ZONE = {"radius": 5.5, "y_half": 8.0}   # about the crosshead joint
STATIC_MOUNT_PAIRS = {frozenset(("frame", "base")), frozenset(("guides", "base"))}
MOUNT_EMBED = 0.5


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rounded(x, ndigits):
    return np.round(np.asarray(x, dtype=float), ndigits).tolist()


def analytic_checks(p):
    """Whole-cycle guarantees derived from the layout constants.

    All rotation is about the Y shaft axis, so Y extents of every part are
    phase-invariant; crosshead/piston extremes occur exactly at phase 0 and
    1/2 (slider-crank extrema). Each check names that basis.
    """
    checks = []

    def add(cid, detail, value, threshold, basis):
        checks.append({"id": cid, "method": "analytic", "detail": detail,
                       "value": float(value), "threshold": float(threshold),
                       "pass": bool(value >= threshold), "basis": basis})

    add("axial_separation",
        "flywheel hub plane y=34 vs rod plane y=0 (reference: render_study.py:91)",
        p.axial_separation, 34.0, "layout constant; equals the reference study value")
    add("axial_separation_upper",
        "separation must not exceed the reference value either",
        68.0 - p.axial_separation, 34.0, "exact match required: value is 68 - separation")
    for i, span in enumerate(p.boss_spans):
        covered = (p.shaft_neg_span[0] <= span[0] and span[1] <= p.shaft_neg_span[1]) or \
                  (p.shaft_pos_span[0] <= span[0] and span[1] <= p.shaft_pos_span[1])
        checks.append({"id": f"shaft_reach_boss_{i}", "method": "analytic",
                       "detail": f"shaft stub covers bearing boss span {span}",
                       "value": float(covered), "threshold": 1.0, "pass": bool(covered),
                       "basis": "interval inclusion"})
    for name, span in (("hub", p.hub_span), ("nut", p.nut_span)):
        covered = p.shaft_pos_span[0] <= span[0] and span[1] <= p.shaft_pos_span[1]
        checks.append({"id": f"shaft_reach_{name}", "method": "analytic",
                       "detail": f"shaft stub covers {name} span {span}",
                       "value": float(covered), "threshold": 1.0, "pass": bool(covered),
                       "basis": "interval inclusion"})
    add("bearing_fit", "boss bore minus shaft radius (two bored bosses)",
        p.boss_bore - p.shaft_radius, 0.1, "coaxial cylinders, phase-invariant")
    add("hub_fit", "flywheel hub bore minus shaft radius",
        p.hub_bore - p.shaft_radius, 0.1, "coaxial, phase-invariant")
    add("nut_fit", "retaining nut bore minus shaft radius",
        p.nut_bore - p.shaft_radius, 0.1, "coaxial, phase-invariant")
    add("big_end_fit", "rod big-end bore minus crank pin radius",
        p.big_end_bore - p.pin_radius, 0.1, "coaxial pin joint, phase-invariant")
    add("wrist_fit", "rod small-end bore minus wrist pin radius",
        p.small_end_bore - p.wrist_pin_radius, 0.1, "coaxial pin joint, phase-invariant")
    add("shank_big_bore_clear", "flat shank end remains outside big-end bore",
        -p.shank_start - p.big_end_bore, 0.1,
        "flat-capped X cylinder has x <= shank_start; no spherical endpoint")
    add("shank_small_bore_clear", "flat shank end remains outside small-end bore",
        p.shank_end + p.rod_length - p.small_end_bore, 0.1,
        "flat-capped X cylinder has x >= shank_end; rigid local geometry")
    add("piston_bore_fit", "cylinder bore minus piston head radius",
        p.cylinder_bore - p.head_radius, 0.1, "coaxial, phase-invariant")
    plate_reach = p.crosshead_travel[0] - 10.0
    add("crosshead_end_clearance",
        "rearmost crosshead plate face minus cylinder end face",
        plate_reach - p.cylinder_span[1],
        0.25, "crosshead extreme is exact at phase 0 (slider-crank extrema)")
    add("head_end_margin_crank_side", "cylinder end minus nearest head face",
        p.cylinder_span[1] - p.head_travel[1], 0.5, "extreme exact at phase 1/2")
    add("head_end_margin_back", "rearmost head face minus cylinder back end",
        p.head_travel[0] - p.cylinder_span[0], 1.0, "extreme exact at phase 0")
    add("guide_clearance", "rail inner face minus crosshead cheek outer face",
        p.guide_y - p.guide_radius - 12.0, 0.5,
        "piston has pure X translation; Y extents phase-invariant")
    add("web_housing_gap", "crank web slab minus rod big-end housing slab",
        (p.web_y - p.web_radius) - p.big_end_span[1], 0.5, "Y slabs, phase-invariant")
    add("web_boss_gap", "bearing boss slab minus crank web slab",
        p.boss_spans[1][0] - (p.web_y + p.web_radius), 0.5, "Y slabs, phase-invariant")
    add("rod_plane_shaft_gap",
        "inner shaft stub face minus rod shank half-thickness; the shaft "
        "does not cross the rod sweep (the v1 defect)",
        p.shaft_pos_span[0] - p.shank_radius, 1.0, "Y slabs, phase-invariant")
    add("rim_base_gap", "flywheel rim lowest point minus base top",
        p.axis_z - (p.fly_major + p.fly_minor) - p.base_top_z, 1.0,
        "rim Z extent is phase-invariant (Y rotation)")
    add("valve_head_gap", "valve chest nearest face minus rearmost head face",
        p.head_travel[0] - p.valve_span[1], 0.5, "extreme exact at phase 0")
    add("boss_flywheel_gap", "hub slab minus boss slab",
        p.hub_span[0] - p.boss_spans[1][1], 0.5, "Y slabs, phase-invariant")
    return checks


def sampled_checks(p, phases):
    """Mesh-level pair clearances over the given phases (finite evidence)."""
    part_ids = [pt.id for pt in p.frame(0.0).parts]
    pairs = [pq for pq in itertools.combinations(part_ids, 2)
             if frozenset(pq) not in STATIC_MOUNT_PAIRS]
    worst = {pq: {"min_distance": np.inf, "interpenetrating": False,
                  "worst_phase": None} for pq in pairs}
    for phase in phases:
        frame = p.frame(float(phase))
        parts = {pt.id: pt for pt in frame.parts}
        world = {pid: (pt.world_vertices(), pt.mesh.faces) for pid, pt in parts.items()}
        pin, ch = frame.joints["crank_pin"], frame.joints["crosshead"]
        for pq in pairs:
            zones = []
            if frozenset(pq) == frozenset(("crank", "rod")):
                zones = [(pin, BIG_END_ZONE["radius"], BIG_END_ZONE["y_half"])]
            elif frozenset(pq) == frozenset(("rod", "piston")):
                zones = [(ch, SMALL_END_ZONE["radius"], SMALL_END_ZONE["y_half"])]
            d, inter = meshcheck.pair_clearance(*world[pq[0]], *world[pq[1]], zones)
            w = worst[pq]
            if d < w["min_distance"]:
                w["min_distance"], w["worst_phase"] = d, float(phase)
            w["interpenetrating"] = w["interpenetrating"] or inter
    checks = []
    for (a, b), w in sorted(worst.items()):
        zones_note = ""
        if frozenset((a, b)) == frozenset(("crank", "rod")):
            zones_note = ("; big-end housing zone (r=6.0, |y|<=7.5 about the "
                          "instantaneous crank pin) excluded as a declared joint")
        elif frozenset((a, b)) == frozenset(("rod", "piston")):
            zones_note = ("; small-end housing zone (r=5.5, |y|<=8.0 about the "
                          "instantaneous crosshead joint) excluded as a declared joint")
        checks.append({
            "id": f"clearance_{a}_{b}", "method": "sampled",
            "detail": f"mesh pair {a} x {b}: min surface distance over "
                      f"{len(phases)} phases{zones_note}",
            "value": w["min_distance"], "threshold": 0.0,
            "pass": bool(w["min_distance"] > 0.0 and not w["interpenetrating"]),
            "worst_phase": w["worst_phase"],
            "interpenetrating_somewhere": w["interpenetrating"],
            "basis": "exact vertex-face/edge-edge distances and strict "
                     "edge-triangle crossings at finitely many phases; not a "
                     "continuous swept-volume proof"})
    return checks


def static_mount_checks(p):
    checks = []
    frame = p.frame(0.0)
    parts = {pt.id: pt for pt in frame.parts}
    for pid in ("frame", "guides"):
        V = parts[pid].world_vertices()
        below = V[V[:, 2] < p.base_top_z - 1e-9]
        depth = float(p.base_top_z - below[:, 2].min()) if len(below) else 0.0
        checks.append({
            "id": f"static_mount_{pid}_base", "method": "analytic",
            "detail": f"{pid} feet embed {depth:.3f} into the base top "
                      f"(declared bonded mount, allowance {MOUNT_EMBED}); all "
                      f"other geometry of the pair is separated",
            "value": MOUNT_EMBED - depth, "threshold": 0.0,
            "pass": bool(len(below) and depth <= MOUNT_EMBED + 1e-9),
            "basis": "static parts; vertex scan at one phase suffices"})
    return checks


def known_bad_original(phases_quick):
    """Reproduce the diagnosed defects on the untouched v1 provider."""
    src = json.loads(SOURCE_SCENE.read_text())
    provider = make_original(src["source"])
    frame0 = provider.frame(0.0)
    parts0 = {pt.id: pt for pt in frame0.parts}
    axial = abs(float(parts0["flywheel"].transform[1, 3]
                      - parts0["crank"].transform[1, 3]))

    def pair(a, b, phase):
        fr = provider.frame(phase)
        parts = {pt.id: pt for pt in fr.parts}
        return meshcheck.pair_clearance(parts[a].world_vertices(), parts[a].mesh.faces,
                                        parts[b].world_vertices(), parts[b].mesh.faces)

    rod_fly = [pair("rod", "flywheel", float(ph)) for ph in phases_quick]
    shaft_boss = pair("crank", "frame", 0.0)
    cross_rim = pair("piston", "flywheel", 0.5)
    return {
        "reference": "mechanical-pipeline-v1 slider_crank, copied verbatim "
                     "(sha256 pinned) and exercised through its own public API",
        "axial_separation": axial,
        "axial_separation_required": 34.0,
        "rod_x_flywheel": {
            "min_distance": min(d for d, _ in rod_fly),
            "interpenetrating_somewhere": any(i for _, i in rod_fly),
            "phases": [float(ph) for ph in phases_quick]},
        "crank_x_frame_solid_boss": {
            "min_distance": shaft_boss[0], "interpenetrating": shaft_boss[1]},
        "piston_crosshead_x_flywheel_rim_phase_0.5": {
            "min_distance": cross_rim[0], "interpenetrating": cross_rim[1]},
    }


def main():
    spec = json.loads((ROOT / "examples/steam-engine.json").read_text())
    params = spec["source"]["parameters"]
    provider = SteamEngineProvider(**params)
    phases = [i / PHASES for i in range(PHASES)]

    # --- audit gate (unmodified) -------------------------------------------
    audit_report = audit.audit(provider, samples=181)

    # --- meshes.json ---------------------------------------------------------
    frame0 = provider.frame(0.0)
    meshes = {pt.id: {"label": pt.label, "material": pt.material,
                      "vertices": rounded(pt.mesh.vertices, 6),
                      "faces": np.asarray(pt.mesh.faces).tolist()}
              for pt in frame0.parts}

    # --- poses.json ----------------------------------------------------------
    poses = []
    for phase in phases:
        frame = provider.frame(phase)
        poses.append({
            "phase": phase,
            "transforms": {pt.id: rounded(pt.transform, 9) for pt in frame.parts},
            "joints": {k: rounded(v, 9) for k, v in frame.joints.items()},
            "residuals": {k: float(v) for k, v in frame.residuals.items()},
        })

    # --- checks ---------------------------------------------------------------
    checks = analytic_checks(provider)
    checks += static_mount_checks(provider)
    checks += sampled_checks(provider, phases)

    max_residual = max(max(po["residuals"].values()) for po in poses)
    checks.append({
        "id": "rod_endpoints_pin_coincident", "method": "analytic",
        "detail": "max over 72 poses of rod big/small-end placement error; "
                  "zero by transform algebra (rod transform is built from the "
                  "two joint points)",
        "value": max(max(po["residuals"]["rod_big_end"], po["residuals"]["rod_small_end"])
                     for po in poses),
        "threshold": 1e-9, "pass": bool(max_residual < 1e-9),
        "basis": "exact construction, evaluated at the 72 delivered phases"})
    last = provider.frame(1.0)
    closure = max(float(np.abs(last.parts[i].transform - frame0.parts[i].transform).max())
                  for i in range(len(frame0.parts)))
    checks.append({
        "id": "closed_cycle", "method": "analytic",
        "detail": "frame(1.0) transforms equal frame(0.0) transforms; the 72 "
                  "samples cover phases i/72 with no duplicate endpoint",
        "value": closure, "threshold": 1e-9, "pass": bool(closure < 1e-9),
        "basis": "2*pi periodicity of the single crank rotation"})

    known_bad = known_bad_original([i / 12 for i in range(12)])

    passed = all(c["pass"] for c in checks)
    report = {
        "schema": "production-mechanics.report/v1",
        "generator": "tools/build_delivery.py (production-mechanics-v2)",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "units": {"length": "model-unit", "angle": "radian", "phase": "cycle",
                  "coordinate_system": "Z up, Y shaft axis, "
                                       "v_world = R @ v_local + translation"},
        "timeline": {"fps": FPS, "duration_seconds": DURATION, "samples": PHASES,
                     "endpoint_duplicated": False},
        "source_scene_parameters": params,
        "source_hashes": {
            "implementation_sha256": {name: sha256(ROOT / name) for name in (
                "src/mechflow/steam_engine.py", "src/mechflow/meshcheck.py",
                "tools/build_delivery.py", "tests/test_joint_material.py")},
            "original_cases_py_sha256": sha256(ROOT / "src/mechflow/cases.py"),
            "original_cases_py_expected": ORIGINAL_CASES_SHA256,
            "original_example_sha256": sha256(SOURCE_SCENE),
            "copied_modules_sha256": {
                name: sha256(ROOT / "src/mechflow" / name)
                for name in ("__init__.py", "types.py", "mesh.py", "audit.py", "cases.py")},
        },
        "audit_gate": audit_report,
        "declared_joint_allowances": [
            {"pair": ["crank", "rod"], "kind": "pin housing",
             "zone": {"about": "instantaneous crank_pin", **BIG_END_ZONE},
             "verified_inside_zone": "big_end_fit (bore 4.4 vs pin 4.2, analytic)"},
            {"pair": ["rod", "piston"], "kind": "pin housing",
             "zone": {"about": "instantaneous crosshead joint", **SMALL_END_ZONE},
             "verified_inside_zone": "wrist_fit (bore 4.2 vs pin 4.0, analytic)"},
            {"pair": ["frame", "base"], "kind": "static mount",
             "embedment": MOUNT_EMBED,
             "note": "pair excluded from mesh sweep; verified by static_mount checks"},
            {"pair": ["guides", "base"], "kind": "static mount",
             "embedment": MOUNT_EMBED,
             "note": "pair excluded from mesh sweep; verified by static_mount checks"},
        ],
        "checks": checks,
        "known_bad_original": known_bad,
        "known_bad_original_fails": bool(
            known_bad["axial_separation"] < 34.0
            and known_bad["rod_x_flywheel"]["interpenetrating_somewhere"]
            and known_bad["crank_x_frame_solid_boss"]["interpenetrating"]
            and known_bad["piston_crosshead_x_flywheel_rim_phase_0.5"]["interpenetrating"]),
        "passed": passed,
        "scope": [
            "Analytic checks use layout arithmetic and phase-invariant "
            "arguments (all rotation is about Y; slider extrema are exact).",
            "Sampled checks measure exact mesh distances at 72 phases; this "
            "is finite evidence, not a continuous-time collision proof.",
            "Static-mount pairs (frame/base, guides/base) are excluded from "
            "the mesh sweep only; their embedment is measured analytically.",
            "No force, load, steam, or manufacturing validation.",
        ],
    }

    out = ROOT / "delivery"
    out.mkdir(exist_ok=True)
    (out / "meshes.json").write_text(json.dumps(meshes) + "\n")
    (out / "poses.json").write_text(json.dumps(poses) + "\n")
    report["delivery_sha256"] = {name: sha256(out / name)
                                 for name in ("meshes.json", "poses.json")}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"checks: {sum(c['pass'] for c in checks)}/{len(checks)} passed; "
          f"known-bad original fails as diagnosed: {report['known_bad_original_fails']}")
    print(f"wrote {out/'meshes.json'}, {out/'poses.json'}, {out/'report.json'}")
    if not passed:
        for c in checks:
            if not c["pass"]:
                print("FAILED:", c["id"], c["detail"], c["value"])
        raise SystemExit(1)


if __name__ == "__main__":
    main()
