"""Prepare the real microscope image used by Tweak the Tumor (run once; outputs are committed).

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\prepare_slide.py [--debug OUT.png]

Source: a real benign (Yokohama C2) breast FNAC patch, Pap stain, from
Patil A, Jain G, Sethi A. A Multi-Center Breast FNAC Cytology Dataset for AI-Assisted
Patch-wise Classification Using C1-C5 Reporting Categories. Zenodo, 2026.
doi:10.5281/zenodo.20762698 (CC BY 4.0). Patch: 06B2344251P/II/06B2344251P_91253_16817.png

Writes data/slide/:
    base.jpg        the real image, unchanged apart from JPEG compression
    background.jpg  the same image with the nuclei painted out (shown where a nucleus shrinks)
    nuclei.json     each nucleus: centre and its outline as a radius at 64 angles
    reference_malignant.jpg  an unedited real malignant (C5) patch from the same dataset, for comparison
slide_image.py reshapes the real nuclei from these files as the sliders move.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "slide_source"
BASE = SOURCE / "06B2344251P_91253_16817.png"
MALIGNANT = SOURCE / "03B0097251P_139936_52359.png"
OUT = ROOT / "data" / "slide"
ANGLES = 64
DARK = 0.36           # luminance below this = nucleus
MIN_AREA, MAX_AREA = 350, 4500
SEED_SPACING = 17     # px between nucleus centres when splitting touching nuclei


def rgb(path: Path) -> np.ndarray:
    image = Image.open(path)
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image, mask=image.split()[-1])
        image = flat
    return np.asarray(image.convert("RGB")).astype(float) / 255


def segment(image: np.ndarray) -> np.ndarray:
    """Label map of nuclei. Touching nuclei are split around distance peaks (a simple watershed)."""
    lum = image @ np.array([0.299, 0.587, 0.114])
    mask = ndi.binary_fill_holes(ndi.binary_opening(lum < DARK, iterations=2))
    distance = ndi.gaussian_filter(ndi.distance_transform_edt(mask), 1.5)
    peaks = (distance == ndi.maximum_filter(distance, size=SEED_SPACING)) & (distance > 5)
    seeds, _ = ndi.label(ndi.binary_dilation(peaks, iterations=1))
    # Every mask pixel joins its nearest seed.
    _, (rows, cols) = ndi.distance_transform_edt(seeds == 0, return_indices=True)
    labels = np.where(mask, seeds[rows, cols], 0)
    keep = np.zeros_like(labels)
    count = 0
    for index in range(1, labels.max() + 1):
        parts, found = ndi.label(ndi.binary_opening(labels == index, iterations=1))
        if not found:
            continue
        sizes = ndi.sum(parts > 0, parts, range(1, found + 1))
        region = parts == 1 + int(np.argmax(sizes))  # drop stray specks
        area = int(region.sum())
        if MIN_AREA <= area <= MAX_AREA:
            count += 1
            keep[region] = count
    return keep


def profile(region: np.ndarray, centre: tuple[float, float]) -> list[float]:
    """Distance from the centre to the region's edge at ANGLES evenly spaced angles."""
    cy, cx = centre
    radii = []
    steps = np.arange(0, 120, 0.5)
    for angle in np.linspace(0, 2 * np.pi, ANGLES, endpoint=False):
        ys = np.round(cy + steps * np.sin(angle)).astype(int)
        xs = np.round(cx + steps * np.cos(angle)).astype(int)
        inside = (ys >= 0) & (ys < region.shape[0]) & (xs >= 0) & (xs < region.shape[1])
        hits = np.zeros_like(steps, dtype=bool)
        hits[inside] = region[ys[inside], xs[inside]]
        outside = np.flatnonzero(~hits)
        radii.append(float(steps[outside[0]] if outside.size else steps[-1]))
    return radii


def paint_out(image: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Fill the masked pixels from the surrounding background (multi-scale normalized blur)."""
    known = ~mask
    filled = image.copy()
    for sigma in (2, 4, 8, 16, 32):
        weight = ndi.gaussian_filter(known.astype(float), sigma)
        blurred = np.stack([ndi.gaussian_filter(image[..., c] * known, sigma) for c in range(3)], -1)
        estimate = blurred / np.maximum(weight, 1e-6)[..., None]
        fill = mask & (weight > 0.02)
        filled[fill] = estimate[fill]
        known = known | fill
        image = filled
        mask = mask & ~fill
    return filled


def save_jpeg(array: np.ndarray, path: Path) -> None:
    Image.fromarray(np.clip(array * 255, 0, 255).astype(np.uint8)).save(path, "JPEG", quality=90)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    image = rgb(BASE)
    labels = segment(image)
    nuclei = []
    for index in range(1, labels.max() + 1):
        region = labels == index
        cy, cx = ndi.center_of_mass(region)
        nuclei.append({"cx": round(float(cx), 2), "cy": round(float(cy), 2),
                       "radii": [round(r, 2) for r in profile(region, (cy, cx))]})
    nuclear = ndi.binary_dilation(labels > 0, iterations=3)
    background = paint_out(image, nuclear)
    save_jpeg(image, OUT / "base.jpg")
    save_jpeg(background, OUT / "background.jpg")
    save_jpeg(rgb(MALIGNANT), OUT / "reference_malignant.jpg")
    meta = {"source": BASE.name, "width": image.shape[1], "height": image.shape[0],
            "angles": ANGLES, "nuclei": nuclei}
    (OUT / "nuclei.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    print(f"{len(nuclei)} nuclei; wrote {sorted(p.name for p in OUT.iterdir())}")
    if "--debug" in sys.argv:
        debug = (image * 255).astype(np.uint8)
        edge = (labels > 0) & ~ndi.binary_erosion(labels > 0)
        boundaries = ndi.grey_dilation(labels, size=3) != ndi.grey_erosion(labels, size=3)
        debug[edge | (boundaries & (labels > 0))] = [255, 255, 0]
        Image.fromarray(debug).save(sys.argv[sys.argv.index("--debug") + 1])


if __name__ == "__main__":
    main()
