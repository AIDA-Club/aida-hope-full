"""Shared UI, validated local data, model adapter, and anonymous CSV logging.

Public mode (set by public_app.py for the public website) never writes any file:
no results log, no cached model presets, no uploads.
"""
from __future__ import annotations

import base64
import csv
import html
import json
import math
import pickle
import threading
from statistics import median
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
CLASSES = ("normal", "benign", "malignant")
RESULT_FIELDS = ("timestamp", "case_id", "first_answer", "ai_pred", "final_answer", "truth")
RESULTS_PATH = ROOT / "data" / "results.csv"
_CSV_LOCK = threading.Lock()
ASSET_FIELDS = ("image", "print_image", "heatmap", "mask_overlay")
PUBLIC_ASSET_FIELDS = ("image", "heatmap", "mask_overlay")  # the website has no print images


class BoothError(ValueError):
    """An error code whose visitor-facing message lives in the translation files."""

    def __init__(self, code: str, case_id=None, field: str | None = None):
        super().__init__(code)
        self.code, self.case_id, self.field = code, case_id, field

    def ui_message(self) -> str:
        message = t(self.code)
        if self.field is not None:
            message += " " + t("validation_detail", case_id=self.case_id if self.case_id is not None
                                else t("unknown_case"), field=self.field)
        return message


def public_mode() -> bool:
    """True on the public website (public_app.py sets it on every run), False at the booth."""
    return bool(st.session_state.get("public_mode"))


def card_case_id(text) -> str | None:
    """A case number typed by the visitor (1-30, "07", "#7", Arabic-Indic digits) as a case id, else None."""
    if not isinstance(text, str):
        return None
    text = text.strip().lstrip("#").strip()
    if not text.isdecimal() or len(text) > 3:
        return None
    number = int(text)
    return f"{number:02d}" if 1 <= number <= 30 else None


def language() -> str:
    return st.session_state.get("lang", "en")


def translations(lang: str) -> dict:
    return json.loads((ROOT / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


def t(key: str, **values) -> str:
    return translations(language())[key].format(**values)


def frame() -> None:
    st.session_state.setdefault("lang", "en")
    # Keep the language in a non-widget key so page-switch widget cleanup cannot erase it.
    st.sidebar.radio(translations("en")["language"], ("en", "ar"), key="language_choice", horizontal=True,
                     index=("en", "ar").index(language()), on_change=update_language,
                     format_func=lambda code: translations(code)["language_name"])
    rtl = language() == "ar"
    direction = "rtl" if rtl else "ltr"
    font = '"Tahoma", "Segoe UI", Arial, sans-serif' if rtl else '"Segoe UI", Arial, sans-serif'
    st.markdown(f"""<style>
    .stApp {{font-family:{font}; direction:{direction};}}
    .stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label {{font-family:{font};}}
    [data-testid="stMainBlockContainer"] {{max-width:1700px; padding-top:1.5rem;}}
    [data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {{gap:0.45rem;}}
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
    [data-testid="stWidgetLabel"] p {{font-size:1.25rem; line-height:1.65;}}
    h1 {{font-size:3.2rem !important; letter-spacing:-0.03em;}}
    h2 {{font-size:2rem !important;}}
    .stButton button, .stFormSubmitButton button {{min-height:72px; border-radius:16px;
        border:1px solid #DFC8D2; padding:0.8rem 1.2rem;}}
    .stButton button p, .stFormSubmitButton button p {{font-size:1.35rem; font-weight:650;}}
    .stButton button:hover {{border-color:#C63D76; background:#FBE9F1;}}
    [data-testid="stTextInput"] input {{font-size:1.4rem; min-height:54px;}}
    [data-testid="stSidebar"] {{border-inline-end:1px solid #EDDCE4;}}
    /* Collapsed, Streamlit slides the sidebar 300px left; in RTL it starts on the right, so
       that would leave a strip over the page. A collapsed sidebar is never meant to be seen. */
    [data-testid="stSidebar"][aria-expanded="false"],
    [data-testid="stSidebar"][aria-expanded="false"] * {{visibility:hidden !important;}}
    [data-testid="stSidebar"] a {{font-size:1.1rem;}}
    [data-testid="stVerticalBlock"], [data-testid="stMarkdownContainer"],
    [data-testid="stWidgetLabel"], [data-testid="stSidebarNav"] {{direction:{direction};}}
    [data-testid="stMarkdownContainer"] {{text-align:{'right' if rtl else 'left'};}}
    [data-testid="stMarkdownContainer"] ul, [data-testid="stMarkdownContainer"] ol {{
        direction:{direction}; padding-inline-start:1.4em; padding-{'left' if rtl else 'right'}:0;
        margin-{'left' if rtl else 'right'}:0;}}
    [data-testid="stMarkdownContainer"] li {{text-align:{'right' if rtl else 'left'};}}
    .booth-footer {{border-top:1px solid #EDDCE4; margin-top:1.2rem;
        padding-top:1rem; color:#526574; font-size:1.05rem;}}
    .booth-credits {{font-size:0.9rem;}}
    .booth-learn {{background:#FBE7F0; border-radius:12px; padding:0.6rem 1rem; text-align:center;
        font-size:1.5rem; font-weight:750; color:#A52C60; margin-top:0.4rem;}}
    .booth-eyebrow {{color:#A52C60; font-weight:700; letter-spacing:0.08em;}}
    .booth-prediction {{font-size:2.8rem; font-weight:750; color:#A52C60; margin:0.4rem 0;}}
    .booth-result {{background:#FBE7F0; border:1px solid #E6B4CA; border-radius:16px;
        padding:0.7rem 1rem; font-size:1.8rem; font-weight:750; margin:0.35rem 0;}}
    .booth-result-truth {{font-size:1.2rem; font-weight:600;}}
    [data-testid="stProgress"] [data-testid="stMarkdownContainer"] p {{line-height:1.3;}}
    .booth-error-note {{background:#FBE7F0; color:#A52C60; border-radius:8px;
        padding:0.4rem 0.8rem; font-size:1rem; margin-bottom:0.7rem;}}
    .st-key-case_number input {{font-size:2.25rem; font-weight:700; min-height:72px;}}
    .st-key-choose_case {{padding:0.8rem 1rem; background:#F6EAF0; border-radius:16px;}}
    .booth-gauge {{display:grid; place-items:center; width:340px; height:340px;
        max-width:100%; border-radius:50%; margin:1.5rem auto;}}
    .booth-gauge-center {{display:flex; flex-direction:column; justify-content:center;
        align-items:center; width:270px; height:270px; border-radius:50%; background:#FFF9FB;}}
    .booth-gauge-number {{font-size:4.5rem; font-weight:750; color:#A52C60; line-height:1.1;}}
    .booth-gauge-label {{font-size:2rem; font-weight:700;}}
    .booth-zoom-toggle {{position:absolute; opacity:0; pointer-events:none;}}
    .booth-zoom {{display:block; cursor:zoom-in; margin:0;}}
    .booth-zoom img {{display:block; width:100%; max-width:560px; border-radius:12px;
        border:1px solid #EDDCE4;}}
    .booth-zoom-toggle:checked + .booth-zoom {{position:fixed; inset:0; z-index:1000000; cursor:zoom-out;
        display:flex; align-items:center; justify-content:center; background:rgba(20,24,30,0.94);
        padding:8px;}}
    .booth-zoom-toggle:checked + .booth-zoom img {{width:auto; height:auto; max-width:100%;
        max-height:100%; border-radius:0; border:0;}}
    .booth-zoom-caption {{color:#526574; font-size:0.95rem; margin:0.3rem 0 0.6rem;}}
    .booth-score {{font-size:1.6rem; font-weight:750; color:#A52C60; text-align:center;}}
    .booth-station {{font-size:1.5rem; font-weight:750; text-align:center; margin:0.6rem 0;}}
    [data-testid="stSlider"] div:has(> div > input[type="range"]) {{width:22px; height:22px;}}
    .st-key-slide_view {{position:sticky; top:3.6rem; z-index:5; background:#FFF9FB; padding-bottom:0.3rem;}}
    .st-key-slide_view img {{max-height:46vh; object-fit:contain; border-radius:10px;}}
    @media (max-width: 640px) {{
        [data-testid="stMainBlockContainer"] {{padding-left:1rem; padding-right:1rem; padding-top:1rem;}}
        h1 {{font-size:2.1rem !important;}}
        h2 {{font-size:1.5rem !important;}}
        h3 {{font-size:1.3rem !important;}}
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
        [data-testid="stWidgetLabel"] p {{font-size:1.08rem;}}
        .stButton button, .stFormSubmitButton button {{min-height:58px;}}
        .stButton button p, .stFormSubmitButton button p {{font-size:1.2rem;}}
        .booth-prediction {{font-size:1.9rem;}}
        .booth-result {{font-size:1.35rem;}}
        .booth-learn {{font-size:1.2rem;}}
        .booth-gauge {{width:250px; height:250px;}}
        .booth-gauge-center {{width:196px; height:196px;}}
        .booth-gauge-number {{font-size:3.2rem;}}
        .booth-gauge-label {{font-size:1.5rem;}}
        [data-testid="stSlider"] div:has(> div > input[type="range"]) {{width:28px; height:28px;}}
        .st-key-slide_view img {{max-height:30vh;}}
    }}
    </style>""", unsafe_allow_html=True)
    st.sidebar.caption(t("sidebar_note"))


def update_language() -> None:
    st.session_state["lang"] = st.session_state["language_choice"]


def footer() -> None:
    """Shown on every page: the disclaimer and short dataset credits.

    A page can swap the credits line for its own by setting st.session_state["footer_credits"]
    to another translation key (the public Challenge uses the image credits).
    """
    credits = st.session_state.pop("footer_credits", None) or "credits_short"
    st.markdown(f'<div class="booth-footer"><strong>{html.escape(t("disclaimer"))}</strong><br>'
                f'<span class="booth-credits">{html.escape(t(credits))}</span></div>',
                unsafe_allow_html=True)


@st.cache_data(show_spinner=False, max_entries=128)
def _jpeg_data_uri(path: str, modified: float) -> str:
    from PIL import Image

    buffer = BytesIO()
    Image.open(path).convert("RGB").save(buffer, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def zoomable_image(path: Path, caption: str, key: str) -> None:
    """A full-width image; tapping it opens it full screen (tap again to close). No JavaScript."""
    source = _jpeg_data_uri(str(path), path.stat().st_mtime)
    label = html.escape(caption, quote=True)
    st.markdown(f'<input type="checkbox" id="zoom-{key}" class="booth-zoom-toggle" aria-label="{label}">'
                f'<label for="zoom-{key}" class="booth-zoom" title="{html.escape(t("zoom_hint"), quote=True)}">'
                f'<img src="{source}" alt="{label}"></label>'
                f'<div class="booth-zoom-caption">{html.escape(caption)} · {html.escape(t("zoom_hint"))}</div>',
                unsafe_allow_html=True)


def asset_path(value: str, case_id=None, field: str | None = None) -> Path:
    data_root = (ROOT / "data").resolve()
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise BoothError("data_invalid", case_id, field)
    candidate = (data_root / value).resolve()
    if not candidate.is_relative_to(data_root) or not candidate.is_file():
        raise BoothError("asset_missing", case_id, field)
    return candidate


def load_cases(assets: tuple[str, ...] = ASSET_FIELDS) -> dict[str, dict]:
    """Validate data/booth_set.json. `assets` = the image fields whose files must exist."""
    try:
        cases = json.loads((ROOT / "data" / "booth_set.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BoothError("data_missing", field="booth_set.json") from exc
    if not isinstance(cases, list) or len(cases) != 30:
        raise BoothError("data_invalid", field="case_count")
    required = ("case_id", "source_file", "image", "print_image", "heatmap", "mask_overlay",
                "truth", "ai_pred", "ai_probs", "correct", "error_type", "cam_mask_overlap")
    indexed = {}
    for case in cases:
        if not isinstance(case, dict):
            raise BoothError("data_invalid", field="case")
        for field in required:
            if field not in case:
                raise BoothError("field_missing", case.get("case_id"), field)
        cid = case["case_id"]
        if not isinstance(cid, str) or cid not in {f"{i:02d}" for i in range(1, 31)} or cid in indexed:
            raise BoothError("data_invalid", cid, "case_id")
        for field in ("truth", "ai_pred"):
            if case[field] not in CLASSES:
                raise BoothError("data_invalid", cid, field)
        probs = case["ai_probs"]
        if not isinstance(probs, dict) or set(probs) != set(CLASSES):
            raise BoothError("data_invalid", cid, "ai_probs")
        for label, probability in probs.items():
            if (isinstance(probability, bool) or not isinstance(probability, (int, float))
                    or not math.isfinite(probability) or not 0 <= probability <= 1):
                raise BoothError("data_invalid", cid, f"ai_probs.{label}")
        overlap = case["cam_mask_overlap"]
        if overlap is not None and (isinstance(overlap, bool) or not isinstance(overlap, (int, float))
                                    or not math.isfinite(overlap) or not 0 <= overlap <= 1):
            raise BoothError("data_invalid", cid, "cam_mask_overlap")
        if not math.isclose(sum(probs.values()), 1, abs_tol=0.01):
            raise BoothError("data_invalid", cid, "ai_probs")
        correct = case["truth"] == case["ai_pred"]
        error_type = (None if correct else "false_negative" if case["truth"] == "malignant"
                      else "false_positive" if case["ai_pred"] == "malignant" else "other_confusion")
        if type(case["correct"]) is not bool or case["correct"] != correct:
            raise BoothError("data_invalid", cid, "correct")
        if case["error_type"] != error_type:
            raise BoothError("data_invalid", cid, "error_type")
        if not isinstance(case["source_file"], str) or not case["source_file"]:
            raise BoothError("data_invalid", cid, "source_file")
        for field in assets:
            asset_path(case[field], cid, field)
        indexed[cid] = case
    return indexed


def booth_set_scores() -> dict | None:
    """The AI's score on the booth cases and on the full test set, counted from data/booth_set.json
    and data/reports/metrics.json (never typed in). None if either file cannot be read."""
    try:
        cases = json.loads((ROOT / "data" / "booth_set.json").read_text(encoding="utf-8"))
        metrics = json.loads((ROOT / "data" / "reports" / "metrics.json").read_text(encoding="utf-8"))
        matrix = metrics["confusion_matrix"]["matrix"]
        test_right, test_n = sum(matrix[i][i] for i in range(len(matrix))), metrics["n_test"]
        return {"n": len(cases), "right": sum(case["correct"] is True for case in cases),
                "test_right": test_right, "test_n": test_n, "test_percent": test_right / test_n * 100}
    except (OSError, ValueError, KeyError, TypeError, IndexError, ZeroDivisionError):
        return None


def booth_set_note() -> str | None:
    """Why the AI scores lower on the booth cases than on the full test set."""
    scores = booth_set_scores()
    return t("booth_set_note", **scores) if scores else None


def start_round(case: dict) -> None:
    # Snapshot the case, so replacing the dataset mid-round cannot change its truth.
    st.session_state["round"] = {"case": case, "phase": "first", "first_answer": None,
                                 "final_answer": None, "logged": False}


def choose_answer(answer: str, final: bool = False) -> None:
    round_ = st.session_state["round"]
    round_["final_answer" if final else "first_answer"] = answer
    round_["phase"] = "truth" if final else "ai"


def set_phase(phase: str) -> None:
    st.session_state["round"]["phase"] = phase


def keep_answer() -> None:
    round_ = st.session_state["round"]
    round_["final_answer"] = round_["first_answer"]
    round_["phase"] = "truth"


def next_visitor() -> None:
    st.session_state.pop("round", None)
    st.session_state["case_number"] = ""


def save_round(round_: dict, destination: Path | None = None) -> None:
    """One append per completed session round; reruns never duplicate a saved row."""
    if round_["logged"]:
        return
    if public_mode():  # the public website never writes visitor data
        raise BoothError("log_error")
    case = round_["case"]
    row = dict(zip(RESULT_FIELDS, (datetime.now(timezone.utc).isoformat(), case["case_id"],
               round_["first_answer"], case["ai_pred"], round_["final_answer"], case["truth"])))
    if any(row[key] not in CLASSES for key in RESULT_FIELDS[2:]):
        raise BoothError("log_error")
    destination = destination or RESULTS_PATH
    with _CSV_LOCK:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a+", encoding="utf-8", newline="") as handle:
            handle.seek(0)
            header = next(csv.reader(handle), None)
            if header is not None and header != list(RESULT_FIELDS):
                raise BoothError("log_error")
            handle.seek(0, 2)
            writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
            if header is None:
                writer.writeheader()
            writer.writerow(row)
            handle.flush()
        round_["logged"] = True


def load_model_bundle() -> tuple:
    """Only unpickle a trusted staff-provided local model; never accept uploads."""
    metadata = json.loads((ROOT / "models" / "wdbc_features.json").read_text(encoding="utf-8"))
    features = metadata.get("features") if isinstance(metadata, dict) else metadata
    if isinstance(features, dict):
        features = [dict(spec, name=name) for name, spec in features.items()]
    if not isinstance(features, list) or len(features) < 5:
        raise BoothError("model_invalid")
    names = []
    for feature in features:
        if not isinstance(feature, dict) or not isinstance(feature.get("name"), str):
            raise BoothError("model_invalid")
        bounds = [feature.get(key) for key in ("min", "median", "max")]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
               for x in bounds) or not bounds[0] <= bounds[1] <= bounds[2] or bounds[0] == bounds[2]:
            raise BoothError("model_invalid")
        names.append(feature["name"])
    if len(set(names)) != len(names):
        raise BoothError("model_invalid")
    with (ROOT / "models" / "wdbc_model.pkl").open("rb") as handle:
        model = pickle.load(handle)
    if not callable(getattr(model, "predict_proba", None)) or len(getattr(model, "classes_", [])) != 2:
        raise BoothError("model_invalid")
    if getattr(model, "n_features_in_", len(features)) != len(features):
        raise BoothError("model_invalid")
    model_names = getattr(model, "feature_names_in_", None)
    if model_names is not None and list(model_names) != names:
        raise BoothError("model_invalid")
    mapping = {"0": "malignant", "1": "benign", "malignant": "malignant", "benign": "benign"}
    if isinstance(metadata, dict):
        mapping.update({str(key).lower(): value for key, value in metadata.get("class_labels", {}).items()})
    labels = [mapping.get(str(label).lower()) for label in model.classes_]
    if set(labels) != {"benign", "malignant"}:
        raise BoothError("model_invalid")
    return model, features, labels


def malignant_probability(model, values: list[float], labels: list[str]) -> float:
    probabilities = [float(p) for p in model.predict_proba([values])[0]]
    if len(probabilities) != 2 or any(not math.isfinite(p) or not 0 <= p <= 1 for p in probabilities):
        raise BoothError("model_invalid")
    if not math.isclose(sum(probabilities), 1, abs_tol=0.01):
        raise BoothError("model_invalid")
    return probabilities[labels.index("malignant")]


def prepare_class_medians() -> dict:
    """Reconstruct train_wdbc.py's training split without refitting the model.

    Verify its sample count and scaler means before using any training presets.
    The sklearn WDBC dataset is bundled locally; no download is performed.
    """
    from sklearn.datasets import load_breast_cancer
    from sklearn.model_selection import train_test_split

    metadata_path = ROOT / "models" / "wdbc_features.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if isinstance(metadata, dict) and "class_medians" in metadata:
        return metadata
    if public_mode():  # computing the presets would rewrite the metadata file
        raise BoothError("presets_mismatch")
    model, features, _ = load_model_bundle()
    dataset = load_breast_cancer()
    feature_indexes = [list(dataset.feature_names).index(feature["name"]) for feature in features]
    measurements = dataset.data[:, feature_indexes]
    labels = dataset.target_names[dataset.target]
    train, _, train_labels, _ = train_test_split(measurements, labels, test_size=0.2,
                                                stratify=labels, random_state=42)
    scaler = next((step for _, step in getattr(model, "steps", []) if hasattr(step, "mean_")), None)
    if (scaler is None or int(scaler.n_samples_seen_) != len(train)
            or not all(math.isclose(float(a), float(b), rel_tol=1e-8, abs_tol=1e-8)
                       for a, b in zip(scaler.mean_, train.mean(axis=0)))):
        raise BoothError("presets_mismatch")
    medians = {label: {feature["name"]: float(median(train[train_labels == label, index]))
                       for index, feature in enumerate(features)} for label in ("benign", "malignant")}
    updated = dict(metadata) if isinstance(metadata, dict) else {"features": metadata}
    updated["class_medians"] = medians
    updated["preset_source"] = {"dataset": "sklearn.datasets.load_breast_cancer", "seed": 42,
                                 "test_size": 0.2, "stratified": True, "n_train": len(train),
                                 "class_counts": {label: int(sum(train_labels == label))
                                                  for label in ("benign", "malignant")},
                                 "verified_against_model_scaler": True}
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(metadata_path)
    return updated


def load_class_medians(features: list[dict]) -> dict[str, dict[str, float]]:
    metadata = json.loads((ROOT / "models" / "wdbc_features.json").read_text(encoding="utf-8"))
    if not isinstance(metadata, dict) or "class_medians" not in metadata:
        metadata = prepare_class_medians()
    medians = metadata["class_medians"]
    if not isinstance(medians, dict):
        raise BoothError("presets_mismatch")
    for label in ("benign", "malignant"):
        for feature in features:
            value = medians.get(label, {}).get(feature["name"])
            if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                    or not feature["min"] <= value <= feature["max"]):
                raise BoothError("presets_mismatch")
    return medians
