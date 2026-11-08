"""Sampled mesh-pair clearance and interpenetration checks.

These helpers measure distances between placed triangle meshes. They run
at a finite set of cycle phases; that is sampled evidence, not a
continuous-time collision proof. Where a pair is reported clear for the
whole cycle by argument (rotation-invariant Y slabs, coaxial fits), the
report marks that result analytic instead.

Conventions:
- ``pair_clearance`` returns ``(distance, interpenetrating)``. The distance
  is the minimum over vertex-face and edge-edge queries (exact for
  polygonal meshes), so ``distance > 0`` at a phase rigorously excludes
  contact at that phase. ``interpenetrating`` counts strict edge-triangle
  crossings; tangent contact is not flagged. (A mesh fully containing
  another without any face crossing is not detected; no such pair exists
  in this assembly, and every pair starts the cycle disjoint.)
- If the part AABBs are separated, the AABB gap is a valid lower bound on
  the true clearance and is returned directly.
- Declared joint allowances are Y-aligned cylindrical zones (a pin
  housing). Queries whose measurement point lies inside a zone are
  skipped: a vertex-face query counts only if the vertex is outside every
  zone, an edge-edge query counts only if the midpoint of the closest
  point pair is outside, and an edge-triangle crossing counts only if the
  crossing point is outside. This permits modeled joint material inside
  the housings (pin surrounded by the rod eye) while still checking the
  full geometry elsewhere; triangle granularity cannot leak past it.
"""
import numpy as np

_EPS = 1e-9


def aabb(vertices):
    return vertices.min(axis=0), vertices.max(axis=0)


def aabb_gap(lo_a, hi_a, lo_b, hi_b):
    """Exact distance between two AABBs (0 when they overlap)."""
    d = np.maximum(np.maximum(lo_a - hi_b, lo_b - hi_a), 0.0)
    return float(np.linalg.norm(d))


def _outside_zones(P, zones):
    """Boolean mask of points outside every declared joint zone."""
    if not zones:
        return np.ones(len(P), dtype=bool)
    keep = np.ones(len(P), dtype=bool)
    for center, radius, y_half in zones:
        rho = np.sqrt((P[:, 0] - center[0]) ** 2 + (P[:, 2] - center[2]) ** 2)
        inside = (rho <= radius) & (np.abs(P[:, 1] - center[1]) <= y_half)
        keep &= ~inside
    return keep


# ---------------------------------------------------------------------------
# vectorized distance kernels
# ---------------------------------------------------------------------------

def _point_tri_dist2(P, A, B, C):
    """Squared distances from points P (m,3) to triangles (A,B,C) (n,3).

    Returns (m, n). Ericson, Real-Time Collision Detection, section 5.1.5,
    with the exact minimum taken over the face projection (when the
    barycentric point is inside) and all clamped edge/vertex candidates.
    """
    AP = P[:, None, :] - A[None, :, :]          # (m,n,3)
    AB = B - A                                  # (n,3)
    AC = C - A
    BC = C - B

    a = np.einsum("ij,ij->i", AB, AB)
    b = np.einsum("ij,ij->i", AB, AC)
    c = np.einsum("ij,ij->i", AC, AC)
    d1 = np.einsum("mnj,nj->mn", AP, AB)
    d2 = np.einsum("mnj,nj->mn", AP, AC)
    denom = a * c - b * b
    denom = np.where(np.abs(denom) < 1e-30, 1e-30, denom)
    v = (c * d1 - b * d2) / denom               # (m,n)
    w = (a * d2 - b * d1) / denom
    u = 1.0 - v - w

    inside = (u >= 0) & (v >= 0) & (w >= 0)
    Q_face = A[None, :, :] + v[:, :, None] * AB[None, :, :] + w[:, :, None] * AC[None, :, :]

    t_ab = np.clip(d1 / np.where(a < 1e-30, 1e-30, a)[None, :], 0.0, 1.0)
    Q_ab = A[None, :, :] + t_ab[:, :, None] * AB[None, :, :]
    t_ac = np.clip(d2 / np.where(c < 1e-30, 1e-30, c)[None, :], 0.0, 1.0)
    Q_ac = A[None, :, :] + t_ac[:, :, None] * AC[None, :, :]
    BP = P[:, None, :] - B[None, :, :]
    d3 = np.einsum("mnj,nj->mn", BP, BC)
    e_bc = np.einsum("ij,ij->i", BC, BC)
    t_bc = np.clip(d3 / np.where(e_bc < 1e-30, 1e-30, e_bc)[None, :], 0.0, 1.0)
    Q_bc = B[None, :, :] + t_bc[:, :, None] * BC[None, :, :]

    dist2 = np.where(
        inside,
        np.einsum("mnj,mnj->mn", P[:, None, :] - Q_face, P[:, None, :] - Q_face),
        np.inf)
    for Q in (Q_ab, Q_ac, Q_bc):
        dd = P[:, None, :] - Q
        dist2 = np.minimum(dist2, np.einsum("mnj,mnj->mn", dd, dd))
    for Q in (A, B, C):
        dd = P[:, None, :] - Q[None, :, :]
        dist2 = np.minimum(dist2, np.einsum("mnj,mnj->mn", dd, dd))
    return dist2


def _seg_seg_dist2_mid(P1, Q1, P2, Q2):
    """Squared distances and closest-pair midpoints for segment pairs.

    P1,Q1 are (m,3), P2,Q2 are (n,3); returns (m,n) dist2 and (m,n,3)
    midpoints. Ericson 5.1.9 vectorized; degenerate segments clamp.
    """
    d1 = Q1 - P1                                # (m,3)
    d2 = Q2 - P2                                # (n,3)
    r = P1[:, None, :] - P2[None, :, :]         # (m,n,3)
    a = np.einsum("ij,ij->i", d1, d1)           # (m,)
    e = np.einsum("ij,ij->i", d2, d2)           # (n,)
    f = np.einsum("nj,mnj->mn", d2, r)
    c = np.einsum("mj,mnj->mn", d1, r)
    b = np.einsum("mj,nj->mn", d1, d2)          # (m,n)
    aa = np.broadcast_to(a[:, None], b.shape)
    ee = np.broadcast_to(e[None, :], b.shape)
    denom = aa * ee - b * b
    denom_safe = np.where(np.abs(denom) < 1e-30, 1.0, denom)
    s = np.where(np.abs(denom) < 1e-30, 0.0, (b * f - c * ee) / denom_safe)
    s = np.clip(s, 0.0, 1.0)
    t = (b * s + f) / np.where(ee < 1e-30, 1e-30, ee)
    t = np.clip(t, 0.0, 1.0)
    s = (b * t - c) / np.where(aa < 1e-30, 1e-30, aa)
    s = np.clip(s, 0.0, 1.0)
    c1 = P1[:, None, :] + s[:, :, None] * d1[:, None, :]
    c2 = P2[None, :, :] + t[:, :, None] * d2[None, :, :]
    diff = c1 - c2
    return np.einsum("mnj,mnj->mn", diff, diff), 0.5 * (c1 + c2)


def _edge_tri_crossing_points(P0, P1, A, B, C):
    """Strict edge-triangle intersections (Möller–Trumbore).

    Returns (hit mask (m,n), crossing points (m,n,3)). Only crossings
    strictly inside both the edge and the triangle count, so resting or
    tangent contact does not flag.
    """
    D = P1 - P0                                 # (m,3)
    E1 = B - A
    E2 = C - A
    T = P0[:, None, :] - A[None, :, :]          # (m,n,3)
    Pv = np.cross(D[:, None, :], E2[None, :, :])
    det = np.einsum("nj,mnj->mn", E1, Pv)
    Qv = np.cross(T, E1[None, :, :])
    inv = np.where(np.abs(det) > _EPS, 1.0 / np.where(np.abs(det) > _EPS, det, 1.0), 0.0)
    u = np.einsum("mnj,mnj->mn", T, Pv) * inv
    v = np.einsum("mj,mnj->mn", D, Qv) * inv
    t = np.einsum("nj,mnj->mn", E2, Qv) * inv
    hit = (np.abs(det) > _EPS) & (u > 1e-7) & (v > 1e-7) & (u + v < 1 - 1e-7) \
        & (t > 1e-7) & (t < 1 - 1e-7)
    points = P0[:, None, :] + t[:, :, None] * D[:, None, :]
    return hit, points


def _unique_edges(faces):
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]], axis=0)
    e = np.sort(e, axis=1)
    return np.unique(e, axis=0)


def pair_clearance(VA, FA, VB, FB, zones=(), chunk_points=512):
    """Minimum surface distance and strict interpenetration between meshes.

    ``zones`` is a sequence of ``(center, radius, y_half)`` Y-aligned
    cylindrical joint allowances; measurements taken inside a zone do not
    count (see module docstring).
    """
    lo_a, hi_a = aabb(VA)
    lo_b, hi_b = aabb(VB)
    gap = aabb_gap(lo_a, hi_a, lo_b, hi_b)
    if gap > 0.0:
        return gap, False                    # conservative lower bound, exact for AABBs

    best = np.inf
    TA, TB = VA[FA], VB[FB]                  # (na,3,3), (nb,3,3)

    # vertex-face, both directions; only vertices outside the zones query
    for P, TT in ((VA, TB), (VB, TA)):
        A, B, C = TT[:, 0], TT[:, 1], TT[:, 2]
        for start in range(0, len(P), chunk_points):
            Pc = P[start:start + chunk_points]
            keep = _outside_zones(Pc, zones)
            if not keep.any():
                continue
            d2 = _point_tri_dist2(Pc[keep], A, B, C)
            best = min(best, float(d2.min()))

    # edge-edge; a query counts only when the closest-pair midpoint is
    # outside every zone
    EA, EB = _unique_edges(FA), _unique_edges(FB)
    SA0, SA1 = VA[EA[:, 0]], VA[EA[:, 1]]
    SB0, SB1 = VB[EB[:, 0]], VB[EB[:, 1]]
    for start in range(0, len(SA0), chunk_points):
        d2, mid = _seg_seg_dist2_mid(SA0[start:start + chunk_points],
                                     SA1[start:start + chunk_points], SB0, SB1)
        flat = d2.reshape(-1)
        keep = _outside_zones(mid.reshape(-1, 3), zones)
        if keep.any():
            best = min(best, float(flat[keep].min()))

    # strict interpenetration: edge crossings both directions, counted
    # only when the crossing point is outside every zone
    inter = False
    for E0, E1, TT in ((SA0, SA1, TB), (SB0, SB1, TA)):
        A, B, C = TT[:, 0], TT[:, 1], TT[:, 2]
        for start in range(0, len(E0), chunk_points):
            hit, points = _edge_tri_crossing_points(
                E0[start:start + chunk_points], E1[start:start + chunk_points], A, B, C)
            if hit.any():
                flat_hit = hit.reshape(-1)
                keep = _outside_zones(points.reshape(-1, 3), zones)
                if (flat_hit & keep).any():
                    inter = True
                    break
        if inter:
            break
    return (float(np.sqrt(best)) if np.isfinite(best) else float("inf")), inter
