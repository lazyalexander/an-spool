"""Rigid-mesh building primitives for the scene providers.

The vertex/face construction math is adapted from the verified reference
study ``reference/render_assembly.py``; those primitives are used here as
plain geometry helpers, not as CAD features. Every builder returns an
immutable :class:`mechflow.types.Mesh` in a part-local coordinate frame;
providers place parts with rigid 4x4 transforms only.
"""
import math

import numpy as np

from .types import Mesh


def _as_mesh(vertices, faces):
    v = np.asarray(vertices, dtype=float).reshape((-1, 3))
    f = np.asarray(faces, dtype=np.int64).reshape((-1, 3))
    return Mesh(vertices=v, faces=f)


def combine(*meshes):
    """Merge several local meshes into one, re-indexing faces."""
    vertices = []
    faces = []
    offset = 0
    for m in meshes:
        vertices.append(np.asarray(m.vertices, dtype=float))
        faces.append(np.asarray(m.faces, dtype=np.int64) + offset)
        offset += len(m.vertices)
    if not vertices:
        return _as_mesh(np.zeros((0, 3)), np.zeros((0, 3)))
    return Mesh(vertices=np.vstack(vertices), faces=np.vstack(faces))


def _norm(v):
    v = np.asarray(v, dtype=float)
    return v / max(np.linalg.norm(v), 1e-12)


def box(center, size):
    """Axis-aligned box centered at ``center`` with full edge lengths ``size``."""
    c = np.asarray(center, dtype=float)
    sx, sy, sz = np.asarray(size, dtype=float) / 2
    corners = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz),
               (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    vertices = [c + np.array(q) for q in corners]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
             (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return _as_mesh(vertices, faces)


def cylinder(a, b, radius, segments=20):
    """Capped cylinder between endpoints ``a`` and ``b``."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    axis = _norm(b - a)
    ref = np.array([0.0, 0.0, 1.0]) if abs(axis[2]) < 0.85 else np.array([0.0, 1.0, 0.0])
    u = _norm(np.cross(axis, ref))
    w = _norm(np.cross(axis, u))
    vertices = []
    faces = []
    for p in (a, b):
        for i in range(segments):
            t = 2 * math.pi * i / segments
            vertices.append(p + radius * (math.cos(t) * u + math.sin(t) * w))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j))
        faces.append((i, segments + j, segments + i))
    ca = len(vertices)
    vertices.append(a)
    cb = len(vertices)
    vertices.append(b)
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((ca, j, i))
        faces.append((cb, segments + i, segments + j))
    return _as_mesh(vertices, faces)


def sphere(center, radius, lat=8, lon=16):
    c = np.asarray(center, dtype=float)
    vertices = []
    faces = []
    for j in range(lat + 1):
        phi = math.pi * j / lat
        for i in range(lon):
            t = 2 * math.pi * i / lon
            vertices.append(c + radius * np.array(
                [math.sin(phi) * math.cos(t), math.sin(phi) * math.sin(t), math.cos(phi)]))
    for j in range(lat):
        for i in range(lon):
            k = (i + 1) % lon
            a = j * lon + i
            b = j * lon + k
            d = (j + 1) * lon + i
            e = (j + 1) * lon + k
            faces.append((a, d, b))
            faces.append((b, d, e))
    return _as_mesh(vertices, faces)


def capsule(a, b, radius):
    """Cylinder with spherical caps; used for rods, spokes and arms."""
    return combine(cylinder(a, b, radius, 16),
                   sphere(a, radius, 6, 12),
                   sphere(b, radius, 6, 12))


def x_tube(length, outer_radius, inner_radius, segments=32):
    """Hollow tube along the local X axis, centered at the origin."""
    x0, x1 = -length / 2, length / 2
    vertices = []
    faces = []
    for x, r in ((x0, outer_radius), (x1, outer_radius), (x0, inner_radius), (x1, inner_radius)):
        for i in range(segments):
            t = 2 * math.pi * i / segments
            vertices.append(np.array([x, r * math.cos(t), r * math.sin(t)]))
    for i in range(segments):
        j = (i + 1) % segments
        # outer wall, inner wall, and annular end rings
        faces.append((i, j, segments + j))
        faces.append((i, segments + j, segments + i))
        faces.append((2 * segments + i, 3 * segments + i, 3 * segments + j))
        faces.append((2 * segments + i, 3 * segments + j, 2 * segments + j))
        faces.append((i, 2 * segments + i, 2 * segments + j))
        faces.append((i, 2 * segments + j, j))
        faces.append((segments + i, segments + j, 3 * segments + j))
        faces.append((segments + i, 3 * segments + j, 3 * segments + i))
    return _as_mesh(vertices, faces)


def torus_y(major_radius, minor_radius, segments=72, sides=10):
    """Torus in the local XZ plane (revolution about the Y axis)."""
    vertices = []
    faces = []
    for i in range(segments):
        t = 2 * math.pi * i / segments
        for j in range(sides):
            q = 2 * math.pi * j / sides
            vertices.append(np.array([
                (major_radius + minor_radius * math.cos(q)) * math.cos(t),
                minor_radius * math.sin(q),
                (major_radius + minor_radius * math.cos(q)) * math.sin(t)]))
    for i in range(segments):
        ni = (i + 1) % segments
        for j in range(sides):
            nj = (j + 1) % sides
            a = i * sides + j
            b = ni * sides + j
            c = ni * sides + nj
            d = i * sides + nj
            faces.append((a, b, c))
            faces.append((a, c, d))
    return _as_mesh(vertices, faces)


def gear_wheel(teeth, root_radius, tip_radius, thickness):
    """Approximate toothed wheel in the local XZ plane (axis along Y).

    The profile is a trapezoidal visual approximation: each tooth rises
    from the root circle to a short tip plateau and falls back, with a
    root gap between teeth. It is meant for illustration only; it is not
    an involute and does not model tooth contact. Tooth ``k`` starts at
    local angle ``2*pi*k/teeth`` (measured from +X toward +Z) and its tip
    plateau is centered 0.325 pitches after the tooth start.
    """
    # Fractions of one pitch: root start, tip lead, tip trail, root end.
    offsets = (0.0, 0.2, 0.45, 0.65)
    radii = (root_radius, tip_radius, tip_radius, root_radius)
    profile = []
    for k in range(teeth):
        pitch = 2 * math.pi / teeth
        a0 = k * pitch
        for frac, r in zip(offsets, radii):
            a = a0 + frac * pitch
            profile.append((r * math.cos(a), r * math.sin(a)))
    n = len(profile)
    half = thickness / 2
    vertices = []
    for x, z in profile:
        vertices.append(np.array([x, -half, z]))
    for x, z in profile:
        vertices.append(np.array([x, half, z]))
    center_front = len(vertices)
    vertices.append(np.array([0.0, -half, 0.0]))
    center_back = len(vertices)
    vertices.append(np.array([0.0, half, 0.0]))
    faces = []
    for i in range(n):
        j = (i + 1) % n
        # side wall
        faces.append((i, j, n + j))
        faces.append((i, n + j, n + i))
        # caps as triangle fans
        faces.append((center_front, j, i))
        faces.append((center_back, n + i, n + j))
    return _as_mesh(vertices, faces)


def translation(x, y, z):
    m = np.eye(4)
    m[:3, 3] = [x, y, z]
    return m


def rotation_y(theta):
    """Rigid rotation about the Y axis; maps +X toward -Z for theta > 0."""
    c, s = math.cos(theta), math.sin(theta)
    m = np.eye(4)
    m[:3, :3] = [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
    return m
