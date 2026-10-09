"""Generate unmistakably synthetic grey PNGs and all 30 schema-compliant cases.

Uses only the Python standard library. Never touches real images or datasets.
"""
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = ("normal", "benign", "malignant")
DIGITS = {
    "0": ("111", "101", "101", "101", "111"), "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"), "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"), "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"), "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"), "9": ("111", "101", "111", "001", "111"),
}


def png(destination: Path, case_id: str, view: str, truth: str) -> None:
    width, height = (600, 848) if view == "print" else (480, 360)
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # PNG scanline filter: none
        for x in range(width):
            grey = 222 if (x // 32 + y // 32) % 2 else 231
            if 24 <= x < width - 24 and 24 <= y < height - 24:
                grey -= 13
            radius = math.hypot((x - width * 0.52) / 1.2, y - height * 0.5)
            if view in ("heatmaps", "overlays") and radius < 68:
                grey = 178 if radius < 40 else 193
            if view == "overlays" and truth != "normal" and 48 < radius < 52:
                grey = 92
            # Case number only; no truth or AI prediction is burned into any image.
            for position, digit in enumerate(case_id):
                dx, dy = x - (32 + position * 48), y - 32
                if 0 <= dx < 30 and 0 <= dy < 50 and DIGITS[digit][dy // 10][dx // 10] == "1":
                    grey = 90
            rows.extend((grey, grey, grey))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)

    content = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(bytes(rows))) + chunk(b"IEND", b""))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)


def generate(force: bool = False) -> Path:
    destination = ROOT / "data" / "booth_set_demo.json"
    if destination.exists() and not force:
        raise SystemExit("Dataset already exists. Use --force only to replace it with FAKE demo data.")
    cases = []
    for number in range(1, 31):
        cid = f"{number:02d}"
        truth = LABELS[(number - 1) % 3]
        prediction = LABELS[number % 3] if number % 4 == 0 else truth
        confidence = (0.64, 0.73, 0.82)[number % 3]
        probabilities = {label: round(confidence if label == prediction else (1 - confidence) / 2, 3)
                         for label in LABELS}
        correct = prediction == truth
        error = (None if correct else "false_negative" if truth == "malignant"
                 else "false_positive" if prediction == "malignant" else "other_confusion")
        paths = {}
        for field, folder in (("image", "images"), ("print_image", "print"),
                              ("heatmap", "heatmaps"), ("mask_overlay", "overlays")):
            filename = f"case{cid}_A5.png" if folder == "print" else f"case{cid}.png"
            relative = Path("data") / "demo" / folder / filename
            png(ROOT / relative, cid, folder, truth)
            paths[field] = relative.relative_to("data").as_posix()
        cases.append({"case_id": cid, "source_file": f"FAKE_case{cid}.png", **paths,
                      "truth": truth, "ai_pred": prediction, "ai_probs": probabilities,
                      "correct": correct, "error_type": error,
                      "cam_mask_overlap": 0.0 if truth == "normal" else 0.25})
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Replace the existing dataset with fake data")
    print(generate(parser.parse_args().force))
