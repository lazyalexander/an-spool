"""Small shared contracts. Source providers do not depend on drawing or export modules."""
from dataclasses import dataclass, field
from typing import Mapping, Protocol

import numpy as np


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    faces: np.ndarray

    def __post_init__(self):
        # Frozen dataclasses alone do not protect the underlying array storage.
        for name in ("vertices", "faces"):
            value = np.array(getattr(self, name), copy=True)
            value.setflags(write=False)
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class Part:
    id: str
    label: str
    material: str
    mesh: Mesh
    transform: np.ndarray = field(default_factory=lambda: np.eye(4))

    def __post_init__(self):
        transform = np.array(self.transform, copy=True)
        transform.setflags(write=False)
        object.__setattr__(self, "transform", transform)

    def world_vertices(self) -> np.ndarray:
        return self.mesh.vertices @ self.transform[:3, :3].T + self.transform[:3, 3]


@dataclass(frozen=True)
class Frame:
    phase: float
    parts: tuple[Part, ...]
    joints: Mapping[str, np.ndarray] = field(default_factory=dict)
    residuals: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Camera:
    eye: tuple[float, float, float]
    target: tuple[float, float, float]
    ortho_width: float


@dataclass(frozen=True)
class RenderSettings:
    width: int
    height: int
    camera: Camera
    light: tuple[float, float, float]
    ground_part_id: str | None = None
    ground_z: float | None = None


class SceneProvider(Protocol):
    def frame(self, phase: float) -> Frame:
        """Return the same named rigid parts for a normalized cycle phase in [0, 1]."""
        ...
