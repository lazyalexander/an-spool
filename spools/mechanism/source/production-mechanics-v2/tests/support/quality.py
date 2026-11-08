"""Kit-local rejection checks. Witnesses prove defects, not collision freedom."""
import hashlib
import json
from pathlib import Path
import numpy as np

PROFILE = "mechanical-film.assembly/v1"
SUPPORTED = {
    "cases.py": "554fb3b484d91a322f21ede5ade2b185d45b7fa354d9273a200b772035d1ec15",
    "mesh.py": "a9ed4f386ed88256003f39a48ec10405827fc4dfeb497c7fda4536e1f147c166",
    "types.py": "7559f4b58111325141844f8e3138b72c42e2902c760f3d992bb555de43173d5a",
    "providers.py": "8eea1880b9073df7dc46164cb983138bd6b786a2402bcd646c4db3c4fbbf9254",
}


def checker_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def disposition(checks):
    required = [c for c in checks if c.get("required", True)]
    if any(c["status"] == "failed" for c in required):
        return "failed"
    if not required or any(c["status"] not in ("passed", "not_applicable") for c in required):
        return "unknown"
    if any(c["status"] == "not_applicable" and not c.get("reason") for c in required):
        return "unknown"
    return "passed"


def components(mesh):
    """Keep the primitive solids separate; overlapping union members do not cancel."""
    parents = list(range(len(mesh.vertices)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for face in mesh.faces:
        a = find(int(face[0]))
        for index in face[1:]:
            parents[find(int(index))] = a
    groups = {}
    for face in mesh.faces:
        groups.setdefault(find(int(face[0])), []).append(face)
    return [mesh.vertices[np.asarray(faces)] for faces in groups.values()]


def interior_component(point, solids):
    """Six independent ray parities must agree on strict interior membership.

    This is a bounded numerical witness check for this fixture's closed primitive
    components, not a supported arbitrary STL collision or containment API.
    """
    directions = np.array([[1,.371,.529],[-.217,1,.413],[.319,-.271,1.]])
    directions = np.vstack((directions, -directions))
    for index, triangles in enumerate(solids):
        a = triangles[:,0]
        e1, e2 = triangles[:,1]-a, triangles[:,2]-a
        agreed = True
        for direction in directions:
            h = np.cross(direction, e2)
            det = np.einsum("ij,ij->i", e1, h)
            valid = np.abs(det) > 1e-10
            inv = np.divide(1., det, out=np.zeros_like(det), where=valid)
            s = point-a
            u = inv*np.einsum("ij,ij->i", s, h)
            q = np.cross(s,e1)
            v = inv*(q@direction)
            t = inv*np.einsum("ij,ij->i", e2,q)
            hits = t[valid & (u>=-1e-10) & (v>=-1e-10) & (u+v<=1+1e-10) & (t>1e-7)]
            # Shared triangle edges count as one crossing, not two.
            if len(np.unique(np.round(hits,8))) % 2 != 1:
                agreed = False
                break
        if agreed:
            return index
    return None


def assess(scene, implementation, provider=None):
    source = scene["source"]
    binding = hashlib.sha256(json.dumps({"source": source, "implementation": implementation},
        sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    report = {"profile": PROFILE, "checker_sha256": checker_identity(),
              "geometry_binding": binding, "source_kind": source.get("kind"),
              "checks": [], "coverage": {
                  "purpose": "Detect specific assembly defects using interior points in actual placed meshes",
                  "phases": [0, .5], "continuous_collision_proof": False,
                  "uncovered": "Other part pairs, other phases, forces, manufacturing and arbitrary CAD assemblies"}}
    def unknown(reason):
        report["checks"].append({"rule": "mechanical_coverage", "required": True,
                                  "status": "unknown", "reason": reason})
    if source.get("kind") != "slider_crank":
        unknown("No supported mechanical acceptance checker for this source kind; media integrity is not mechanical approval")
    elif any(implementation.get(name) != value for name,value in SUPPORTED.items()):
        unknown("Provider implementation changed; this checker profile has not been validated against its geometry semantics")
    else:
        if provider is None:
            from mechflow.providers import make_provider
            provider = make_provider(source)
        checks = {}
        for name in ("rod_flywheel_clearance", "crosshead_flywheel_clearance", "bearing_bores"):
            checks[name] = {"rule": name, "required": True, "status": "unknown",
                "reason": "No defect witness is not proof of clearance", "evidence": []}
        for phase in (0., .5):
            frame = provider.frame(phase)
            parts = {p.id:p for p in frame.parts}
            if not {"rod","piston","flywheel","frame","crank"} <= parts.keys():
                unknown("Required part identities are unavailable")
                break
            solids = {pid:[tri @ p.transform[:3,:3].T+p.transform[:3,3]
                           for tri in components(p.mesh)] for pid,p in parts.items()}
            pin, crosshead = np.asarray(frame.joints["crank_pin"]), np.asarray(frame.joints["crosshead"])
            rod_points = [pin+(crosshead-pin)*fraction for fraction in (.2,.4,.6,.8)]
            candidates = [
                ("rod_flywheel_clearance", "rod", "flywheel", rod_points),
                ("crosshead_flywheel_clearance", "piston", "flywheel",
                 [crosshead+np.array([x,1.,0.]) for x in (-7.,0.,7.)]),
                ("bearing_bores", "crank", "frame",
                 [np.asarray(frame.joints["crank_center"])+np.array([0.,15.,0.])])]
            for rule, left, right, points in candidates:
                for point in points:
                    lhs, rhs = interior_component(point,solids[left]), interior_component(point,solids[right])
                    if lhs is not None and rhs is not None:
                        checks[rule]["status"] = "failed"
                        checks[rule]["reason"] = ("Shaft occupies an unbored solid bearing boss" if rule=="bearing_bores"
                            else "Unintended bodies share an interior point outside a permitted joint")
                        checks[rule]["evidence"].append({"phase": phase, "parts": [left,right],
                            "world_point": point.tolist(), "primitive_components": [lhs,rhs],
                            "method": "Six-ray interior parity on each closed primitive component"})
                        break
        report["checks"].extend(checks.values())
        unknown("Continuous motion clearance has not been certified; this profile only rejects proven sampled defects")
    report["status"] = disposition(report["checks"])
    return report


def preflight(shots, implementation):
    results = [{"shot": sid, **assess(scene, implementation)} for sid,scene in shots]
    statuses = [result["status"] for result in results]
    status = "failed" if "failed" in statuses else "unknown" if "unknown" in statuses else "passed"
    return {"schema": "mechanical-film.quality/v1", "profile": PROFILE,
            "checker_sha256": checker_identity(), "status": status,
            "delivery_eligible": status=="passed", "shots": results,
            "build_status": "not_started", "creative_approval": "not_requested",
            "model_calls": 0, "model_tokens": 0}
