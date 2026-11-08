"""Corrected steam-engine slider-crank with a coherent axial layout.

Regression being fixed: ``mechflow.cases.SliderCrankProvider`` places the
flywheel with the crank's *complete* transform (copied here at
``mechflow/cases.py:181``), which collapsed the 34 model units of axial
separation used by the verified reference study
(``steam-engine-v2/render_study.py:91`` places the flywheel at
``center + (0, 34, 0)``). Sharing the transform put the flywheel rim and
spokes in the connecting-rod plane (rod/spoke and crosshead/rim
intersections) and left the crankshaft passing through solid, unbored
bearing bosses.

This provider restores the axial stack along the Y shaft axis and models
the fits the layout implies (all dimensions in model units, Z up, Y along
the shaft):

    rod plane y=0
      big end |y|<=7.5 (bored, pin clearance 0.2)
      crank webs y in [8.5, 15.5]  (gap 1.0 to the big end)
      shaft stubs |y| >= 11        (no shaft crosses the rod plane, so the
                                    rod sweep never meets a shaft segment)
      bearing bosses y in [17, 27] (bored tubes, shaft clearance 0.5)
      flywheel hub y in [30.5, 37.5] (bored, clearance 0.5), rim y in [30, 38]
      retaining nut y in [38, 41] (bored, clearance 0.2), shaft ends at 42

Further fixes relative to the source scene:

- the crosshead is two cheek plates plus a wrist pin, so the rod small
  end sits in a modeled bore (clearance 0.2) instead of inside a solid box;
- the cylinder is shortened so the crosshead cheeks never enter the bore
  shell, and the valve chest is moved to the head end so the piston head
  cannot strike it;
- crosshead guides (rails and posts) are restored as a fixed part.

All local meshes are built once; frames update rigid transforms only.
Frame residuals measure geometric closure, never force or steam. Static
mounts (stands, cradle feet and guide posts embedded 0.5 into the base)
are declared joints; every other part pair carries positive clearance.
"""
import math

import numpy as np

from . import mesh as prim
from .cases import _check_phase, _finite, _positive
from .types import Frame, Mesh, Part


def y_tube(center_x, center_z, y0, y1, outer_radius, inner_radius, segments=32):
    """Hollow tube along the Y axis, centered on (``center_x``, ``center_z``).

    ``mesh.x_tube`` only builds along X, and the copied ``mesh.py`` must
    stay byte-identical to the original, so the Y variant lives here.
    """
    vertices = []
    faces = []
    for y, r in ((y0, outer_radius), (y1, outer_radius),
                 (y0, inner_radius), (y1, inner_radius)):
        for i in range(segments):
            t = 2 * math.pi * i / segments
            vertices.append(np.array([center_x + r * math.cos(t), y,
                                      center_z + r * math.sin(t)]))
    for i in range(segments):
        j = (i + 1) % segments
        faces.append((i, j, segments + j))
        faces.append((i, segments + j, segments + i))
        faces.append((2 * segments + i, 3 * segments + i, 3 * segments + j))
        faces.append((2 * segments + i, 3 * segments + j, 2 * segments + j))
        faces.append((i, 2 * segments + i, 2 * segments + j))
        faces.append((i, 2 * segments + j, j))
        faces.append((segments + i, segments + j, 3 * segments + j))
        faces.append((segments + i, 3 * segments + j, 3 * segments + i))
    return Mesh(vertices=np.asarray(vertices, dtype=float),
                faces=np.asarray(faces, dtype=np.int64))


class SteamEngineProvider:
    """Mounted slider-crank steam engine with restored axial separation.

    Defaults reproduce the source scene's kinematics (crank radius 16,
    rod 64, piston rod 50, crank center x=40, axis z=65); only the axial
    layout and the fits are redesigned. Kinematics are identical in form
    to the verified reference: the crank pin is a fixed local point under
    a single rotation per cycle and the connecting rod is placed rigidly
    so both pin endpoints coincide exactly.
    """

    def __init__(self, crank_radius=16.0, rod_length=64.0, piston_rod_length=50.0,
                 center_x=40.0, axis_z=65.0):
        self.crank_radius = _positive("crank_radius", crank_radius)
        self.rod_length = _positive("rod_length", rod_length)
        self.piston_rod_length = _positive("piston_rod_length", piston_rod_length)
        self.center_x = _finite("center_x", center_x)
        self.axis_z = _finite("axis_z", axis_z)
        if not self.crank_radius < self.rod_length:
            raise ValueError(
                "rod_length must exceed crank_radius; the slider cannot close "
                f"otherwise (crank_radius={self.crank_radius}, rod_length={self.rod_length})")

        r, L, prol = self.crank_radius, self.rod_length, self.piston_rod_length
        cx, az = self.center_x, self.axis_z

        # --- axial layout constants (world Y unless noted) -----------------
        self.flywheel_y = 34.0            # hub symmetry plane; reference used +34
        self.rod_plane_y = 0.0
        self.axial_separation = self.flywheel_y - self.rod_plane_y
        self.shaft_radius = 5.0
        self.shaft_pos_span = (11.0, 42.0)    # stub outboard of +Y web, reaches nut
        self.shaft_neg_span = (-30.0, -11.0)  # stub outboard of -Y web
        self.web_y = 12.0
        self.web_radius = 3.5              # web slabs: [8.5, 15.5] and mirrored
        self.pin_radius = 4.2
        self.pin_span = (-12.0, 12.0)      # pin ends sit inside the web capsules
        self.boss_bore = 5.5               # bored, shaft clearance 0.5
        self.boss_outer = 10.0
        self.boss_spans = ((-27.0, -17.0), (17.0, 27.0))
        self.hub_bore = 5.5                # bored, shaft clearance 0.5
        self.hub_outer = 9.0
        self.hub_span = (30.5, 37.5)
        self.nut_bore = 5.2                # bored, shaft clearance 0.2
        self.nut_outer = 7.0
        self.nut_span = (38.0, 41.0)
        self.big_end_outer = 6.0
        self.big_end_bore = 4.4            # pin clearance 0.2
        self.big_end_span = (-7.5, 7.5)
        self.small_end_outer = 5.0
        self.small_end_bore = 4.2          # wrist pin clearance 0.2
        self.small_end_span = (-8.0, 8.0)
        self.wrist_pin_radius = 4.0
        self.shank_radius = 4.2
        self.shank_start = -5.5            # shank blends into the big-end housing
        self.shank_end = -L + 4.6          # flat end remains outside the small bore
        self.fly_major = r + 25.0
        self.fly_minor = 4.0

        # --- slider extremes and the cylinder sized around them ------------
        # Crosshead extremes are exactly at theta = 0 and pi.
        head_half = 6.5
        margin = 12.0
        crosshead_min = cx - r - L
        crosshead_max = cx + r - L
        head_min = crosshead_min - prol - head_half
        head_max = crosshead_max - prol + head_half
        cheek_half_x = 9.0
        plate_half_x = 10.0                # backing plate reaches furthest
        end_gap = 0.5                      # plate/cheek face to cylinder end face
        cyl_x1 = crosshead_min - plate_half_x - end_gap
        cyl_x0 = head_min - margin
        cyl_len = cyl_x1 - cyl_x0
        cyl_cx = (cyl_x0 + cyl_x1) / 2
        self.cylinder_bore = 13.5
        self.cylinder_outer = 17.0
        self.cylinder_span = (cyl_x0, cyl_x1)
        self.head_radius = 13.0            # radial clearance 0.5 in the bore
        self.crosshead_travel = (crosshead_min, crosshead_max)
        self.head_travel = (head_min, head_max)
        self.head_end_margin = cyl_x1 - head_max   # 1.0 with the defaults

        # --- static parts ---------------------------------------------------
        base_x0 = cyl_x0 - 15.0
        base_x1 = cx + self.fly_major + 24.0
        self.base_top_z = 14.0
        base = prim.box(((base_x0 + base_x1) / 2, 0.0, 7.0),
                        (base_x1 - base_x0, 78.0, 14.0))

        # Bearing stands and bored bosses; cylinder cradle supports sit 0.5
        # below the tube wall (no embed) while stand/cradle feet embed 0.5
        # into the base top (declared static mounts, verified analytically).
        stand_top = az - 8.0
        frame_parts = []
        for sy in (-23.0, 23.0):
            frame_parts.append(prim.box((cx, sy, (13.5 + stand_top) / 2),
                                        (18.0, 12.0, stand_top - 13.5)))
        for span in self.boss_spans:
            frame_parts.append(y_tube(cx, az, span[0], span[1],
                                      self.boss_outer, self.boss_bore, 32))
        self.cradle_top_z = az - self.cylinder_outer - 0.5
        for sx in (-95.0, -63.0):
            frame_parts.append(prim.box(
                (sx, 0.0, (13.5 + self.cradle_top_z) / 2),
                (14.0, 30.0, self.cradle_top_z - 13.5)))
        frame = prim.combine(*frame_parts)

        # Crosshead guides: two rails on the slider line, posts to the base.
        self.guide_y = 15.5                # rail centerlines; inner face at 13.0
        self.guide_radius = 2.5
        self.guide_span_x = (-39.0, 4.0)
        rail_x0, rail_x1 = self.guide_span_x
        guide_parts = []
        for sy in (-self.guide_y, self.guide_y):
            guide_parts.append(prim.cylinder(
                (rail_x0, sy, az), (rail_x1, sy, az), self.guide_radius, 16))
            for sx in (-38.0, 4.0):
                guide_parts.append(prim.box((sx, sy, (13.5 + az) / 2),
                                            (4.0, 5.0, az - 13.5)))
        guides = prim.combine(*guide_parts)

        # Cylinder with valve chest at the head end, clear of head travel.
        valve_cx_local = (cyl_x0 + 1.0 + 5.0) - cyl_cx   # 10-long chest, 1.0 off the end
        cylinder = prim.combine(
            prim.x_tube(cyl_len, self.cylinder_outer, self.cylinder_bore),
            prim.box((valve_cx_local, 0.0, 20.0), (10.0, 26.0, 15.0)),
            prim.cylinder((valve_cx_local, 0.0, 27.0), (valve_cx_local, 0.0, 41.0), 4.0, 20))
        self.valve_span = (cyl_x0 + 1.0, cyl_x0 + 11.0)

        # --- moving parts ----------------------------------------------------
        # Piston and crosshead: two cheek plates leave a real slot for the
        # rod small end; the wrist pin is part of this rigid body.
        piston = prim.combine(
            prim.box((0.0, 10.25, 0.0), (18.0, 3.5, 20.0)),
            prim.box((0.0, -10.25, 0.0), (18.0, 3.5, 20.0)),
            prim.box((-8.75, 0.0, 0.0), (2.5, 24.0, 20.0)),
            prim.cylinder((0.0, -12.0, 0.0), (0.0, 12.0, 0.0), self.wrist_pin_radius, 20),
            prim.cylinder((-9.0, 0.0, 0.0), (-prol + head_half, 0.0, 0.0), 3.6, 20),
            prim.cylinder((-prol - head_half, 0.0, 0.0), (-prol + head_half, 0.0, 0.0),
                          self.head_radius, 40))

        # Crankshaft: pin and webs between the bearing lines, shaft stubs
        # only outboard of the webs so nothing crosses the rod plane.
        crank_parts = [
            prim.cylinder((0.0, self.shaft_pos_span[0], 0.0),
                          (0.0, self.shaft_pos_span[1], 0.0), self.shaft_radius, 24),
            prim.cylinder((0.0, self.shaft_neg_span[0], 0.0),
                          (0.0, self.shaft_neg_span[1], 0.0), self.shaft_radius, 24),
        ]
        for y in (-self.web_y, self.web_y):
            crank_parts.append(prim.capsule((0.0, y, 0.0), (-r, y, 0.0), self.web_radius))
        crank_parts.append(prim.cylinder(
            (-r, self.pin_span[0], 0.0), (-r, self.pin_span[1], 0.0), self.pin_radius, 24))
        crank = prim.combine(*crank_parts)

        # Flywheel in its own local frame; placed at y = +34 on the shaft.
        wheel_parts = [prim.torus_y(self.fly_major, self.fly_minor)]
        for i in range(8):
            a = 2 * math.pi * i / 8
            # Spokes run from the hub shell outward; starting them at the
            # axis would drive them through the shaft (crank x flywheel
            # interpenetration, caught by the mesh checker).
            wheel_parts.append(prim.capsule(
                (self.hub_outer * math.cos(a), 0.0, self.hub_outer * math.sin(a)),
                ((self.fly_major - 4.0) * math.cos(a), 0.0,
                 (self.fly_major - 4.0) * math.sin(a)), 3.0))
        wheel_parts.append(y_tube(0.0, 0.0, self.hub_span[0] - self.flywheel_y,
                                  self.hub_span[1] - self.flywheel_y,
                                  self.hub_outer, self.hub_bore, 32))
        wheel_parts.append(y_tube(0.0, 0.0, self.nut_span[0] - self.flywheel_y,
                                  self.nut_span[1] - self.flywheel_y,
                                  self.nut_outer, self.nut_bore, 24))
        flywheel = prim.combine(*wheel_parts)

        # Fixed local rod: big-end housing at the origin, small end at
        # (-rod_length, 0, 0); both housings are bored tubes.
        rod = prim.combine(
            # A separate ring cannot subtract a capsule's spherical caps.
            # Flat ends overlap the outer eye walls without filling either bore.
            prim.cylinder((self.shank_start, 0.0, 0.0),
                          (self.shank_end, 0.0, 0.0), self.shank_radius, 24),
            y_tube(0.0, 0.0, self.big_end_span[0], self.big_end_span[1],
                   self.big_end_outer, self.big_end_bore, 28),
            _shift_y_tube(-L, self.small_end_span, self.small_end_outer,
                          self.small_end_bore, 24))

        self._meshes = {
            "base": ("Base", "base", base),
            "frame": ("Bearing stands and bosses", "frame", frame),
            "guides": ("Crosshead guides", "frame", guides),
            "cylinder": ("Cylinder", "steel", cylinder),
            "piston": ("Piston and crosshead", "steel", piston),
            "crank": ("Crankshaft", "accent", crank),
            "flywheel": ("Flywheel", "brass", flywheel),
            "rod": ("Connecting rod", "accent", rod),
        }
        self._cylinder_x = cyl_cx

    def frame(self, phase):
        phase = _check_phase(phase)
        r, L, prol = self.crank_radius, self.rod_length, self.piston_rod_length
        cx, az = self.center_x, self.axis_z
        theta = 2 * math.pi * phase

        center = np.array([cx, 0.0, az])
        shaft = prim.translation(cx, 0.0, az) @ prim.rotation_y(theta)
        pin = center + shaft[:3, :3] @ np.array([-r, 0.0, 0.0])
        reach = math.sqrt(L * L - (pin[2] - az) ** 2)
        crosshead = np.array([pin[0] - reach, 0.0, az])
        piston = crosshead - np.array([prol, 0.0, 0.0])

        # Rigid rod placement: local origin to the crank pin, local -X to the crosshead.
        rod_angle = math.atan2(az - pin[2], reach)
        rod_transform = prim.translation(*pin) @ prim.rotation_y(rod_angle)
        # The flywheel shares the shaft rotation but sits 34 units along +Y.
        flywheel_transform = (prim.translation(cx, self.flywheel_y, az)
                              @ prim.rotation_y(theta))

        transforms = {
            "base": np.eye(4),
            "frame": np.eye(4),
            "guides": np.eye(4),
            "cylinder": prim.translation(self._cylinder_x, 0.0, az),
            "piston": prim.translation(crosshead[0], 0.0, az),
            "crank": shaft,
            "flywheel": flywheel_transform,
            "rod": rod_transform,
        }
        parts = tuple(
            Part(id=pid, label=label, material=material, mesh=m, transform=transforms[pid])
            for pid, (label, material, m) in self._meshes.items())

        def placed(pid, local):
            t = transforms[pid]
            return t[:3, :3] @ np.asarray(local, dtype=float) + t[:3, 3]

        residuals = {
            "rod_closure": abs(float(np.linalg.norm(pin - crosshead)) - L),
            "crank_radius": abs(float(np.linalg.norm(pin - center)) - r),
            "rod_big_end": float(np.linalg.norm(placed("rod", (0.0, 0.0, 0.0)) - pin)),
            "rod_small_end": float(np.linalg.norm(placed("rod", (-L, 0.0, 0.0)) - crosshead)),
            "flywheel_axial": abs(float(flywheel_transform[1, 3]) - self.flywheel_y),
            "flywheel_spin": float(np.linalg.norm(
                flywheel_transform[:3, :3] - shaft[:3, :3])),
        }
        joints = {
            "crank_center": center,
            "crank_pin": pin,
            "crosshead": crosshead,
            "piston": piston,
            "flywheel_center": np.array([cx, self.flywheel_y, az]),
        }
        return Frame(phase=phase, parts=parts, joints=joints, residuals=residuals)


def _shift_y_tube(dx, span, outer, inner, segments):
    """``y_tube`` translated by ``dx`` along X (for the rod small end)."""
    m = y_tube(0.0, 0.0, span[0], span[1], outer, inner, segments)
    vertices = m.vertices.copy()
    vertices[:, 0] += dx
    return Mesh(vertices=vertices, faces=np.array(m.faces, copy=True))
