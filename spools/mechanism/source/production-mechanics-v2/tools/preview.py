#!/usr/bin/env python3
"""Neutral low-cost preview: flat-shaded painter's-algorithm stills + GIF.

Not a beauty render — single directional light, flat engineering colors,
no textures. Run from the package root:

    PYTHONPATH=src:/private/tmp/steam-ink-deps python3 tools/preview.py

Writes delivery/preview/preview-*.png (8 stills over the cycle) and
delivery/preview/preview.gif (24 frames, 125 ms each, one 3 s cycle).
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mechflow.steam_engine import SteamEngineProvider           # noqa: E402

# Neutral engineering palette by material category.
PALETTE = {
    "base": (52, 60, 63),
    "frame": (96, 108, 112),
    "steel": (168, 174, 174),
    "accent": (150, 96, 52),
    "brass": (176, 148, 92),
}


def render(frame, spec, width, height):
    cam = spec["render"]["camera"]
    eye = np.array(cam["eye"], dtype=float)
    target = np.array(cam["target"], dtype=float)
    forward = target - eye
    forward /= np.linalg.norm(forward)
    right = np.cross(forward, [0.0, 0.0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    light = np.array(spec["render"]["light"], dtype=float)
    light /= np.linalg.norm(light)
    scale = width / cam["ortho_width"]

    img = Image.new("RGB", (width, height), (24, 27, 29))
    draw = ImageDraw.Draw(img)

    tris = []          # (depth, polygon, color)
    for part in frame.parts:
        V = part.world_vertices()
        rel = V - eye
        sx = rel @ right
        sy = rel @ up
        depth = rel @ forward
        F = np.asarray(part.mesh.faces)
        base_color = PALETTE[part.material]
        for f in F:
            tri = V[f]
            n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
            norm = np.linalg.norm(n)
            if norm < 1e-12:
                continue
            n /= norm
            shade = 0.35 + 0.65 * abs(float(n @ light))
            color = tuple(min(255, int(c * shade)) for c in base_color)
            idx = list(f)
            tris.append((float(depth[idx].mean()),
                         [(float(sx[i] * scale + width / 2),
                           float(height / 2 - sy[i] * scale)) for i in idx],
                         color))
    tris.sort(key=lambda t: t[0])        # far first
    for _, poly, color in tris:
        draw.polygon(poly, fill=color)
    return img


def main():
    spec = json.loads((ROOT / "examples/steam-engine.json").read_text())
    provider = SteamEngineProvider(**spec["source"]["parameters"])
    out = ROOT / "delivery/preview"
    out.mkdir(parents=True, exist_ok=True)

    width, height = spec["render"]["width"], spec["render"]["height"]
    stills = [i / 8 for i in range(8)]
    for i, phase in enumerate(stills):
        img = render(provider.frame(phase), spec, width, height)
        img.save(out / f"preview-{i}.png")
    gif_frames = []
    for i in range(24):
        img = render(provider.frame(i / 24), spec, 480, 360)
        gif_frames.append(img)
    gif_frames[0].save(out / "preview.gif", save_all=True,
                       append_images=gif_frames[1:], duration=125, loop=0)
    for img in gif_frames:
        img.close()
    print(f"wrote {len(stills)} stills and preview.gif to {out}")


if __name__ == "__main__":
    main()
