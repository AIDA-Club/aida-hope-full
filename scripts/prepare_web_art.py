r"""Copy the supplied transparent artwork (design/assets) into frontend/public/art as trimmed WebP.

The supplied cutouts carry faint alpha noise (alpha 1-8) far outside each shape, which inflates
their bounds and can show as a haze on coloured panels. That noise is cleared, each image is
cropped to its visible shape, downscaled for the web and saved as WebP with lossless alpha.
Run: .venv\Scripts\python.exe scripts/prepare_web_art.py
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE, TARGET = ROOT / "design" / "assets", ROOT / "frontend" / "public" / "art"
NOISE = 8  # alpha at or below this is treated as fully transparent


def width_for(name: str) -> int:
    if name.startswith("mascot"):
        return 900
    if name.startswith("avatar"):
        return 420
    if name.startswith("ribbon"):
        return 1100
    if name.startswith("illustration"):
        return 560
    if name in ("decoration-pink-petal.png", "decoration-pink-oval.png", "decoration-lilac-blob.png"):
        return 700
    if name.startswith("decoration"):
        return 320
    return 0  # icons: redrawn as SVG in frontend/src/components/Icon.tsx


def main() -> None:
    files = {}
    for folder in sorted(SOURCE.iterdir()):
        for path in sorted(folder.glob("*.png")):
            files.setdefault(path.name, path)  # later batches repeat shared files unchanged
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, path in files.items():
        width = width_for(name)
        if not width:
            continue
        image = Image.open(path).convert("RGBA")
        alpha = image.getchannel("A").point(lambda v: 0 if v <= NOISE else v)
        image.putalpha(alpha)
        image = image.crop(alpha.getbbox())
        if image.width > width:
            image = image.resize((width, round(image.height * width / image.width)), Image.LANCZOS)
        image.save(TARGET / f"{path.stem}.webp", "WEBP", quality=90, method=6, exact=False)
        print(f"{name}: {image.size}")


if __name__ == "__main__":
    main()
