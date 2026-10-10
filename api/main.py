"""Thin HTTP API around the existing Python logic, for the React website in frontend/.

Run with: .venv\\Scripts\\python.exe -m uvicorn api.main:app --port 8000

Every number, prediction and answer comes from the same functions the Streamlit app uses
(booth.py, challenge_logic.py, tweak_logic.py, aida_chat.py, slide_image.py). Like the public
Streamlit site (public_app.py), the API never writes visitor data to disk: no results log,
no uploads. Per-visitor state lives in server memory (api/sessions.py).
"""
from __future__ import annotations

import json
import math
import os
import random
import tomllib
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import aida_chat as chat
import booth
import challenge_logic as rules
import slide_image
import tweak_logic
from api.sessions import COOKIE, IDLE_SECONDS, Session, SessionStore

ROOT = booth.ROOT
LANGS = ("en", "ar")
SECRET_KEYS = ("PROVIDER", "API_KEY", "MODEL", "BASE_URL", "DAILY_CALL_CAP")
FRONTEND = ROOT / "frontend" / "dist"
# Real images used as illustrations on Home and About. Folder 6 is not one of the 30 booth
# cards, so showing its heatmap cannot spoil a card. Home shows card originals only.
ABOUT_IMAGES = {"original": ROOT / "data" / "reports" / "gradcam_all" / "originals" / "malignant_id_153.png",
                "heatmap": ROOT / "data" / "reports" / "gradcam_all" / "heatmaps" / "malignant_id_153.png",
                "confusion-matrix": ROOT / "data" / "reports" / "confusion_matrix.png"}
HOME_CARDS = ("01", "09", "21")

app = FastAPI(title="AIDA × Hope API", docs_url="/api/docs", openapi_url="/api/openapi.json")
sessions = SessionStore()


# ---------------------------------------------------------------------------
# Plumbing
# ---------------------------------------------------------------------------
def visitor(request: Request, response: Response) -> Session:
    sid, session = sessions.get(request.cookies.get(COOKIE))
    if sid != request.cookies.get(COOKIE):
        response.set_cookie(COOKIE, sid, max_age=IDLE_SECONDS, httponly=True, samesite="lax")
    return session


def problem(status: int, code: str, **extra) -> HTTPException:
    """An error whose visitor-facing text is the translation key `code`."""
    return HTTPException(status, detail={"code": code, **extra})


@app.exception_handler(booth.BoothError)
def booth_error(_: Request, exc: booth.BoothError) -> JSONResponse:
    return JSONResponse({"detail": {"code": exc.code, "case_id": exc.case_id, "field": exc.field}}, 500)


def _mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


@lru_cache(maxsize=4)
def _cases(_modified: float) -> dict[str, dict]:
    return booth.load_cases(booth.PUBLIC_ASSET_FIELDS)


def cases() -> dict[str, dict]:
    """The validated 30 booth cases; re-read when data/booth_set.json changes."""
    return _cases(_mtime(ROOT / "data" / "booth_set.json"))


@lru_cache(maxsize=4)
def _translations(lang: str, _modified: float) -> dict:
    return booth.translations(lang)


def translations(lang: str) -> dict:
    return _translations(lang, _mtime(ROOT / "i18n" / f"{lang}.json"))


def checked_lang(lang: str) -> str:
    if lang not in LANGS:
        raise problem(422, "unknown_language")
    return lang


# ---------------------------------------------------------------------------
# General
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/i18n/{lang}")
def i18n(lang: str) -> dict:
    """The app's existing translations (i18n/en.json, i18n/ar.json)."""
    return translations(checked_lang(lang))


@app.get("/api/cards/{cid}/original")
def card_original(cid: str) -> FileResponse:
    """A booth card's original ultrasound (printed on the card itself, so never a spoiler)."""
    case = cases().get(cid)
    if case is None:
        raise problem(404, "card_invalid")
    return FileResponse(booth.asset_path(case["image"], cid, "image"))


@app.get("/api/home")
def home() -> dict:
    return {"cards": [f"/api/cards/{cid}/original" for cid in HOME_CARDS]}


# ---------------------------------------------------------------------------
# Can you beat the AI? (the public visitor flow of pages/1_Challenge_Reveal.py)
# ---------------------------------------------------------------------------
# Phases: "choose" (pick an answer) -> "ai" (prediction + heatmap) -> "truth" (dataset label,
# score) -> next case ... -> "end". Nothing about a case is sent before its phase allows it.
class StartRequest(BaseModel):
    card: str | None = Field(default=None, max_length=8)


class PickRequest(BaseModel):
    answer: str


@app.get("/api/challenge/info")
def challenge_info() -> dict:
    cases()  # report a dataset problem here, before a visitor starts
    return {"round_size": rules.ROUND_SIZE, "n_cards": 30, "scores": booth.booth_set_scores()}


@app.get("/api/challenge/folders")
def challenge_folders() -> list[dict]:
    """The six patient folders from the booth (shown only when the visitor asks)."""
    folders = []
    for number, cid in enumerate(rules.FOLDER_CASES, start=1):
        case = rules.folder_case(cid, cases())
        folders.append({"number": number, "id": cid, "card": int(cid) if cid in cases() else None,
                        "ai_pred": case["ai_pred"], "truth": case["truth"],
                        "percent": rules.explanation_percent(case),
                        "title_key": f"wrong_{cid}_title", "text_key": f"wrong_{cid}_text",
                        "overlay": f"/api/challenge/folders/{cid}/overlay"})
    return folders


@app.get("/api/challenge/folders/{cid}/overlay")
def folder_overlay(cid: str) -> FileResponse:
    if cid not in rules.FOLDER_CASES:
        raise problem(404, "card_invalid")
    return FileResponse(booth.asset_path(rules.folder_case(cid, cases())["mask_overlay"], cid, "mask_overlay"))


def round_view(state: dict | None) -> dict | None:
    if state is None:
        return None
    total, index, phase = len(state["cases"]), state["index"], state["phase"]
    you, ai, played = rules.score(state["cases"], state["answers"])
    view = {"total": total, "index": index, "phase": phase, "answer": state["answer"],
            "score": {"you": you, "ai": ai, "played": played},
            "steps": ["done" if i < index or (i == index and phase == "truth") else
                      "current" if i == index else "todo" for i in range(total)]}
    if phase == "end":
        return view
    case = state["cases"][index]
    cid, token = case["case_id"], f"{index}-{state['started']}"
    view["case"] = {"card": int(cid), "image": f"/api/challenge/image/image?v={token}"}
    if phase in ("ai", "truth"):
        view["case"].update(ai_pred=case["ai_pred"], ai_probs=case["ai_probs"], ai_correct=case["correct"],
                            heatmap=f"/api/challenge/image/heatmap?v={token}")
    if phase == "truth":
        view["case"].update(truth=case["truth"], overlay=f"/api/challenge/image/mask_overlay?v={token}",
                            outcome_key=rules.outcome_key(case, state["answer"]),
                            explanation_key=rules.explanation_key(case),
                            explanation_percent=rules.explanation_percent(case),
                            overlap_key=rules.overlap_label(case))
    return view


def current_round(session: Session) -> dict:
    if session.round is None:
        raise problem(409, "no_round")
    return session.round


@app.get("/api/challenge/round")
def get_round(request: Request, response: Response) -> dict:
    session = visitor(request, response)
    with session.lock:
        return {"round": round_view(session.round)}


@app.post("/api/challenge/start")
def start_round(body: StartRequest, request: Request, response: Response) -> dict:
    """A random round of five cards, or one card typed by the visitor."""
    session = visitor(request, response)
    all_cases = cases()
    if body.card is None:
        chosen = random.sample(sorted(all_cases), rules.ROUND_SIZE)
    else:
        cid = booth.card_case_id(body.card)
        if cid is None or cid not in all_cases:
            raise problem(422, "card_invalid")
        chosen = [cid]
    with session.lock:  # snapshot the cases, so a dataset change cannot alter a running round
        session.round = {"cases": [dict(all_cases[cid]) for cid in chosen], "index": 0, "phase": "choose",
                         "answer": None, "answers": [], "started": random.getrandbits(32)}
        return {"round": round_view(session.round)}


@app.post("/api/challenge/pick")
def pick(body: PickRequest, request: Request, response: Response) -> dict:
    session = visitor(request, response)
    if body.answer not in booth.CLASSES:
        raise problem(422, "invalid_answer")
    with session.lock:
        state = current_round(session)
        if state["phase"] != "choose":
            raise problem(409, "wrong_phase")
        state["answer"] = body.answer
        return {"round": round_view(state)}


@app.post("/api/challenge/reveal-ai")
def reveal_ai(request: Request, response: Response) -> dict:
    session = visitor(request, response)
    with session.lock:
        state = current_round(session)
        if state["phase"] != "choose" or state["answer"] is None:
            raise problem(409, "reveal_locked")
        state["phase"] = "ai"
        return {"round": round_view(state)}


@app.post("/api/challenge/reveal-truth")
def reveal_truth(request: Request, response: Response) -> dict:
    session = visitor(request, response)
    with session.lock:
        state = current_round(session)
        if state["phase"] != "ai":
            raise problem(409, "wrong_phase")
        state["answers"].append(state["answer"])  # scored once, when the truth is revealed
        state["phase"] = "truth"
        return {"round": round_view(state)}


@app.post("/api/challenge/next")
def next_case(request: Request, response: Response) -> dict:
    session = visitor(request, response)
    with session.lock:
        state = current_round(session)
        if state["phase"] != "truth":
            raise problem(409, "wrong_phase")
        state.update(index=state["index"] + 1, answer=None)
        state["phase"] = "end" if state["index"] >= len(state["cases"]) else "choose"
        return {"round": round_view(state)}


@app.post("/api/challenge/end")
def end_round(request: Request, response: Response) -> dict:
    session = visitor(request, response)
    with session.lock:
        session.round = None
    return {"round": None}


@app.get("/api/challenge/image/{kind}")
def round_image(kind: str, request: Request, response: Response, v: str = "") -> FileResponse:
    """The current case's images, each only once its phase is reached."""
    session = visitor(request, response)
    allowed = {"image": ("choose", "ai", "truth"), "heatmap": ("ai", "truth"), "mask_overlay": ("truth",)}
    with session.lock:
        state = session.round
        if kind not in allowed or state is None or state["phase"] not in allowed[kind]:
            raise problem(404, "image_unavailable")
        case = state["cases"][state["index"]]
    image = FileResponse(booth.asset_path(case[kind], case["case_id"], kind))
    image.headers["Cache-Control"] = "private, max-age=600"
    return image


# ---------------------------------------------------------------------------
# Tweak the Tumor (pages/2_Tweak_the_Tumor.py)
# ---------------------------------------------------------------------------
class PredictRequest(BaseModel):
    values: list[float] = Field(min_length=1, max_length=64)
    threshold: float = Field(default=tweak_logic.DEFAULT_THRESHOLD, ge=0, le=1)


@lru_cache(maxsize=2)
def _bundle(_model: float, _meta: float) -> tuple:
    model, features, labels = booth.load_model_bundle()
    return model, features, labels, booth.load_class_medians(features)


def model_files() -> tuple[Path, Path]:
    return ROOT / "models" / "wdbc_model.pkl", ROOT / "models" / "wdbc_features.json"


def bundle() -> tuple:
    pickle_file, metadata = model_files()
    if not pickle_file.is_file() or not metadata.is_file():
        raise problem(503, "coming_soon")
    try:
        return _bundle(_mtime(pickle_file), _mtime(metadata))
    except booth.BoothError:
        raise
    except Exception:
        raise problem(500, "model_invalid") from None


@app.get("/api/tweak/model")
def tweak_model() -> dict:
    pickle_file, metadata = model_files()
    if not pickle_file.is_file() or not metadata.is_file():
        return {"available": False}
    _, features, _, medians = bundle()
    return {"available": True, "default_threshold": tweak_logic.DEFAULT_THRESHOLD,
            "slide": set(slide_image.FEATURES) <= {feature["name"] for feature in features},
            "features": [{"name": feature["name"], "key": tweak_logic.FRIENDLY_FEATURES.get(feature["name"]),
                          "min": feature["min"], "max": feature["max"], "median": feature["median"]}
                         for feature in features[:5]],
            "presets": {label: [medians[label][feature["name"]] for feature in features[:5]]
                        for label in ("benign", "malignant")}}


def model_row(values: list[float], features: list[dict]) -> list[float]:
    """The five slider values, then every other feature at its median (as the page does)."""
    if len(values) != min(5, len(features)):
        raise problem(422, "model_input")
    row = [float(feature["median"]) for feature in features]
    for index, (value, feature) in enumerate(zip(values, features)):
        if not math.isfinite(value) or not feature["min"] <= value <= feature["max"]:
            raise problem(422, "model_input", feature=feature["name"])
        row[index] = value
    return row


@app.post("/api/tweak/predict")
def tweak_predict(body: PredictRequest) -> dict:
    model, features, labels, _ = bundle()
    row = model_row(body.values, features)
    try:
        probability = booth.malignant_probability(model, row, labels)
    except Exception:
        raise problem(500, "model_prediction_error") from None
    prediction, confidence = tweak_logic.decision(probability, body.threshold)
    return {"malignant": probability, "benign": 1 - probability, "threshold": body.threshold,
            "prediction": prediction, "confidence": confidence}


@lru_cache(maxsize=256)
def _slide_jpeg(look: slide_image.Look) -> bytes:
    return slide_image.render_jpeg(look)


@app.get("/api/tweak/slide")
def tweak_slide(values: str = Query(max_length=200)) -> Response:
    """The real microscope image, reshaped to match the current slider values."""
    _, features, _, medians = bundle()
    try:
        numbers = [float(value) for value in values.split(",")]
    except ValueError:
        raise problem(422, "model_input") from None
    row = model_row(numbers, features)
    names = [feature["name"] for feature in features]
    if not set(slide_image.FEATURES) <= set(names):
        raise problem(404, "slide_unavailable")
    look = slide_image.look_for(dict(zip(names, row)), {f["name"]: f for f in features}, medians["benign"])
    return Response(_slide_jpeg(look), media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/tweak/reference/{label}")
def tweak_reference(label: str) -> FileResponse:
    files = {"benign": slide_image.SLIDE / "base.jpg", "malignant": slide_image.SLIDE / "reference_malignant.jpg"}
    if label not in files:
        raise problem(404, "slide_unavailable")
    return FileResponse(files[label])


# ---------------------------------------------------------------------------
# Ask AIDA (pages/3_Ask_AIDA.py)
# ---------------------------------------------------------------------------
class TopicRequest(BaseModel):
    topic: str
    lang: str = "en"


class MessageRequest(BaseModel):
    question: str = Field(max_length=4000)
    lang: str = "en"


def chat_settings() -> tuple[chat.Settings | None, str | None]:
    """The live assistant's settings: AIDA_* environment variables, else .streamlit/secrets.toml.

    Without either, Ask AIDA answers offline from kb/fallback_*.md, exactly like the booth.
    """
    secrets: dict = {}
    try:
        path = ROOT / ".streamlit" / "secrets.toml"
        if path.is_file():
            secrets = {key: value for key, value in tomllib.loads(path.read_text(encoding="utf-8")).items()
                       if key in SECRET_KEYS}
    except Exception as exc:
        return None, chat.exception_category(exc)
    for key in SECRET_KEYS:
        if os.environ.get(f"AIDA_{key}"):
            secrets[key] = os.environ[f"AIDA_{key}"]
    return chat.settings_from(secrets), chat.configuration_reason(secrets)


def chat_view(session: Session, settings: chat.Settings | None) -> dict:
    return {"transcript": session.transcript, "turns_left": chat.turns_left(session.chat_history),
            "max_chars": chat.MAX_MESSAGE_CHARS, "live": settings is not None}


@app.get("/api/chat")
def get_chat(request: Request, response: Response) -> dict:
    session = visitor(request, response)
    with session.lock:
        return chat_view(session, chat_settings()[0])


@app.post("/api/chat/topic")
def chat_topic(body: TopicRequest, request: Request, response: Response) -> dict:
    """A quick topic: the hand-written answer (always offline; not counted as a question)."""
    session = visitor(request, response)
    lang = checked_lang(body.lang)
    if body.topic not in chat.TOPICS:
        raise problem(422, "kb_missing")
    try:
        text = chat.fallback_sections(lang)[body.topic]
    except (OSError, KeyError):
        raise problem(500, "kb_missing") from None
    with session.lock:
        session.transcript.append({"role": "topic", "topic": body.topic, "html": chat.message_html(text)})
        return chat_view(session, chat_settings()[0])


def live_or_offline(history: list[dict], question: str, lang: str, settings: chat.Settings | None,
                    unavailable_reason: str | None) -> tuple[list[dict], str]:
    """The page's answer(): a live reply, or the offline guidance in the question's language.

    Returns the transcript entries to show and the text kept in the model history.
    """
    try:
        if settings is None:
            raise chat.ChatUnavailable(unavailable_reason or "no secrets")
        reply = "".join(chat.call_llm(history, lang, settings))
        if not reply.strip():
            raise chat.ChatUnavailable("ChatUnavailable")
        fixed = chat.fix_numbers(reply)
        return [{"role": "assistant", "html": chat.message_html(fixed)}], fixed
    except Exception as exc:
        reason = str(exc) if isinstance(exc, chat.ChatUnavailable) else chat.exception_category(exc)
        chat.log_fallback(reason)
        question_lang = "ar" if chat.is_mainly_arabic(question) else "en"
        strings = translations(question_lang)
        note = strings["chat_offline"]
        try:
            fallback = chat.fix_numbers(chat.offline_answer(question, strings))
        except (OSError, KeyError):
            # The safety guidance still appears even if a KB file is unavailable.
            guidance = "chat_symptom_guidance" if chat.mentions_symptom(question) else "chat_offline_generic"
            fallback = chat.fix_numbers(strings[guidance])
        return ([{"role": "notice", "html": chat.message_html(note, notice=True)},
                 {"role": "assistant", "html": chat.message_html(fallback)}], f"_{note}_\n\n{fallback}")


@app.post("/api/chat/message")
def chat_message(body: MessageRequest, request: Request, response: Response) -> dict:
    session = visitor(request, response)
    lang = checked_lang(body.lang)
    error = chat.check_message(body.question)
    if error:
        raise problem(422, error, limit=chat.MAX_MESSAGE_CHARS)
    settings, reason = chat_settings()
    with session.lock:
        if chat.turns_left(session.chat_history) == 0:
            raise problem(429, "chat_turn_limit")
        session.chat_history.append({"role": "user", "content": body.question})
        session.transcript.append({"role": "user", "html": chat.message_html(body.question)})
        history = list(session.chat_history)
    entries, kept = live_or_offline(history, body.question, lang, settings, reason)
    with session.lock:
        session.chat_history.append({"role": "assistant", "content": kept})
        session.transcript.extend(entries)
        return chat_view(session, settings)


@app.post("/api/chat/reset")
def chat_reset(request: Request, response: Response) -> dict:
    """New conversation: clears the shown transcript and the question count."""
    session = visitor(request, response)
    with session.lock:
        session.chat_history, session.transcript = [], []
        return chat_view(session, chat_settings()[0])


# ---------------------------------------------------------------------------
# About (pages/4_About.py)
# ---------------------------------------------------------------------------
@app.get("/api/about")
def about() -> dict:
    """All numbers come from data/reports/metrics.json and data/booth_set.json (never typed in)."""
    try:
        metrics = json.loads((ROOT / "data" / "reports" / "metrics.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise problem(500, "about_metrics_missing") from None
    caught, missed = metrics["malignant_caught"], metrics["malignant_missed"]
    return {"n_test": metrics["n_test"], "accuracy": metrics["accuracy"], "caught": caught, "missed": missed,
            "malignant_total": caught + missed, "false_alarms": metrics["false_alarms"],
            "split_sizes": metrics["split_sizes"], "test_counts": metrics.get("test_counts"),
            "confusion_matrix": metrics["confusion_matrix"], "booth_set": booth.booth_set_scores(),
            "images": {name: f"/api/about/image/{name}" for name, path in ABOUT_IMAGES.items() if path.is_file()}}


@app.get("/api/about/image/{name}")
def about_image(name: str) -> FileResponse:
    path = ABOUT_IMAGES.get(name)
    if path is None or not path.is_file():
        raise problem(404, "image_unavailable")
    return FileResponse(path)


# ---------------------------------------------------------------------------
# The built website (frontend/dist), when present: one port for everything.
# ---------------------------------------------------------------------------
if FRONTEND.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def website(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(404)
        candidate = (FRONTEND / path).resolve()
        if path and candidate.is_relative_to(FRONTEND.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND / "index.html")  # client-side routes
