"""Build every printed booth material from print_content.yaml.

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\build_print.py

Outputs go to print_out/:
    case_cards.pdf       30 A5 challenge cards (no answers on them)
    answer_key.pdf       A4 staff-only answer table
    folders.pdf          6 fictional patient folders, 6 A4 pages each
    tips_card.pdf        A5 "how to read an ultrasound" card, English front, Arabic back
    takehome_cards.pdf   85 x 55 mm cards, 10 per A4 sheet with crop marks
    poster_A2.pdf        A2 portrait poster
    previews/*.png       page 1 of each PDF + every page of folder 1

All wording lives in print_content.yaml; this script only does layout.
Every raster image is resampled to exactly 300 dpi at its printed size.
"""
from __future__ import annotations

import csv
import json
import sys
from io import BytesIO
from pathlib import Path

import arabic_reshaper
import qrcode
import yaml
from bidi.algorithm import get_display
from PIL import Image
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A2, A4, A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
GRADCAM = DATA / "reports" / "gradcam_all"
OUT = ROOT / "print_out"
PREVIEWS = OUT / "previews"
FONTS = ROOT / "assets" / "fonts"
DPI = 300

# One accent colour on a white / grey base, for a clean medical look.
PINK = HexColor("#D6336C")
PINK_LIGHT = HexColor("#FCE8EF")
INK = HexColor("#243746")
GREY = HexColor("#6B7785")
GREY_LIGHT = HexColor("#F1F3F5")
RULE = HexColor("#D5DADF")

# Font names used below. register_fonts() maps them to real files.
SANS, SANS_BOLD, SANS_BLACK = "Lato", "Lato-Bold", "Lato-Black"
AR, AR_BOLD = "Amiri", "Amiri-Bold"
AR_SCALE = 1.15  # Amiri looks smaller than Lato at the same point size.


# ---------------------------------------------------------------------------
# Fonts and text helpers
# ---------------------------------------------------------------------------
def register_fonts() -> list[str]:
    """Register the bundled fonts; fall back to Windows fonts if one is missing."""
    notes = []
    wanted = {SANS: ["Lato-Regular.ttf", "C:/Windows/Fonts/segoeui.ttf"],
              SANS_BOLD: ["Lato-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf"],
              SANS_BLACK: ["Lato-Black.ttf", "C:/Windows/Fonts/segoeuib.ttf"],
              AR: ["Amiri-Regular.ttf", "C:/Windows/Fonts/arial.ttf"],
              AR_BOLD: ["Amiri-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]}
    for name, candidates in wanted.items():
        for index, candidate in enumerate(candidates):
            path = Path(candidate) if Path(candidate).is_absolute() else FONTS / candidate
            if path.is_file():
                pdfmetrics.registerFont(TTFont(name, str(path)))
                if index:
                    notes.append(f"{name}: bundled font missing, used {path.name}")
                break
        else:
            sys.exit(f"No font found for {name}; put the TTF files in assets/fonts/.")
    return notes


def shape_ar(text: str) -> str:
    """Join Arabic letters and put them in right-to-left visual order for PDF drawing."""
    return get_display(arabic_reshaper.reshape(text))


def width_of(text: str, font: str, size: float, arabic: bool = False) -> float:
    return pdfmetrics.stringWidth(shape_ar(text) if arabic else text, font, size)


def wrap(text: str, font: str, size: float, max_width: float, arabic: bool = False) -> list[str]:
    """Greedy word wrap. Arabic is wrapped in logical order, then shaped line by line."""
    lines = []
    for paragraph in str(text).split("\n"):
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if not current or width_of(trial, font, size, arabic) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_text(c: Canvas, text: str, x: float, y: float, width: float, font: str, size: float,
              color=INK, align: str | None = None, leading: float | None = None,
              arabic: bool = False) -> float:
    """Draw wrapped text in the box starting at (x, y = first baseline). Returns the next y."""
    leading = leading or size * (1.45 if arabic else 1.25)
    align = align or ("right" if arabic else "left")
    c.setFont(font, size)
    c.setFillColor(color)
    for line in wrap(text, font, size, width, arabic):
        shown = shape_ar(line) if arabic else line
        if align == "right":
            c.drawRightString(x + width, y, shown)
        elif align == "center":
            c.drawCentredString(x + width / 2, y, shown)
        else:
            c.drawString(x, y, shown)
        y -= leading
    return y


def draw_bullets(c: Canvas, items: list[str], x: float, y: float, width: float, font: str,
                 size: float, color=INK, gap: float = 0.0, arabic: bool = False,
                 bullet_color=PINK) -> float:
    """A bulleted list; Arabic bullets sit on the right."""
    indent = size * 1.2
    for item in items:
        c.setFillColor(bullet_color)
        radius = size * 0.17
        dot_y = y + size * 0.32
        c.circle(x + width - radius if arabic else x + radius, dot_y, radius, stroke=0, fill=1)
        text_x = x if arabic else x + indent
        y = draw_text(c, item, text_x, y, width - indent, font, size, color, arabic=arabic) - gap
    return y


def fit_lines(text: str, font: str, max_size: float, width: float, max_lines: int = 2,
              arabic: bool = False) -> tuple[float, list[str]]:
    """Largest font size (down to 8 pt) at which the text fits in max_lines lines."""
    size = max_size
    while size > 8:
        lines = wrap(text, font, size, width, arabic)
        if len(lines) <= max_lines and all(width_of(l, font, size, arabic) <= width for l in lines):
            return size, lines
        size -= 1
    return size, wrap(text, font, size, width, arabic)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
def image_300dpi(path: Path, width_mm: float, height_mm: float | None = None) -> ImageReader:
    """Resample an image to exactly 300 dpi at its printed size (JPEG keeps PDFs small)."""
    image = Image.open(path)
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        background = Image.new("RGB", image.size, "white")
        background.paste(image, mask=image.split()[-1])
        image = background
    image = image.convert("RGB")
    height_mm = height_mm or width_mm * image.height / image.width
    size = (round(width_mm / 25.4 * DPI), round(height_mm / 25.4 * DPI))
    if size != image.size:
        image = image.resize(size, Image.LANCZOS)
    buffer = BytesIO()
    image.save(buffer, "JPEG", quality=92, dpi=(DPI, DPI))
    buffer.seek(0)
    return ImageReader(buffer)


def place_image(c: Canvas, path: Path, x: float, y: float, width_mm: float,
                height_mm: float | None = None, border=RULE) -> float:
    """Draw an image with its bottom-left at (x, y). Returns the drawn height in points."""
    reader = image_300dpi(path, width_mm, height_mm)
    w, h = reader.getSize()
    height = width_mm * mm * h / w
    c.drawImage(reader, x, y, width_mm * mm, height)
    if border is not None:
        c.setStrokeColor(border)
        c.setLineWidth(0.6)
        c.rect(x, y, width_mm * mm, height, stroke=1, fill=0)
    return height


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def load_inputs() -> tuple[dict, list[dict], dict[str, dict]]:
    content = yaml.safe_load((ROOT / "print_content.yaml").read_text(encoding="utf-8"))
    booth = json.loads((DATA / "booth_set.json").read_text(encoding="utf-8"))
    with (DATA / "reports" / "predictions.csv").open(encoding="utf-8", newline="") as handle:
        predictions = {row["file_name"]: row for row in csv.DictReader(handle)}
    # Sanity check: the booth set and the test predictions must agree.
    for case in booth:
        row = predictions.get(case["source_file"])
        if row is None or row["truth"] != case["truth"] or row["pred"] != case["ai_pred"]:
            sys.exit(f"booth_set.json case {case['case_id']} disagrees with predictions.csv")
    for folder in content["folders"]:
        row = predictions.get(folder["case_file"])
        if row is None:
            sys.exit(f"Folder {folder['number']}: {folder['case_file']} is not in predictions.csv")
        if row["truth"].upper() not in folder["real_result"].upper():
            sys.exit(f"Folder {folder['number']}: real_result does not match truth '{row['truth']}'")
    return content, booth, predictions


def overlap_label(case: dict) -> str:
    """Same thresholds as the app: >=0.3 yes, 0.1-0.3 partly, <0.1 no, blank for normal."""
    overlap = case.get("cam_mask_overlap")
    if case["truth"] == "normal" or overlap is None:
        return ""
    return "Yes" if overlap >= 0.3 else "Partly" if overlap >= 0.1 else "No"


def footer(c: Canvas, page_width: float, text: str, y: float = 9 * mm, size: float = 8) -> None:
    c.setFont(SANS, size)
    c.setFillColor(GREY)
    c.drawCentredString(page_width / 2, y, text)


# ---------------------------------------------------------------------------
# 1. Case cards (A5, one per booth case, NO answers)
# ---------------------------------------------------------------------------
def build_case_cards(content: dict, booth: list[dict]) -> Path:
    path = OUT / "case_cards.pdf"
    width, height = A5
    margin = 8 * mm  # more than the required 5 mm safe margin
    c = Canvas(str(path), pagesize=A5)
    c.setTitle("AIDA × Hope case cards")
    for case in sorted(booth, key=lambda item: item["case_id"]):
        # Corner label "CASE 01" (only the number: never the file name, it contains the class).
        label = f"{content['case_cards']['label']} {case['case_id']}"
        c.setFillColor(PINK)
        c.roundRect(margin, height - margin - 16 * mm, 46 * mm, 16 * mm, 3 * mm, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont(SANS_BLACK, 24)
        c.drawCentredString(margin + 23 * mm, height - margin - 11 * mm, label)
        # Large image, full width inside the margins.
        image_mm = (width - 2 * margin) / mm
        top = height - margin - 22 * mm
        place_image(c, DATA / case["print_image"], margin, top - image_mm * mm, image_mm)
        draw_text(c, content["case_cards"]["prompt"], margin, top - image_mm * mm - 9 * mm,
                  width - 2 * margin, SANS_BOLD, 12, INK, align="center")
        footer(c, width, content["meta"]["footer"], y=margin + 1 * mm)
        c.showPage()
    c.save()
    return path


# ---------------------------------------------------------------------------
# 2. Answer key (A4, staff only)
# ---------------------------------------------------------------------------
def build_answer_key(content: dict, booth: list[dict]) -> Path:
    path = OUT / "answer_key.pdf"
    width, height = A4
    margin = 15 * mm
    text = content["answer_key"]
    c = Canvas(str(path), pagesize=A4)
    c.setTitle("AIDA × Hope answer key (staff only)")
    # Header banner
    c.setFillColor(PINK)
    c.rect(0, height - 24 * mm, width, 24 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont(SANS_BLACK, 26)
    c.drawString(margin, height - 16 * mm, text["header"])
    c.setFont(SANS_BOLD, 12)
    c.drawRightString(width - margin, height - 15 * mm, text["title"])
    y = draw_text(c, text["note"], margin, height - 32 * mm, width - 2 * margin, SANS, 8.5, GREY)

    rows = [text["columns"]]
    wrong_rows = []
    for index, case in enumerate(sorted(booth, key=lambda item: item["case_id"]), start=1):
        confidence = case["ai_probs"][case["ai_pred"]]
        shown = ">99%" if confidence >= 0.995 else f"{confidence * 100:.0f}%"
        correct = "Yes" if case["correct"] else {
            "false_negative": "No: missed cancer", "false_positive": "No: false alarm",
            "other_confusion": "No"}.get(case["error_type"], "No")
        rows.append([case["case_id"], case["truth"].capitalize(), case["ai_pred"].capitalize(),
                     shown, correct, overlap_label(case)])
        if not case["correct"]:
            wrong_rows.append(index)
    table = Table(rows, colWidths=[16 * mm, 26 * mm, 30 * mm, 28 * mm, 38 * mm, 42 * mm],
                  rowHeights=[9 * mm] + [7.4 * mm] * (len(rows) - 1))
    style = [("FONT", (0, 0), (-1, 0), SANS_BOLD, 9), ("FONT", (0, 1), (-1, -1), SANS, 10),
             ("FONT", (0, 1), (0, -1), SANS_BOLD, 10),
             ("TEXTCOLOR", (0, 0), (-1, 0), white), ("BACKGROUND", (0, 0), (-1, 0), INK),
             ("TEXTCOLOR", (0, 1), (-1, -1), INK), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (3, 0), (3, -1), "CENTER"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, GREY_LIGHT])]
    for row in wrong_rows:  # highlight the AI's mistakes
        style += [("BACKGROUND", (0, row), (-1, row), PINK_LIGHT),
                  ("TEXTCOLOR", (4, row), (4, row), PINK), ("FONT", (4, row), (4, row), SANS_BOLD, 10)]
    table.setStyle(TableStyle(style))
    _, table_height = table.wrap(width - 2 * margin, height)
    table.drawOn(c, margin, y - 3 * mm - table_height)
    footer(c, width, content["answer_key"]["header"] + " · " + content["meta"]["footer"])
    c.save()
    return path


# ---------------------------------------------------------------------------
# 3. Patient folders (6 folders x 6 A4 pages)
# ---------------------------------------------------------------------------
def folder_page_frame(c: Canvas, content: dict, folder: dict, page_no: int, title: str) -> float:
    """Shared header/footer for folder pages 2-6. Returns the y where content starts."""
    width, height = A4
    margin = 18 * mm
    common = content["folder_common"]
    c.setFillColor(PINK)
    c.rect(0, height - 6 * mm, width, 6 * mm, stroke=0, fill=1)
    c.setFont(SANS_BOLD, 10)
    c.setFillColor(INK)
    c.drawString(margin, height - 15 * mm, common["clinic_name"])
    c.setFont(SANS, 9)
    c.setFillColor(GREY)
    c.drawString(margin, height - 20 * mm, common["department"])
    c.setFont(SANS_BOLD, 8.5)
    c.setFillColor(PINK)
    c.drawRightString(width - margin, height - 15 * mm, common["stamp"])
    c.setFont(SANS, 9)
    c.setFillColor(GREY)
    c.drawRightString(width - margin, height - 20 * mm,
                      f"{folder['patient_name']} · {folder['age_range']} · Folder {folder['number']}")
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(margin, height - 24 * mm, width - margin, height - 24 * mm)
    c.setFont(SANS_BLACK, 24)
    c.setFillColor(INK)
    c.drawString(margin, height - 36 * mm, title)
    footer(c, width, f"Folder {folder['number']} · page {page_no} of 6 · {content['meta']['footer']}")
    return height - 50 * mm


def draw_stamp(c: Canvas, text: str, cx: float, cy: float, size: float, angle: float = 8) -> None:
    """A rotated double-bordered rubber stamp."""
    c.saveState()
    c.translate(cx, cy)
    c.rotate(angle)
    text_width = pdfmetrics.stringWidth(text, SANS_BLACK, size)
    box_w, box_h = text_width + size * 1.6, size * 2.4
    c.setStrokeColor(PINK)
    c.setLineWidth(2.2)
    c.roundRect(-box_w / 2, -box_h / 2, box_w, box_h, size * 0.3, stroke=1, fill=0)
    c.setLineWidth(0.8)
    inset = size * 0.25
    c.roundRect(-box_w / 2 + inset, -box_h / 2 + inset, box_w - 2 * inset, box_h - 2 * inset,
                size * 0.2, stroke=1, fill=0)
    c.setFillColor(PINK)
    c.setFont(SANS_BLACK, size)
    c.drawCentredString(0, -size * 0.35, text)
    c.restoreState()


def folder_cover(c: Canvas, content: dict, folder: dict) -> None:
    width, height = A4
    margin = 22 * mm
    common = content["folder_common"]
    c.setFillColor(PINK)
    c.rect(0, height - 50 * mm, width, 50 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont(SANS_BLACK, 26)
    c.drawString(margin, height - 25 * mm, common["clinic_name"])
    c.setFont(SANS, 13)
    c.drawString(margin, height - 34 * mm, common["department"])
    # Folder number (the folder's title is NOT shown here: it would give away the verdict)
    c.setFillColor(GREY)
    c.setFont(SANS_BOLD, 14)
    c.drawString(margin, height - 75 * mm, common["folder_label"])
    c.setFillColor(INK)
    c.setFont(SANS_BLACK, 64)
    c.drawString(margin, height - 100 * mm, f"Folder {folder['number']}")
    # Patient details box
    top = height - 118 * mm
    box_h = 52 * mm
    c.setFillColor(GREY_LIGHT)
    c.roundRect(margin, top - box_h, width - 2 * margin, box_h, 4 * mm, stroke=0, fill=1)
    fields = [("Patient", folder["patient_name"]), ("Age range", folder["age_range"]),
              ("Examination", "Breast ultrasound"), ("Reason for scan", folder["scan_reason"])]
    y = top - 13 * mm
    for label, value in fields:
        c.setFont(SANS_BOLD, 10)
        c.setFillColor(GREY)
        c.drawString(margin + 8 * mm, y, label.upper())
        y = draw_text(c, value, margin + 50 * mm, y, width - 2 * margin - 58 * mm, SANS, 13, INK) - 4 * mm
    draw_stamp(c, common["stamp"], width / 2, 62 * mm, 17)
    draw_text(c, common["fictional_note"], margin, 30 * mm, width - 2 * margin, SANS, 9, GREY,
              align="center")
    footer(c, width, f"Folder {folder['number']} · page 1 of 6 · {content['meta']['footer']}")


def folder_scan(c: Canvas, content: dict, folder: dict) -> None:
    width, _ = A4
    common = content["folder_common"]
    top = folder_page_frame(c, content, folder, 2, common["page_titles"]["scan"])
    size_mm = 160
    x = (width - size_mm * mm) / 2
    place_image(c, GRADCAM / "originals" / folder["case_file"], x, top - size_mm * mm, size_mm)
    draw_text(c, common["scan_caption"], 18 * mm, top - size_mm * mm - 10 * mm, width - 36 * mm,
              SANS, 12, GREY, align="center")


def confidence_bars(c: Canvas, probs: dict, predicted: str, x: float, y: float, width: float) -> float:
    for label in ("normal", "benign", "malignant"):
        value = probs[label]
        strong = label == predicted
        c.setFont(SANS_BOLD if strong else SANS, 11)
        c.setFillColor(INK)
        c.drawString(x, y, label.capitalize())
        shown = ">99%" if value >= 0.995 else "<1%" if value < 0.005 else f"{value * 100:.0f}%"
        c.drawRightString(x + width, y, shown)
        y -= 5 * mm
        c.setFillColor(GREY_LIGHT)
        c.roundRect(x, y, width, 4 * mm, 2 * mm, stroke=0, fill=1)
        if value > 0.005:
            c.setFillColor(PINK if strong else GREY)
            c.roundRect(x, y, max(width * value, 4 * mm), 4 * mm, 2 * mm, stroke=0, fill=1)
        y -= 9 * mm
    return y


def folder_ai_report(c: Canvas, content: dict, folder: dict, row: dict) -> None:
    width, _ = A4
    margin = 18 * mm
    common = content["folder_common"]
    fields = common["ai_report_fields"]
    top = folder_page_frame(c, content, folder, 3, common["page_titles"]["ai_report"])
    # Report header table, like a clinical report.
    info = [["Patient", folder["patient_name"], "Examination", "Breast ultrasound"],
            ["Age range", folder["age_range"], "Report type", "Automated AI analysis"]]
    table = Table(info, colWidths=[28 * mm, 55 * mm, 32 * mm, 59 * mm], rowHeights=8 * mm)
    table.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), SANS, 10),
                               ("FONT", (0, 0), (0, -1), SANS_BOLD, 9), ("FONT", (2, 0), (2, -1), SANS_BOLD, 9),
                               ("TEXTCOLOR", (0, 0), (-1, -1), INK), ("TEXTCOLOR", (0, 0), (0, -1), GREY),
                               ("TEXTCOLOR", (2, 0), (2, -1), GREY), ("BACKGROUND", (0, 0), (-1, -1), GREY_LIGHT),
                               ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, 0), 0.4, white)]))
    table.wrap(width - 2 * margin, 50 * mm)
    table.drawOn(c, margin, top - 16 * mm)
    y = top - 26 * mm
    # Left: heatmap. Right: prediction and confidence bars.
    image_mm = 90
    c.setFont(SANS_BOLD, 10)
    c.setFillColor(GREY)
    c.drawString(margin, y, fields["heatmap"].upper())
    place_image(c, GRADCAM / "heatmaps" / folder["case_file"], margin, y - 4 * mm - image_mm * mm, image_mm)
    right_x = margin + (image_mm + 10) * mm
    right_w = width - margin - right_x
    c.drawString(right_x, y, fields["prediction"].upper())
    c.setFont(SANS_BLACK, 34)
    c.setFillColor(PINK)
    c.drawString(right_x, y - 16 * mm, row["pred"].upper())
    c.setFont(SANS_BOLD, 10)
    c.setFillColor(GREY)
    c.drawString(right_x, y - 30 * mm, fields["confidence"].upper())
    probs = {label: float(row[f"prob_{label}"]) for label in ("normal", "benign", "malignant")}
    confidence_bars(c, probs, row["pred"], right_x, y - 38 * mm, right_w)
    # Recommendation box
    y = y - 4 * mm - image_mm * mm - 10 * mm
    box_h = 30 * mm
    c.setFillColor(PINK_LIGHT)
    c.roundRect(margin, y - box_h, width - 2 * margin, box_h, 3 * mm, stroke=0, fill=1)
    c.setFillColor(PINK)
    c.rect(margin, y - box_h, 2 * mm, box_h, stroke=0, fill=1)
    c.setFont(SANS_BOLD, 10)
    c.drawString(margin + 7 * mm, y - 9 * mm, fields["recommendation"].upper())
    draw_text(c, folder["ai_recommendation"], margin + 7 * mm, y - 20 * mm, width - 2 * margin - 14 * mm,
              SANS_BOLD, 17, INK)
    # Mandatory disclaimer line
    c.setStrokeColor(RULE)
    c.line(margin, y - box_h - 10 * mm, width - margin, y - box_h - 10 * mm)
    draw_text(c, common["ai_report_disclaimer"], margin, y - box_h - 17 * mm, width - 2 * margin,
              SANS_BOLD, 11, GREY, align="center")


def folder_real_result(c: Canvas, content: dict, folder: dict, row: dict) -> None:
    width, _ = A4
    margin = 18 * mm
    common = content["folder_common"]
    top = folder_page_frame(c, content, folder, 4, common["page_titles"]["real_result"])
    c.setFont(SANS_BLACK, 22)
    c.setFillColor(PINK)
    c.drawString(margin, top, folder["real_result"])
    size_mm = 138
    x = (width - size_mm * mm) / 2
    image_top = top - 8 * mm
    place_image(c, GRADCAM / "overlays" / folder["case_file"], x, image_top - size_mm * mm, size_mm)
    caption = common["real_result_caption_normal" if row["truth"] == "normal" else "real_result_caption"]
    y = draw_text(c, caption, margin, image_top - size_mm * mm - 7 * mm, width - 2 * margin, SANS, 10,
                  GREY, align="center")
    draw_text(c, folder["real_result_detail"], margin, y - 5 * mm, width - 2 * margin, SANS, 13, INK)


def folder_verdict(c: Canvas, content: dict, folder: dict) -> None:
    width, _ = A4
    margin = 18 * mm
    common = content["folder_common"]
    top = folder_page_frame(c, content, folder, 5, common["page_titles"]["verdict"])
    c.setFont(SANS_BOLD, 13)
    c.setFillColor(GREY)
    c.drawString(margin, top, f"Folder {folder['number']}: {folder['title']}")
    # Huge verdict text, auto-sized to fit in at most two lines.
    size, lines = fit_lines(folder["verdict"], SANS_BLACK, 64, width - 2 * margin, 2)
    y = top - 8 * mm - size
    c.setFont(SANS_BLACK, size)
    c.setFillColor(PINK)
    for line in lines:
        c.drawString(margin, y, line)
        y -= size * 1.05
    # Arabic verdict (draft) on the right
    y = draw_text(c, folder["ar"]["verdict"], margin, y - 4 * mm, width - 2 * margin, AR_BOLD,
                  22 * AR_SCALE, PINK, arabic=True)
    c.setFont(SANS, 7.5)
    c.setFillColor(GREY)
    c.drawRightString(width - margin, y + 2 * mm, "Arabic: draft, needs native review")
    y = draw_text(c, folder["verdict_subtitle"], margin, y - 6 * mm, width - 2 * margin, SANS_BOLD, 16, INK)
    c.setStrokeColor(RULE)
    c.line(margin, y - 2 * mm, width - margin, y - 2 * mm)
    is_error = folder["verdict"] in ("FALSE NEGATIVE", "FALSE POSITIVE")
    c.setFont(SANS_BOLD, 11)
    c.setFillColor(GREY)
    c.drawString(margin, y - 12 * mm, (common["consequences_label"] if is_error else common["lesson_label"]).upper())
    draw_bullets(c, folder["consequences"], margin, y - 22 * mm, width - 2 * margin, SANS, 15, gap=4 * mm)


def folder_safeguard(c: Canvas, content: dict, folder: dict) -> None:
    width, _ = A4
    margin = 18 * mm
    common = content["folder_common"]
    top = folder_page_frame(c, content, folder, 6, common["page_titles"]["safeguard"])
    y = draw_bullets(c, folder["human_safeguard"], margin, top, width - 2 * margin, SANS, 15, gap=3.5 * mm)
    # Arabic version (draft), right-aligned
    c.setStrokeColor(RULE)
    c.line(margin, y, width - margin, y)
    c.setFont(SANS, 7.5)
    c.setFillColor(GREY)
    c.drawString(margin, y - 6 * mm, "Arabic: draft, needs native review")
    y = draw_bullets(c, folder["ar"]["human_safeguard"], margin, y - 12 * mm, width - 2 * margin,
                     AR, 14 * AR_SCALE, gap=1.5 * mm, arabic=True)
    # Discussion question in a pink box at the bottom
    question_lines = wrap(folder["discussion_question"], SANS_BOLD, 18, width - 2 * margin - 16 * mm)
    box_h = (14 + 8 * len(question_lines)) * mm
    box_top = min(y - 6 * mm, 30 * mm + box_h)
    c.setFillColor(PINK_LIGHT)
    c.roundRect(margin, box_top - box_h, width - 2 * margin, box_h, 4 * mm, stroke=0, fill=1)
    c.setFont(SANS_BOLD, 11)
    c.setFillColor(PINK)
    c.drawString(margin + 8 * mm, box_top - 9 * mm, common["discussion_label"].upper())
    draw_text(c, folder["discussion_question"], margin + 8 * mm, box_top - 18 * mm,
              width - 2 * margin - 16 * mm, SANS_BOLD, 18, INK, leading=8 * mm)


def build_folders(content: dict, predictions: dict) -> Path:
    path = OUT / "folders.pdf"
    c = Canvas(str(path), pagesize=A4)
    c.setTitle("AIDA × Hope patient folders (fictional cases)")
    for folder in content["folders"]:
        row = predictions[folder["case_file"]]
        for page in (lambda: folder_cover(c, content, folder),
                     lambda: folder_scan(c, content, folder),
                     lambda: folder_ai_report(c, content, folder, row),
                     lambda: folder_real_result(c, content, folder, row),
                     lambda: folder_verdict(c, content, folder),
                     lambda: folder_safeguard(c, content, folder)):
            page()
            c.showPage()
    c.save()
    return path


# ---------------------------------------------------------------------------
# 4. Tips card (A5, English front, Arabic back)
# ---------------------------------------------------------------------------
def draw_lesion_diagram(c: Canvas, x: float, y: float, w: float, h: float, suspicious: bool) -> None:
    """Simple schematic (not a real scan): smooth wide oval vs irregular tall mass with a shadow."""
    c.setFillColor(HexColor("#8A939C"))
    c.roundRect(x, y, w, h, 3 * mm, stroke=0, fill=1)
    cx, cy = x + w / 2, y + h * 0.58
    if suspicious:
        c.setFillColor(HexColor("#5E666E"))  # dark shadow underneath
        c.rect(cx - w * 0.13, y, w * 0.26, cy - y, stroke=0, fill=1)
        # An irregular outline with short spikes, taller than it is wide.
        points = [(0.0, 1.0), (0.3, 0.72), (0.62, 0.8), (0.55, 0.42), (0.95, 0.2), (0.6, -0.05),
                  (0.8, -0.45), (0.4, -0.55), (0.3, -0.95), (-0.05, -0.7), (-0.4, -0.9), (-0.5, -0.5),
                  (-0.9, -0.3), (-0.6, 0.05), (-0.85, 0.45), (-0.45, 0.6), (-0.35, 0.95)]
        rx, ry = w * 0.11, h * 0.36
        p = c.beginPath()
        p.moveTo(cx + points[0][0] * rx, cy + points[0][1] * ry)
        for px, py in points[1:]:
            p.lineTo(cx + px * rx, cy + py * ry)
        p.close()
        c.setFillColor(HexColor("#1E2328"))
        c.drawPath(p, stroke=0, fill=1)
    else:
        c.setFillColor(HexColor("#1E2328"))
        c.ellipse(cx - w * 0.3, cy - h * 0.16, cx + w * 0.3, cy + h * 0.16, stroke=0, fill=1)


def tips_page(c: Canvas, text: dict, arabic: bool) -> None:
    width, height = A5
    margin = 12 * mm
    body_w = width - 2 * margin
    title_font, body_font = (AR_BOLD, AR) if arabic else (SANS_BLACK, SANS)
    scale = AR_SCALE if arabic else 1
    c.setFillColor(PINK)
    c.rect(0, height - 8 * mm, width, 8 * mm, stroke=0, fill=1)
    y = draw_text(c, text["title"], margin, height - 22 * mm, body_w, title_font, 19 * scale, INK,
                  arabic=arabic)
    y = draw_text(c, text["subtitle"], margin, y - 1 * mm, body_w, body_font, 11 * scale, GREY, arabic=arabic)
    y -= 5 * mm
    number_r = 3.6 * mm
    for number, tip in enumerate(text["tips"], start=1):
        circle_x = width - margin - number_r if arabic else margin + number_r
        c.setFillColor(PINK)
        c.circle(circle_x, y + 1.3 * mm, number_r, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont(SANS_BOLD, 11)
        c.drawCentredString(circle_x, y - 0.3 * mm, str(number))
        text_x = margin if arabic else margin + 2 * number_r + 3 * mm
        y = draw_text(c, tip, text_x, y, body_w - 2 * number_r - 3 * mm, body_font, 12 * scale, INK,
                      arabic=arabic) - 4 * mm
    # Two schematic drawings for tips 3 and 4.
    y -= 3 * mm
    box_w, box_h = (body_w - 8 * mm) / 2, 36 * mm
    order = (("diagram_right", True), ("diagram_left", False)) if arabic else \
            (("diagram_left", False), ("diagram_right", True))
    for index, (key, suspicious) in enumerate(order):
        x = margin + index * (box_w + 8 * mm)
        draw_lesion_diagram(c, x, y - box_h, box_w, box_h, suspicious)
        draw_text(c, text[key], x, y - box_h - 5 * mm, box_w, body_font, 9.5 * scale, INK,
                  align="center", arabic=arabic)
    c.setFillColor(GREY_LIGHT)
    c.roundRect(margin, 12 * mm, body_w, 16 * mm, 2 * mm, stroke=0, fill=1)
    draw_text(c, text["footer"], margin + 4 * mm, 22.5 * mm, body_w - 8 * mm, SANS_BOLD if not arabic else AR_BOLD,
              9 * scale, INK, align="center", arabic=arabic)
    footer(c, width, "AIDA × Hope", y=6 * mm, size=7)
    if arabic:
        c.setFont(SANS, 6.5)
        c.drawString(margin, 6 * mm, "Arabic draft: needs native review")


def build_tips_card(content: dict) -> Path:
    path = OUT / "tips_card.pdf"
    c = Canvas(str(path), pagesize=A5)
    c.setTitle("How to read a breast ultrasound")
    tips_page(c, content["tips_card"]["en"], arabic=False)
    c.showPage()
    tips_page(c, content["tips_card"]["ar"], arabic=True)
    c.showPage()
    c.save()
    return path


# ---------------------------------------------------------------------------
# 5. Take-home cards (85 x 55 mm, 10 per A4 with crop marks)
# ---------------------------------------------------------------------------
CARD_W, CARD_H = 85 * mm, 55 * mm


def qr_image(url: str) -> ImageReader:
    """A QR code rendered at 300 dpi for a 20 mm square."""
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1)
    qr.add_data(url)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    pixels = round(20 / 25.4 * DPI)
    image = image.resize((pixels, pixels), Image.NEAREST)
    buffer = BytesIO()
    image.save(buffer, "PNG", dpi=(DPI, DPI))
    buffer.seek(0)
    return ImageReader(buffer)


def draw_card(c: Canvas, x: float, y: float, text: dict, takehome: dict, qr: ImageReader,
              arabic: bool, credit: str) -> None:
    pad = 4 * mm
    qr_size = 20 * mm
    title_font, body_font, bold_font = (AR_BOLD, AR, AR_BOLD) if arabic else (SANS_BLACK, SANS, SANS_BOLD)
    scale = AR_SCALE if arabic else 1
    c.setFillColor(PINK)
    c.rect(x, y + CARD_H - 2.2 * mm, CARD_W, 2.2 * mm, stroke=0, fill=1)
    # QR column: right side in English, left side in Arabic.
    qr_x = x + pad if arabic else x + CARD_W - pad - qr_size
    qr_y = y + 8.5 * mm
    c.drawImage(qr, qr_x, qr_y, qr_size, qr_size)
    c.setFont(bold_font, 6 * scale)
    c.setFillColor(INK)
    caption = shape_ar(text["qr_caption"]) if arabic else text["qr_caption"]
    c.drawCentredString(qr_x + qr_size / 2, qr_y + qr_size + 1.6 * mm, caption)
    if takehome["qr_url"].startswith("["):  # still a placeholder: say so in print
        c.setFont(SANS_BOLD, 5.5)
        c.setFillColor(PINK)
        c.drawCentredString(qr_x + qr_size / 2, qr_y - 2.6 * mm, takehome["placeholder_label"])
    # Text column
    text_x = x + pad + qr_size + 3 * mm if arabic else x + pad
    text_w = CARD_W - 2 * pad - qr_size - 3 * mm
    top = y + CARD_H - 8.5 * mm
    body = 6.7 * scale
    ty = draw_text(c, text["title"], text_x, top, text_w, title_font, 12 * scale, PINK, arabic=arabic)
    ty = draw_text(c, text["signs_heading"], text_x, ty + 0.3 * mm, text_w, bold_font, 7.1 * scale, INK,
                   arabic=arabic, leading=7.1 * scale * 1.25)
    ty = draw_bullets(c, text["signs"], text_x, ty, text_w, body_font, body, INK, arabic=arabic)
    ty = draw_text(c, text["reassurance"], text_x, ty - 0.8 * mm, text_w, bold_font, body, INK,
                   arabic=arabic, leading=body * 1.25)
    draw_text(c, text["men"], text_x, ty - 0.4 * mm, text_w, body_font, body, GREY, arabic=arabic,
              leading=body * 1.25)
    c.setFont(SANS, 4.6)
    c.setFillColor(GREY)
    c.drawCentredString(x + CARD_W / 2, y + 2.4 * mm, credit)


def crop_marks(c: Canvas, x0: float, y0: float, cols: int, rows: int) -> None:
    """Short cut lines outside the card grid, one per cut, offset so they never touch a card."""
    offset, length = 2 * mm, 6 * mm
    c.setStrokeColor(INK)
    c.setLineWidth(0.25)
    grid_w, grid_h = cols * CARD_W, rows * CARD_H
    for col in range(cols + 1):
        x = x0 + col * CARD_W
        c.line(x, y0 - offset, x, y0 - offset - length)
        c.line(x, y0 + grid_h + offset, x, y0 + grid_h + offset + length)
    for row in range(rows + 1):
        y = y0 + row * CARD_H
        c.line(x0 - offset, y, x0 - offset - length, y)
        c.line(x0 + grid_w + offset, y, x0 + grid_w + offset + length, y)


def build_takehome(content: dict) -> Path:
    path = OUT / "takehome_cards.pdf"
    width, height = A4
    takehome = content["takehome"]
    qr = qr_image(takehome["qr_url"])
    cols, rows = 2, 5
    # Centred grid, so the Arabic page lines up when printed double-sided.
    x0, y0 = (width - cols * CARD_W) / 2, (height - rows * CARD_H) / 2
    c = Canvas(str(path), pagesize=A4)
    c.setTitle("Know Your Normal take-home cards")
    for lang in ("en", "ar"):
        for row in range(rows):
            for col in range(cols):
                draw_card(c, x0 + col * CARD_W, y0 + row * CARD_H, takehome[lang], takehome, qr,
                          lang == "ar", content["meta"]["footer"])
        crop_marks(c, x0, y0, cols, rows)
        c.setFont(SANS, 6)
        c.setFillColor(GREY)
        side = "Front (English)" if lang == "en" else "Back (Arabic DRAFT)"
        # Printer note in the top margin, between the crop marks.
        c.drawString(x0 + 9 * mm, height - 6 * mm, f"{side}. Print at 100%, double-sided, flip on long edge.")
        c.showPage()
    c.save()
    return path


# ---------------------------------------------------------------------------
# 6. Poster (A2 portrait)
# ---------------------------------------------------------------------------
def text_height(text: str, font: str, size: float, width: float, arabic: bool = False,
                leading: float | None = None) -> float:
    """Height that draw_text() will use for this text."""
    leading = leading or size * (1.45 if arabic else 1.25)
    return len(wrap(text, font, size, width, arabic)) * leading


def build_poster(content: dict, booth: list[dict]) -> Path:
    path = OUT / "poster_A2.pdf"
    width, height = A2
    margin = 28 * mm
    body_w = width - 2 * margin
    poster, en, ar = content["poster"], content["poster"]["en"], content["poster"]["ar"]
    c = Canvas(str(path), pagesize=A2)
    c.setTitle("Can you beat the AI?")

    # --- Header band: headline in both languages -------------------------------
    band_h = 120 * mm
    c.setFillColor(PINK)
    c.rect(0, height - band_h, width, band_h, stroke=0, fill=1)
    size, lines = fit_lines(en["headline"], SANS_BLACK, 120, body_w, 1)
    c.setFont(SANS_BLACK, size)
    c.setFillColor(white)
    c.drawString(margin, height - 56 * mm, lines[0])
    draw_text(c, ar["headline"], margin, height - 91 * mm, body_w, AR_BOLD, 52 * AR_SCALE, white, arabic=True)
    c.setFont(SANS_BOLD, 18)
    c.drawString(margin, height - 111 * mm, poster["organisers"])

    # --- Station message ---------------------------------------------------------
    y = height - band_h - 24 * mm
    size, _ = fit_lines(en["station_message"], SANS_BLACK, 48, body_w, 1)
    y = draw_text(c, en["station_message"], margin, y, body_w, SANS_BLACK, size, INK)
    size, _ = fit_lines(ar["station_message"], AR_BOLD, 44 * AR_SCALE, body_w, 1, arabic=True)
    y = draw_text(c, ar["station_message"], margin, y - 2 * mm, body_w, AR_BOLD, size, INK, arabic=True)

    # --- Three steps, boxes sized to their text ----------------------------------
    y -= 10 * mm
    c.setFont(SANS_BOLD, 22)
    c.setFillColor(GREY)
    c.drawString(margin, y, en["steps_heading"].upper())
    c.setFont(AR_BOLD, 24 * AR_SCALE)
    c.drawRightString(width - margin, y, shape_ar(ar["steps_heading"]))
    y -= 10 * mm
    col_gap = 12 * mm
    col_w = (body_w - 2 * col_gap) / 3
    text_w = col_w - 16 * mm
    en_size, ar_size = 20, 17 * AR_SCALE
    box_h = 32 * mm + max(text_height(s_en, SANS_BOLD, en_size, text_w)
                          + text_height(s_ar, AR, ar_size, text_w, arabic=True)
                          for s_en, s_ar in zip(en["steps"], ar["steps"])) + 5 * mm
    for index, (step_en, step_ar) in enumerate(zip(en["steps"], ar["steps"])):
        x = margin + index * (col_w + col_gap)
        c.setFillColor(GREY_LIGHT)
        c.roundRect(x, y - box_h, col_w, box_h, 6 * mm, stroke=0, fill=1)
        c.setFillColor(PINK)
        c.circle(x + 16 * mm, y - 14 * mm, 8 * mm, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont(SANS_BLACK, 30)
        c.drawCentredString(x + 16 * mm, y - 19.3 * mm, str(index + 1))
        ty = draw_text(c, step_en, x + 8 * mm, y - 32 * mm, text_w, SANS_BOLD, en_size, INK)
        draw_text(c, step_ar, x + 8 * mm, ty - 3 * mm, text_w, AR, ar_size, INK, arabic=True)
    y -= box_h + 12 * mm

    # --- Honest model numbers, full width ----------------------------------------
    y = draw_text(c, en["model_line"], margin, y, body_w, SANS_BLACK, 30, PINK)
    y = draw_text(c, en["model_note"], margin, y - 1 * mm, body_w, SANS, 17, INK)
    y = draw_text(c, ar["model_line"], margin, y - 3 * mm, body_w, AR_BOLD, 24 * AR_SCALE, PINK, arabic=True)
    y = draw_text(c, ar["model_note"], margin, y, body_w, AR, 16 * AR_SCALE, INK, arabic=True)
    y -= 6 * mm

    # --- Results row: confusion matrix | two booth heatmaps ------------------------
    matrix_mm = 115
    matrix_h = place_image(c, DATA / "reports" / "confusion_matrix.png", margin, y - 103.5 * mm, matrix_mm,
                           border=None)
    draw_text(c, en["confusion_caption"], margin, y - matrix_h - 6 * mm, matrix_mm * mm, SANS, 13, GREY)
    right_x = margin + matrix_mm * mm + 12 * mm
    right_w = width - margin - right_x
    heat_mm = min((right_w / mm - 8) / 2, 92)
    # One heatmap on the tumor, one elsewhere. Heatmaps only: no outline, no case
    # number and no label, so nothing on the poster gives away a booth answer.
    examples = [next(case for case in booth if case["case_id"] == case_id) for case_id in ("01", "25")]
    top = y - 6 * mm
    for index, case in enumerate(examples):
        place_image(c, DATA / case["heatmap"], right_x + index * (heat_mm + 8) * mm, top - heat_mm * mm, heat_mm)
    ty = draw_text(c, en["heatmap_caption"], right_x, top - heat_mm * mm - 7 * mm, right_w, SANS, 13, GREY)
    y = min(ty, y - matrix_h - 6 * mm - text_height(en["confusion_caption"], SANS, 13, matrix_mm * mm)) - 8 * mm

    # --- WHO theme ---------------------------------------------------------------
    c.setStrokeColor(RULE)
    c.setLineWidth(1)
    c.line(margin, y, width - margin, y)
    y = draw_text(c, en["theme"], margin, y - 11 * mm, body_w, SANS_BOLD, 18, INK, align="center")
    y = draw_text(c, ar["theme"], margin, y - 1 * mm, body_w, AR, 16 * AR_SCALE, INK, align="center", arabic=True)

    # --- Credits and disclaimer along the bottom ----------------------------------
    credits_h = 58 * mm
    if y < credits_h + 4 * mm:
        sys.exit(f"Poster content overlaps the credits band by {(credits_h + 4 * mm - y) / mm:.0f} mm")
    c.setFillColor(GREY_LIGHT)
    c.rect(0, 0, width, credits_h, stroke=0, fill=1)
    cy = credits_h - 11 * mm
    c.setFont(SANS_BOLD, 14)
    c.setFillColor(INK)
    c.drawString(margin, cy, poster["credits_heading"].upper() + ":  " + poster["organisers"])
    cy -= 8 * mm
    for citation in content["credits"]["full"]:
        cy = draw_text(c, citation, margin, cy, body_w, SANS, 11.5, GREY) - 2 * mm
    c.setFont(SANS_BOLD, 15)
    c.setFillColor(PINK)
    c.drawString(margin, 10 * mm, en["disclaimer"])
    c.setFont(AR_BOLD, 15 * AR_SCALE)
    c.drawRightString(width - margin, 10 * mm, shape_ar(ar["disclaimer"]))
    c.save()
    return path


# ---------------------------------------------------------------------------
# Previews
# ---------------------------------------------------------------------------
def export_previews(pdfs: dict[str, Path]) -> list[Path]:
    """Page 1 of every PDF, plus every page of folder 1, as PNG."""
    import pypdfium2 as pdfium

    PREVIEWS.mkdir(parents=True, exist_ok=True)
    for old in PREVIEWS.glob("*.png"):
        old.unlink()
    written = []

    def render(pdf_path: Path, page_index: int, name: str, dpi: int) -> None:
        document = pdfium.PdfDocument(str(pdf_path))
        image = document[page_index].render(scale=dpi / 72).to_pil()
        target = PREVIEWS / name
        image.save(target)
        written.append(target)
        document.close()

    for key, pdf_path in pdfs.items():
        render(pdf_path, 0, f"{key}_p1.png", 40 if key == "poster_A2" else 110)
    for key in ("tips_card", "takehome_cards"):  # their Arabic side is page 2
        render(pdfs[key], 1, f"{key}_p2_arabic.png", 110)
    for page in range(1, 6):
        render(pdfs["folders"], page, f"folders_p{page + 1}.png", 110)
    return written


def main() -> None:
    notes = register_fonts()
    content, booth, predictions = load_inputs()
    OUT.mkdir(exist_ok=True)
    pdfs = {"case_cards": build_case_cards(content, booth),
            "answer_key": build_answer_key(content, booth),
            "folders": build_folders(content, predictions),
            "tips_card": build_tips_card(content),
            "takehome_cards": build_takehome(content),
            "poster_A2": build_poster(content, booth)}
    previews = export_previews(pdfs)
    for name, pdf in pdfs.items():
        print(f"{pdf.relative_to(ROOT)}  ({pdf.stat().st_size / 1e6:.1f} MB)")
    print(f"{len(previews)} previews in {PREVIEWS.relative_to(ROOT)}")
    for note in notes:
        print("NOTE:", note)


if __name__ == "__main__":
    main()
