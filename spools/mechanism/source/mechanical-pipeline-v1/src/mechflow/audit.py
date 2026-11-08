"""Check prescribed geometry, not forces, collisions, or contact dynamics."""
import numpy as np


def audit(provider, samples=181, tolerance=1e-7):
    if samples < 2:
        raise ValueError("At least two audit samples are required")
    first = provider.frame(0.0)
    identities = tuple(p.id for p in first.parts)
    if not identities or any(not isinstance(x, str) or not x for x in identities) or len(set(identities)) != len(identities):
        raise ValueError("Part IDs must be nonempty and unique")
    meshes = {p.id: (p.mesh.vertices.copy(), p.mesh.faces.copy()) for p in first.parts}
    transforms = {p.id: p.transform.copy() for p in first.parts}
    maximum = {}
    joint_names = set(first.joints)
    residual_names = set(first.residuals)
    for phase in np.linspace(0, 1, samples):
        frame = provider.frame(float(phase))
        if not np.isfinite(frame.phase) or abs(frame.phase - phase) > tolerance:
            raise ValueError("Provider returned the wrong phase")
        if set(frame.joints) != joint_names or set(frame.residuals) != residual_names:
            raise ValueError("Joint or constraint identities changed within a cycle")
        if tuple(p.id for p in frame.parts) != identities:
            raise ValueError("Part identities/order changed within a cycle")
        for part in frame.parts:
            vertices, faces = meshes[part.id]
            if vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) < 3 or not np.isfinite(vertices).all():
                raise ValueError(f"Invalid vertices: {part.id}")
            if faces.ndim != 2 or faces.shape[1] != 3 or not np.issubdtype(faces.dtype, np.integer):
                raise ValueError(f"Invalid triangle indices: {part.id}")
            if faces.size and (faces.min() < 0 or faces.max() >= len(vertices)):
                raise ValueError(f"Out-of-range triangle: {part.id}")
            if not np.array_equal(vertices, part.mesh.vertices) or not np.array_equal(faces, part.mesh.faces):
                raise ValueError(f"Local mesh changed: {part.id}")
            t = part.transform
            if t.shape != (4, 4) or not np.isfinite(t).all():
                raise ValueError(f"Invalid transform: {part.id}")
            if not np.allclose(t[3], [0, 0, 0, 1], atol=tolerance, rtol=0):
                raise ValueError(f"Invalid homogeneous transform: {part.id}")
            rotation = t[:3, :3]
            if not np.allclose(rotation.T @ rotation, np.eye(3), atol=tolerance, rtol=0) or not np.isclose(np.linalg.det(rotation), 1, atol=tolerance, rtol=0):
                raise ValueError(f"Non-rigid transform: {part.id}")
        for name, point in frame.joints.items():
            if np.asarray(point).shape != (3,) or not np.isfinite(point).all():
                raise ValueError(f"Invalid joint: {name}")
        for name, value in frame.residuals.items():
            if not np.isfinite(value) or value < 0 or value > tolerance:
                raise ValueError(f"Constraint residual failed: {name}={value}")
            maximum[name] = max(maximum.get(name, 0.0), float(value))
    last = provider.frame(1.0)
    for name in joint_names:
        if not np.allclose(last.joints[name], first.joints[name], atol=tolerance, rtol=0):
            raise ValueError(f"Joint cycle does not close: {name}")
    for part in last.parts:
        if not np.allclose(part.transform, transforms[part.id], atol=tolerance, rtol=0):
            raise ValueError(f"Cycle does not close: {part.id}")
    return {"samples": samples, "tolerance": tolerance, "parts": len(identities), "maximum_residuals": maximum,
            "scope": "Prescribed rigid kinematics and cycle closure only; no contact, collision, load, or thermodynamic validation."}
