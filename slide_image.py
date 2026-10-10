"""Tweak the Tumor's microscope view: a real breast FNAC image whose nuclei follow the sliders.

The picture is a real benign cytology patch (see data/slide/ and scripts/prepare_slide.py).
Each real nucleus is resampled into a new outline, so its own stained texture is kept:
    nucleus size     -> every nucleus grows or shrinks
    texture          -> stronger or fainter speckle (grey-level variation) inside the nuclei
    smoothness       -> bumpier or smoother nucleus edges
    concavity        -> deeper dents in the edges
    concave points   -> more dents per nucleus
At the typical benign values the image is the original. No Streamlit here, so it can be tested alone.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

SLIDE = Path(__file__).resolve().parent / "data" / "slide"
# WDBC feature name -> the slider it belongs to.
SIZE, TEXTURE, SMOOTHNESS = "mean radius", "mean texture", "mean smoothness"
CONCAVITY, CONCAVE_POINTS = "mean concavity", "worst concave points"
FEATURES = (SIZE, TEXTURE, SMOOTHNESS, CONCAVITY, CONCAVE_POINTS)
MAX_DENTS = 6


@dataclass(frozen=True)
class Look:
    scale: float = 1.0      # nucleus size, 1 = as photographed
    contrast: float = 1.0   # chromatin speckle inside the nucleus
    grain: float = 0.0      # extra coarse speckle
    smooth: float = 0.0     # 0..1: round off the real outline
    bumps: float = 0.0      # 0..0.11: wavy edge, as a fraction of the radius
    dent_depth: float = 0.0
    dents: int = 0


def offset(value: float, spec: dict, typical: float) -> float:
    """-1 at the feature's minimum, 0 at the typical benign value, +1 at its maximum."""
    if value >= typical:
        return (value - typical) / max(spec["max"] - typical, 1e-9)
    return (value - typical) / max(typical - spec["min"], 1e-9)


def look_for(values: dict[str, float], specs: dict[str, dict], benign: dict[str, float]) -> Look:
    t = {name: offset(values[name], specs[name], benign[name]) for name in FEATURES}
    points = max(t[CONCAVE_POINTS], 0.0)
    depth = 0.42 * max(t[CONCAVITY], 0.0) ** 0.7 + 0.15 * points
    return Look(scale=(values[SIZE] / benign[SIZE]) ** 0.85,
                contrast=1 + (1.6 if t[TEXTURE] >= 0 else 0.6) * t[TEXTURE],
                grain=0.12 * max(t[TEXTURE], 0.0),
                smooth=max(-t[SMOOTHNESS], 0.0),
                bumps=0.11 * max(t[SMOOTHNESS], 0.0),
                dent_depth=min(depth, 0.45),
                dents=round(1 + (MAX_DENTS - 1) * points) if depth > 0.01 else 0)


@lru_cache(maxsize=1)
def assets() -> tuple[np.ndarray, np.ndarray, list[dict], np.ndarray]:
    base = np.asarray(Image.open(SLIDE / "base.jpg").convert("RGB")).astype(np.float32) / 255
    background = np.asarray(Image.open(SLIDE / "background.jpg").convert("RGB")).astype(np.float32) / 255
    meta = json.loads((SLIDE / "nuclei.json").read_text(encoding="utf-8"))
    rng = np.random.default_rng(7)
    for nucleus in meta["nuclei"]:  # fixed per-nucleus randomness, so the picture never flickers
        nucleus["phases"] = rng.uniform(0, 2 * math.pi, 5)
        start = rng.uniform(0, 2 * math.pi)
        nucleus["dent_angles"] = (start + np.arange(MAX_DENTS) * 2 * math.pi / MAX_DENTS
                                  + rng.uniform(-0.35, 0.35, MAX_DENTS))[rng.permutation(MAX_DENTS)]
    grain = ndi.gaussian_filter(rng.standard_normal(base.shape[:2]), 1.4)
    grain = (grain / grain.std()).astype(np.float32)
    return base, background, meta["nuclei"], grain


def outline(nucleus: dict, look: Look) -> np.ndarray:
    """The nucleus's new radius at each of its sampled angles."""
    radii = np.asarray(nucleus["radii"], dtype=np.float32)
    angles = np.linspace(0, 2 * math.pi, radii.size, endpoint=False)
    shape = radii.mean() + (radii - radii.mean()) * (1 - 0.85 * look.smooth)
    wave = sum(np.sin(k * angles + phase) for k, phase in zip(range(5, 10), nucleus["phases"])) / 2.2
    shape = shape * (1 + look.bumps * wave)
    for angle in nucleus["dent_angles"][:look.dents]:
        gap = np.angle(np.exp(1j * (angles - angle)))
        shape = shape * (1 - look.dent_depth * np.exp(-(gap / 0.3) ** 2))
    return np.maximum(shape * look.scale, 1.0)


def render(look: Look) -> Image.Image:
    base, background, nuclei, grain = assets()
    out = background.copy()
    height, width = out.shape[:2]
    for nucleus in nuclei:
        source = np.asarray(nucleus["radii"], dtype=np.float32)
        target = outline(nucleus, look)
        cx, cy, reach = nucleus["cx"], nucleus["cy"], float(target.max()) + 2
        x0, x1 = max(int(cx - reach), 0), min(int(cx + reach) + 1, width)
        y0, y1 = max(int(cy - reach), 0), min(int(cy + reach) + 1, height)
        if x0 >= x1 or y0 >= y1:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        dx, dy = xs - cx, ys - cy
        distance = np.hypot(dx, dy)
        position = (np.arctan2(dy, dx) % (2 * math.pi)) / (2 * math.pi) * source.size
        r_target = np.interp(position, np.arange(source.size + 1), np.append(target, target[0]))
        r_source = np.interp(position, np.arange(source.size + 1), np.append(source, source[0]))
        alpha = np.clip(r_target - distance + 0.5, 0, 1)
        if not alpha.any():
            continue
        # Pull each pixel from the matching point of the real nucleus (kept slightly inside its edge).
        pull = distance * (0.85 * r_source) / r_target
        rows = cy + pull * dy / np.maximum(distance, 1e-6)
        cols = cx + pull * dx / np.maximum(distance, 1e-6)
        colour = np.stack([ndi.map_coordinates(base[..., c], [rows, cols], order=1, mode="nearest")
                           for c in range(3)], axis=-1)
        inside = alpha > 0.5
        # Texture: stretch only the brightness differences, so the stain colour stays the same.
        brightness = colour.mean(axis=-1, keepdims=True)
        typical = brightness[inside].mean() if inside.any() else brightness.mean()
        colour = colour + (brightness - typical) * (look.contrast - 1)
        colour = colour * (1 + look.grain * grain[y0:y1, x0:x1, None])
        patch = out[y0:y1, x0:x1]
        out[y0:y1, x0:x1] = patch * (1 - alpha[..., None]) + np.clip(colour, 0, 1) * alpha[..., None]
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def render_jpeg(look: Look, quality: int = 86) -> bytes:
    buffer = BytesIO()
    render(look).save(buffer, "JPEG", quality=quality)
    return buffer.getvalue()
