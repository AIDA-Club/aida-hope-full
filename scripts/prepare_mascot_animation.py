r"""Turn the animated mascot video into a transparent, web-playable animation for the Home hero.

The source is an MPEG-4 Part 2 (mp4v) clip on a flat near-white background. Browsers cannot
play that codec, and an MP4 has no transparency, so this script:
  1. decodes the frames with ffmpeg (pass its path with --ffmpeg, e.g. from `imageio-ffmpeg`),
  2. removes the background: the background is flat (noise <= 2 colour units) while the white
     fur is at least ~6 units away, so after a light blur (to ignore compression blocks) pixels
     within 3 units of the background colour that connect to the frame border, plus large
     enclosed pockets of background, become transparent; the outline gets a ~1 px soft edge and
     the white background mixed into edge pixels is removed; the source's white sticker
     outline (up to HALO_WIDTH px of near-white next to the background) is removed too,
  3. crops all frames to their shared content box and saves:
       frontend/public/art/mascot-home.webp       (animated WebP with alpha, loops)
       frontend/public/art/mascot-home-still.webp (first frame, for reduced motion)

    python scripts\prepare_mascot_animation.py --ffmpeg PATH\to\ffmpeg.exe --video PATH\to\clip.mp4
        [--width 640] [--fps 20] [--quality 75]

Defaults keep the file small enough for a homepage (the page shows the still first and swaps
in the animation once it has downloaded).
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "frontend" / "public" / "art"
THRESHOLD = 3.0      # blurred colour distance from the background that still counts as background
POCKET_DISTANCE, POCKET_AREA = 1.5, 1500  # enclosed pure-background holes (e.g. under the arm)
EDGE_SOFTNESS = 1.3  # px (source resolution) of anti-aliasing on the outline
EDGE_INSET = 1       # px the outline is pulled in, to drop compression ringing
HALO_WIDTH, HALO_MIN = 8, 232  # the source has a baked-in white sticker outline: up to this many px of
                               # near-white (every channel >= HALO_MIN) next to the background is removed


def frames(ffmpeg: str, video: Path, folder: Path, fps: int) -> list[Path]:
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(video), "-vf", f"fps={fps}",
                    str(folder / "f_%04d.png")], check=True)
    return sorted(folder.glob("f_*.png"))


def background_colour(rgb: np.ndarray) -> np.ndarray:
    edge = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    return np.median(edge, axis=0)


def alpha_for(rgb: np.ndarray, bg: np.ndarray) -> np.ndarray:
    distance = ndi.gaussian_filter(np.sqrt(((rgb.astype(np.float32) - bg) ** 2).sum(axis=2)), 1.5)
    labels, _ = ndi.label(distance < THRESHOLD)
    border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    background = np.isin(labels, border[border > 0])
    near_white = rgb.min(axis=2) >= HALO_MIN
    for _ in range(HALO_WIDTH):  # grow into the white outline, one pixel at a time
        background |= ndi.binary_dilation(background) & near_white
    pockets, n = ndi.label(distance < POCKET_DISTANCE)
    holes = np.zeros_like(background)
    if n:
        sizes = ndi.sum(np.ones_like(distance), pockets, index=np.arange(1, n + 1))
        holes = np.isin(pockets, np.arange(1, n + 1)[sizes >= POCKET_AREA])
    # The figure: everything not connected to the border, with tiny noise holes filled and
    # specks removed, minus large enclosed pockets of background.
    figure = ndi.binary_fill_holes(ndi.binary_opening(~background, iterations=2)) & ~holes
    figure = ndi.binary_erosion(figure, iterations=EDGE_INSET)
    alpha = ndi.gaussian_filter(figure.astype(np.float32), EDGE_SOFTNESS)
    return (np.clip(alpha, 0, 1) * 255).round().astype(np.uint8)


def unmatte(rgb: np.ndarray, alpha: np.ndarray, bg: np.ndarray) -> np.ndarray:
    """Remove the white background that is mixed into semi-transparent edge pixels."""
    a = alpha.astype(np.float32)[..., None] / 255
    out = (rgb.astype(np.float32) - bg * (1 - a)) / np.maximum(a, 1e-3)
    return np.where(a > 0.02, np.clip(out, 0, 255), rgb).astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--quality", type=int, default=75)
    parser.add_argument("--width", type=int, default=640, help="px; the hero shows it at up to ~470 css px")
    parser.add_argument("--fps", type=int, default=20)
    parser.add_argument("--still-only", action="store_true", help="only the first frame, for a quick check")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as folder:
        paths = frames(args.ffmpeg, args.video, Path(folder), args.fps)
        if args.still_only:
            paths = paths[:1]
        first = np.asarray(Image.open(paths[0]).convert("RGB"))
        bg = background_colour(first)
        rgba = []
        for path in paths:
            rgb = np.asarray(Image.open(path).convert("RGB"))
            alpha = alpha_for(rgb, bg)
            rgba.append(np.dstack([unmatte(rgb, alpha, bg), alpha]))
    union = np.any(np.stack([frame[..., 3] > 8 for frame in rgba]), axis=0)
    rows, cols = np.where(union)
    box = (cols.min(), rows.min(), cols.max() + 1, rows.max() + 1)
    images = []
    for frame in rgba:
        image = Image.fromarray(frame, "RGBA").crop(box)
        images.append(image.resize((args.width, round(image.height * args.width / image.width)), Image.LANCZOS))
    ART.mkdir(parents=True, exist_ok=True)
    images[0].save(ART / "mascot-home-still.webp", "WEBP", quality=90, method=6)
    if not args.still_only:
        images[0].save(ART / "mascot-home.webp", "WEBP", save_all=True, append_images=images[1:],
                       duration=round(1000 / args.fps), loop=0, quality=args.quality, alpha_quality=90, method=4)
    print(f"{len(images)} frames, background {bg.round().tolist()}, crop {box}, size {images[0].size}")
    for name in ("mascot-home.webp", "mascot-home-still.webp"):
        print(name, f"{(ART / name).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
