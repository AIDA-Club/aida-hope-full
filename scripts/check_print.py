"""Check the built print PDFs: decode every QR code and look for draft marks.

Run from the project folder (Windows), after scripts\\build_print.py:
    .venv\\Scripts\\python.exe scripts\\check_print.py

Each page is rendered at 200 dpi and every QR code on it is decoded with OpenCV
(opencv-python-headless). Prints one line per PDF and exits non-zero if any QR code is
missing or decodes to anything other than takehome.qr_url in print_content.yaml.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pypdfium2 as pdfium
import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "print_out"
# PDF -> QR codes expected on each page.
EXPECTED = {"case_cards.pdf": 1, "takehome_cards.pdf": 10, "poster_A2.pdf": 1}
DRAFT_TEXT = ("needs native review", "Arabic DRAFT")


def decode_image(image: np.ndarray) -> list[str]:
    detector = cv2.QRCodeDetector()
    found, texts, _, _ = detector.detectAndDecodeMulti(image)
    texts = [text for text in texts if text] if found else []
    if not texts:
        single, _, _ = detector.detectAndDecode(image)
        texts = [single] if single else []
    return texts


def decode_page(page, per_page: int) -> list[str]:
    """Decode a page; a page with several cards is cut into one tile per card first.

    Each tile (or page) is tried at a few resolutions, so a miss by the detector on one
    rendering is not reported as a missing code.
    """
    columns, rows = (2, 5) if per_page == 10 else (1, 1)
    best: list[str] = []
    for dpi in (200, 300, 150):
        image = np.asarray(page.render(scale=dpi / 72).to_pil().convert("L"))
        height, width = image.shape
        texts = []
        for row in range(rows):
            for column in range(columns):
                tile = image[row * height // rows:(row + 1) * height // rows,
                             column * width // columns:(column + 1) * width // columns]
                texts += decode_image(tile)[:1] if per_page > 1 else decode_image(tile)
        if len(texts) > len(best):
            best = texts
        if len(best) >= per_page:
            break
    return best


def decode_pdf(path: Path, per_page: int) -> list[list[str]]:
    document = pdfium.PdfDocument(str(path))
    try:
        return [decode_page(document[index], per_page) for index in range(len(document))]
    finally:
        document.close()


def page_texts(path: Path) -> list[str]:
    document = pdfium.PdfDocument(str(path))
    try:
        return [document[index].get_textpage().get_text_range() for index in range(len(document))]
    finally:
        document.close()


def draft_marks(folder: Path = OUT) -> dict[str, int]:
    """Number of pages per PDF that carry an Arabic draft mark."""
    return {pdf.name: sum(any(mark in text for mark in DRAFT_TEXT) for text in page_texts(pdf))
            for pdf in sorted(folder.glob("*.pdf"))}


def check(folder: Path = OUT) -> tuple[bool, list[str]]:
    url = yaml.safe_load((ROOT / "print_content.yaml").read_text(encoding="utf-8"))["takehome"]["qr_url"]
    ok, lines = True, []
    for name, per_page in EXPECTED.items():
        pages = decode_pdf(folder / name, per_page)
        decoded = [text for page in pages for text in page]
        wrong = sorted({text for text in decoded if text != url})
        short = [index + 1 for index, page in enumerate(pages) if len(page) < per_page]
        good = not wrong and not short
        ok &= good
        lines.append(f"{name}: {len(decoded)} QR codes on {len(pages)} pages, "
                     f"{sum(text == url for text in decoded)} decode to {url}"
                     + ("" if good else f"  PROBLEM wrong={wrong} pages missing codes={short}"))
    return ok, lines


def main() -> int:
    ok, lines = check()
    print("\n".join(lines))
    print("Pages with an Arabic draft mark:", draft_marks())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
