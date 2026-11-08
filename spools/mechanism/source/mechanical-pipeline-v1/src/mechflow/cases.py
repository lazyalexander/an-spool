"""Scene providers for the reusable visualization slice.

``make_provider`` builds a :class:`mechflow.types.SceneProvider` from the
dictionary stored under the ``source`` key of an example scene file.
Providers own kinematics, stable part identities and material *categories*
only; color, shading and export policy live elsewhere.

Both providers build every local mesh once at construction time and only
update rigid 4x4 transforms per frame, so local geometry stays constant
through the whole cycle. Frame residuals measure geometric closure (rod
length, joint placement, prescribed gear ratio), never force or steam.
"""
import math

import numpy as np

from . import mesh as prim
from .types import Frame, Part

MATERIAL_CATEGORIES = ("base", "frame", "steel", "accent", "brass")


def _finite(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    x = float(value)
    if not math.isfinite(x):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return x


def _positive(name, value):
    x = _finite(name, value)
    if not 1e-3 <= x <= 1e4:
        raise ValueError(f"{name} must be in the visual fixture range [0.001, 10000], got {value!r}")
    return x


def _tooth_count(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be an integer, got {value!r}")
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            raise ValueError(f"{name} must be an integer, got {value!r}")
        value = int(value)
    if value < 4:
        raise ValueError(f"{name} must be at least 4, got {value!r}")
    if value > 512:
        raise ValueError(f"{name} exceeds the visual fixture limit of 512")
    return value


def _check_phase(phase):
    if isinstance(phase, bool) or not isinstance(phase, (int, float)):
        raise ValueError(f"phase must be a number in [0, 1], got {phase!r}")
    phase = float(phase)
    if not math.isfinite(phase) or not 0.0 <= phase <= 1.0:
        raise ValueError(f"phase must be in [0, 1], got {phase!r}")
    return phase


def _rotation_y_angle(transform):
    """Recover the Y-rotation angle of a ``translate @ rotation_y`` matrix."""
    return math.atan2(transform[0, 2], transform[0, 0])


class SliderCrankProvider:
    """Mounted visual steam-engine style slider-crank.

    The crank and flywheel share one shaft and perform a single local
    rotation per cycle (adapted from the verified reference kinematics).
    The connecting rod is a fixed local mesh placed rigidly so its two
    pin endpoints coincide exactly with the crank pin and the crosshead.
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

        # Piston head travel extremes occur at theta = 0 and pi.
        head_min = cx - r - L - prol
        head_max = cx + r - L - prol
        margin = 12.0
        head_half = 6.5
        cyl_len = (head_max - head_min) + 2 * margin + 2 * head_half
        cyl_cx = (head_min + head_max) / 2

        fly_major = r + 25.0
        base_x0 = cyl_cx - cyl_len / 2 - 15.0
        base_x1 = cx + fly_major + 24.0

        base = prim.box(((base_x0 + base_x1) / 2, 0.0, 7.0),
                        (base_x1 - base_x0, 78.0, 14.0))

        stands = []
        stand_bottom, stand_top = 13.0, az - 8.0
        for sy in (-15.0, 15.0):
            stands.append(prim.box((cx, sy, (stand_bottom + stand_top) / 2),
                                   (18.0, 17.0, stand_top - stand_bottom)))
            stands.append(prim.cylinder((cx, sy - 9.0, az), (cx, sy + 9.0, az), 10.0, 32))
        frame = prim.combine(*stands)

        cylinder = prim.combine(
            prim.x_tube(cyl_len, 17.0, 13.5),
            # valve chest and a short inlet pipe stay attached to the cylinder
            prim.box((-2.0, 0.0, 20.0), (18.0, 26.0, 15.0)),
            prim.cylinder((-3.0, 0.0, 27.0), (-3.0, 0.0, 41.0), 4.0, 20))

        piston = prim.combine(
            prim.box((0.0, 0.0, 0.0), (18.0, 24.0, 20.0)),
            prim.cylinder((-9.0, 0.0, 0.0), (-prol + head_half, 0.0, 0.0), 3.6, 20),
            prim.cylinder((-prol - head_half, 0.0, 0.0), (-prol + head_half, 0.0, 0.0), 13.0, 40))

        # One fixed local crank with its pin at (-crank_radius, 0, 0).
        crank_parts = [prim.cylinder((0.0, -27.0, 0.0), (0.0, 27.0, 0.0), 5.0, 24)]
        for y in (-10.0, 10.0):
            crank_parts.append(prim.capsule((0.0, y, 0.0), (-r, y, 0.0), 4.3))
        crank_parts.append(prim.cylinder((-r, -20.0, 0.0), (-r, 20.0, 0.0), 4.2, 24))
        crank = prim.combine(*crank_parts)

        wheel_parts = [prim.torus_y(fly_major, 4.0)]
        for i in range(8):
            a = 2 * math.pi * i / 8
            wheel_parts.append(prim.capsule(
                (0.0, 0.0, 0.0),
                ((fly_major - 4.0) * math.cos(a), 0.0, (fly_major - 4.0) * math.sin(a)), 3.0))
        wheel_parts.append(prim.torus_y(7.0, 3.0))
        flywheel = prim.combine(*wheel_parts)

        # Fixed local rod: big end at the origin, small end at (-rod_length, 0, 0).
        rod = prim.combine(
            prim.capsule((0.0, 0.0, 0.0), (-L, 0.0, 0.0), 4.2),
            prim.cylinder((0.0, -10.0, 0.0), (0.0, 10.0, 0.0), 6.0, 24),
            prim.cylinder((-L, -8.0, 0.0), (-L, 8.0, 0.0), 5.0, 24))

        self._meshes = {
            "base": ("Base", "base", base),
            "frame": ("Bearing stands", "frame", frame),
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

        transforms = {
            "base": np.eye(4),
            "frame": np.eye(4),
            "cylinder": prim.translation(self._cylinder_x, 0.0, az),
            "piston": prim.translation(crosshead[0], 0.0, az),
            "crank": shaft,
            "flywheel": shaft,
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
        }
        joints = {
            "crank_center": center,
            "crank_pin": pin,
            "crosshead": crosshead,
            "piston": piston,
        }
        return Frame(phase=phase, parts=parts, joints=joints, residuals=residuals)


class GearPairProvider:
    """Two-shaft external gear pair with approximate visual teeth.

    Tooth counts set the angular velocity ratio: the pinion makes
    ``teeth_gear / gcd`` turns per cycle and the gear makes
    ``teeth_pinion / gcd`` turns in the opposite direction, so every
    transform closes exactly at phase 1 (defaults: two turns vs one turn).
    The wheel profiles are trapezoidal visual approximations (see
    :func:`mechflow.mesh.gear_wheel`); the gear is phased so a pinion
    tooth meets a gear gap at the pitch point at phase 0. No tooth-contact
    simulation is claimed.
    """

    def __init__(self, teeth_pinion=12, teeth_gear=24, module=4.0,
                 thickness=14.0, axis_z=65.0):
        self.teeth_pinion = _tooth_count("teeth_pinion", teeth_pinion)
        self.teeth_gear = _tooth_count("teeth_gear", teeth_gear)
        self.module = _positive("module", module)
        self.thickness = _positive("thickness", thickness)
        self.axis_z = _finite("axis_z", axis_z)

        np_, ng = self.teeth_pinion, self.teeth_gear
        m = self.module
        self.pitch_pinion = m * np_ / 2
        self.pitch_gear = m * ng / 2
        self.center_distance = self.pitch_pinion + self.pitch_gear
        g = math.gcd(np_, ng)
        self.turns_pinion = ng // g
        self.turns_gear = np_ // g

        # Phase offsets so a pinion tip plateau (0.325 pitches after the
        # tooth start) meets a gear root gap (0.825 pitches) at the pitch
        # point when phase = 0. rotation_y maps local angle a to world
        # angle a - theta, hence the signs below.
        self._pinion_offset = 0.325 * 2 * math.pi / np_
        self._gear_offset = 0.825 * 2 * math.pi / ng - math.pi

        az = self.axis_z
        cd = self.center_distance
        tip_gear = self.pitch_gear + m
        shaft_r = max(m, 2.5)

        def wheel(teeth, pitch):
            return prim.combine(
                prim.gear_wheel(teeth, pitch - m, pitch + m, self.thickness),
                prim.cylinder((0.0, -34.0, 0.0), (0.0, 34.0, 0.0), shaft_r, 24),
                prim.cylinder((0.0, -self.thickness / 2 - 4.0, 0.0),
                              (0.0, self.thickness / 2 + 4.0, 0.0), 2.5 * shaft_r, 24))

        pinion_mesh = prim.combine(
            wheel(np_, self.pitch_pinion),
            # hand crank on the pinion shaft, pointing away from the gear:
            # this is the driven input
            prim.capsule((0.0, -34.0, 0.0), (-2.2 * self.pitch_pinion, -34.0, 0.0), 3.0),
            prim.cylinder((-2.2 * self.pitch_pinion, -48.0, 0.0),
                          (-2.2 * self.pitch_pinion, -34.0, 0.0), 3.5, 20))
        gear_mesh = wheel(ng, self.pitch_gear)

        base_x0 = -self.pitch_pinion - m - 18.0
        base_x1 = cd + tip_gear + 18.0
        base = prim.box(((base_x0 + base_x1) / 2, 0.0, 7.0),
                        (base_x1 - base_x0, 78.0, 14.0))

        stands = []
        stand_bottom, stand_top = 13.0, az - 8.0
        for sx in (0.0, cd):
            for sy in (-22.0, 22.0):
                stands.append(prim.box((sx, sy, (stand_bottom + stand_top) / 2),
                                       (16.0, 14.0, stand_top - stand_bottom)))
                stands.append(prim.cylinder((sx, sy - 7.0, az), (sx, sy + 7.0, az), 8.0, 28))
        frame = prim.combine(*stands)

        self._meshes = {
            "base": ("Base", "base", base),
            "frame": ("Shaft supports", "frame", frame),
            "pinion": (f"Pinion {np_}T", "steel", pinion_mesh),
            "gear": (f"Gear {ng}T", "brass", gear_mesh),
        }

    def frame(self, phase):
        phase = _check_phase(phase)
        az = self.axis_z
        theta_pinion = 2 * math.pi * self.turns_pinion * phase + self._pinion_offset
        theta_gear = -2 * math.pi * self.turns_gear * phase + self._gear_offset

        pinion_center = np.array([0.0, 0.0, az])
        gear_center = np.array([self.center_distance, 0.0, az])
        transforms = {
            "base": np.eye(4),
            "frame": np.eye(4),
            "pinion": prim.translation(*pinion_center) @ prim.rotation_y(theta_pinion),
            "gear": prim.translation(*gear_center) @ prim.rotation_y(theta_gear),
        }
        parts = tuple(
            Part(id=pid, label=label, material=material, mesh=m, transform=transforms[pid])
            for pid, (label, material, m) in self._meshes.items())

        # Closure residuals derived from the actual placed transforms.
        a_pinion = _rotation_y_angle(transforms["pinion"])
        a_gear = _rotation_y_angle(transforms["gear"])
        const = (self.teeth_pinion * self._pinion_offset
                 + self.teeth_gear * self._gear_offset)
        mesh_phase = (self.teeth_pinion * a_pinion + self.teeth_gear * a_gear - const)
        mesh_phase = abs((mesh_phase + math.pi) % (2 * math.pi) - math.pi)
        residuals = {
            "mesh_phase": mesh_phase,
            "center_distance": abs(float(np.linalg.norm(gear_center - pinion_center))
                                   - self.center_distance),
            "ratio": abs(self.turns_pinion * self.teeth_pinion
                         - self.turns_gear * self.teeth_gear),
        }
        joints = {
            "pinion_center": pinion_center,
            "gear_center": gear_center,
            "pitch_point": np.array([self.pitch_pinion, 0.0, az]),
        }
        return Frame(phase=phase, parts=parts, joints=joints, residuals=residuals)


_KINDS = {
    "slider_crank": SliderCrankProvider,
    "gear_pair": GearPairProvider,
}


def make_provider(spec):
    """Build a scene provider from the ``source`` dictionary of an example.

    ``spec`` must be a mapping with a ``kind`` of ``slider_crank`` or
    ``gear_pair`` and an optional ``parameters`` mapping. Invalid or
    nonfinite parameters raise ``ValueError``; impossible geometry is
    never silently clamped.
    """
    if not isinstance(spec, dict):
        raise ValueError(f"source spec must be a mapping, got {spec!r}")
    kind = spec.get("kind")
    if kind not in _KINDS:
        raise ValueError(f"unknown source kind {kind!r}; expected one of {sorted(_KINDS)}")
    parameters = spec.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ValueError(f"source parameters must be a mapping, got {parameters!r}")
    try:
        return _KINDS[kind](**parameters)
    except TypeError as exc:
        raise ValueError(f"invalid parameters for {kind}: {exc}") from exc
