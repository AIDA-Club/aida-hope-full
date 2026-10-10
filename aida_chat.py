"""Ask AIDA chat logic, kept free of Streamlit so it can be unit-tested.

The page (pages/3_Ask_AIDA.py) and scripts/eval_chat.py both use this module.
Privacy: nothing here writes chat contents to disk or to any log.
"""
from __future__ import annotations

import re
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KB = ROOT / "kb"

# Limits required for the booth.
MAX_OUTPUT_TOKENS = 400
MAX_MESSAGE_CHARS = 500
MAX_TURNS = 12          # visitor messages per browser session
TIMEOUT_SECONDS = 20

# OpenAI-compatible endpoints. Gemini's comes from Google's OpenAI-compatibility
# docs (https://ai.google.dev/gemini-api/docs/openai, checked 9 Oct 2026).
BASE_URLS = {"deepseek": "https://api.deepseek.com",
             "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/"}
TOPICS = ("know_signs", "myth_fact", "explain_term", "get_help")


@dataclass(frozen=True)
class Settings:
    provider: str
    api_key: str
    model: str
    base_url: str


class ChatUnavailable(RuntimeError):
    """The live assistant cannot answer: no key, an API error or a timeout."""


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
def settings_from(secrets: Mapping | None) -> Settings | None:
    """Read PROVIDER / API_KEY / MODEL (and optional BASE_URL). None when not configured."""
    try:
        provider = str(secrets.get("PROVIDER", "")).strip().lower()
        api_key = str(secrets.get("API_KEY", "")).strip()
        model = str(secrets.get("MODEL", "")).strip()
        base_url = str(secrets.get("BASE_URL", "") or BASE_URLS.get(provider, "")).strip()
    except Exception:  # missing secrets.toml, wrong type, etc.
        return None
    if not api_key or not model or not base_url or api_key.startswith("PASTE"):
        return None
    return Settings(provider, api_key, model, base_url)


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
# The system prompt is the whole KB, so keep an eye on its size. This is a check
# (tests fail above it), not a cut: no topic file is ever truncated.
MAX_SYSTEM_PROMPT_CHARS = 120_000  # about 30,000 tokens at ~4 characters per token

# Fallback headings are written for people; the code matches them to the four buttons.
FALLBACK_HEADINGS = {"Know the Signs": "know_signs", "Myth or Fact": "myth_fact",
                     "Explain a Term": "explain_term", "Where to Get Help": "get_help"}


def strip_unconfirmed(text: str) -> str:
    """Remove help_uae.md's "Not yet confirmed" part so the model never sees it.

    Cuts from the '---' line just before '## Not yet confirmed' up to (not including)
    '## Sources', or to the end if there is no Sources heading. The file on disk is
    unchanged: the booth team still needs that list.
    """
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("## Not yet confirmed")), None)
    if start is None:
        return text
    rule = next((i for i in range(start - 1, -1, -1) if lines[i].strip() == "---"), None)
    if rule is not None and all(not line.strip() for line in lines[rule + 1:start]):
        start = rule
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## Sources")), len(lines))
    return "\n".join(lines[:start] + lines[end:])


def strip_section(text: str, heading: str) -> str:
    """Remove one '## heading' section, up to the next '## ' heading or the end."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == heading), None)
    if start is None:
        return text
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[:start] + lines[end:])


def confirmed_help(text: str) -> str:
    """help_uae.md as the chatbot and the public repo see it: CONFIRMED parts only.

    Its Sources list goes too, because it links the news articles behind the
    unconfirmed items. Other KB files keep their Sources.
    """
    return strip_section(strip_unconfirmed(text), "## Sources").rstrip() + "\n"


def build_system_prompt(kb_dir: Path = KB) -> str:
    """system_prompt.md followed by every other kb/*.md except the fallback files."""
    system = (kb_dir / "system_prompt.md").read_text(encoding="utf-8").strip()
    parts = [system, "", "REFERENCE MATERIAL"]
    for path in sorted(kb_dir.glob("*.md")):
        if path.name == "system_prompt.md" or path.name.startswith("fallback_"):
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "help_uae.md":
            text = confirmed_help(text)
        parts += ["", f"--- {path.name} ---", text.strip()]
    return "\n".join(parts)


def fallback_sections(lang: str, kb_dir: Path = KB) -> dict[str, str]:
    """Hand-written answers, keyed by topic. '## Know the Signs' etc. map to the buttons."""
    content = (kb_dir / f"fallback_{lang}.md").read_text(encoding="utf-8")
    parts = re.split(r"^## (.+?)\s*$", content, flags=re.MULTILINE)
    sections = {}
    for i in range(1, len(parts), 2):
        topic = FALLBACK_HEADINGS.get(parts[i])
        if topic:
            sections[topic] = parts[i + 1].strip()
    return sections


# ---------------------------------------------------------------------------
# Phone numbers: repaired in code, not by the prompt
# ---------------------------------------------------------------------------
# In Arabic replies the model sometimes writes a number with its groups in the
# wrong order ("6294 705 6 971+"). fix_numbers() puts any CONFIRMED number back
# exactly as the KB writes it. Numbers that are not confirmed are left alone.
EMERGENCY_NUMBERS = ("998", "999", "997")
LTR_ISOLATE, POP_ISOLATE = "⁦", "⁩"  # keep a number left-to-right inside Arabic
# A run of digits, allowing +, spaces and hyphens inside, and a stray + at either end.
_NUMBER_RUN = re.compile(r"\+?\d(?:[\d \-]*\d)?\+?")
_ARABIC_LETTER = re.compile(r"[؀-ۿ]")


def _digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def confirmed_numbers(kb_dir: Path = KB) -> dict[str, str]:
    """Every phone number in help_uae.md's CONFIRMED part, keyed by its digits.

    The value is the number exactly as the KB writes it. A run counts as a phone
    number when it has 5+ digits (80050, 8002033, +971 6 506 5542...); 4-digit
    years and the PO Box are skipped. The emergency numbers are added too.
    """
    text = confirmed_help((kb_dir / "help_uae.md").read_text(encoding="utf-8"))
    numbers = {}
    for match in _NUMBER_RUN.finditer(text):
        canonical = match.group().strip(" -").rstrip("+")
        if len(_digits(canonical)) < 5 or text[max(0, match.start() - 4):match.start()] == "Box ":
            continue
        numbers.setdefault(_digits(canonical), canonical)
    for number in EMERGENCY_NUMBERS:
        numbers.setdefault(number, number)
    return numbers


def _match_confirmed(run: str, numbers: dict[str, str]) -> str | None:
    """The canonical number this run is (as written, reversed or with '971+' moved to the end)."""
    groups = [_digits(group) for group in re.split(r"[ \-]+", run.strip(" -")) if _digits(group)]
    digits = "".join(groups)
    candidates = [digits, "".join(reversed(groups)), digits[::-1]]
    if run.rstrip().endswith("971+") and digits.endswith("971"):
        candidates.append("971" + digits[:-3])
    for candidate in candidates:
        if candidate in numbers:
            return numbers[candidate]
    return None


def _fix_numbers(text: str, numbers: dict[str, str]) -> tuple[str, list[tuple[str, str]]]:
    arabic = bool(_ARABIC_LETTER.search(text))
    text = text.replace(LTR_ISOLATE, "").replace(POP_ISOLATE, "")  # so running it twice is safe
    fixes = []

    def replace(match: re.Match) -> str:
        run = match.group()
        core = run.strip(" -")
        canonical = _match_confirmed(core, numbers)
        if canonical is None:
            return run  # not a confirmed number: leave it exactly as it is
        if core != canonical:
            fixes.append((core, canonical))
        shown = f"{LTR_ISOLATE}{canonical}{POP_ISOLATE}" if arabic else canonical
        return run.replace(core, shown, 1)

    return _NUMBER_RUN.sub(replace, text), fixes


def fix_numbers(text: str, kb_dir: Path = KB) -> str:
    """Repair confirmed phone numbers; in Arabic text, also wrap them in LTR isolates."""
    return _fix_numbers(text, confirmed_numbers(kb_dir))[0]


def number_fixes(text: str, kb_dir: Path = KB) -> list[tuple[str, str]]:
    """(before, after) for every number fix_numbers() would change. Used by the eval report."""
    return _fix_numbers(text, confirmed_numbers(kb_dir))[1]


# Very small keyword router: which hand-written answer fits a typed question best.
_TOPIC_WORDS = {
    "know_signs": ("sign", "symptom", "lump", "pain", "nipple", "discharge", "change", "skin",
                   "علام", "عرض", "أعراض", "كتلة", "ألم", "حلمة", "إفراز", "تغير", "تغيّر"),
    "myth_fact": ("myth", "true", "fact", "bra", "cause", "men", "man", "male", "deodorant",
                  "خرافة", "حقيقة", "صحيح", "يسبب", "تسبب", "الرجال", "رجل"),
    "explain_term": ("what is", "what does", "mean", "benign", "malignant", "biopsy", "term",
                     "mammogram", "ultrasound", "metastasis", "bi-rads", "birads",
                     "ما معنى", "ما هو", "ما هي", "حميد", "خبيث", "خزعة", "ماموغرام", "مصطلح"),
    "get_help": ("help", "doctor", "clinic", "number", "contact", "call", "where", "scared",
                 "afraid", "worried", "مساعدة", "طبيب", "عيادة", "رقم", "اتصال", "أين", "خائف", "قلق"),
}


def match_topic(text: str) -> str:
    """The fallback topic with the most keyword hits; 'get_help' when nothing matches."""
    lowered = text.lower()
    scores = {topic: sum(word in lowered for word in words) for topic, words in _TOPIC_WORDS.items()}
    best = max(TOPICS, key=lambda topic: scores[topic])
    return best if scores[best] else "get_help"


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------
def is_arabic(text: str) -> bool:
    return bool(re.search(r"[؀-ۿ]", text))


def check_message(text: str) -> str | None:
    """Return an i18n error key when a message breaks a limit, else None."""
    if not text.strip():
        return "chat_empty"
    if len(text) > MAX_MESSAGE_CHARS:
        return "chat_too_long"
    return None


def turns_used(history: list[dict]) -> int:
    return sum(1 for message in history if message["role"] == "user")


def turns_left(history: list[dict]) -> int:
    return max(0, MAX_TURNS - turns_used(history))


# ---------------------------------------------------------------------------
# The live call
# ---------------------------------------------------------------------------
def build_messages(history: list[dict], ui_lang: str, system_prompt: str) -> list[dict]:
    """System prompt + language hint + the conversation so far (last message is the user's)."""
    language = "Arabic" if ui_lang == "ar" else "English"
    hint = (f"\n\nThe visitor's screen is in {language}. Reply in the language of the visitor's "
            f"latest message; if it is unclear, reply in {language}.")
    return [{"role": "system", "content": system_prompt + hint}] + [
        {"role": message["role"], "content": message["content"]} for message in history]


def call_llm(history: list[dict], ui_lang: str, settings: Settings | None,
             system_prompt: str | None = None, client=None) -> Iterator[str]:
    """Stream the assistant's reply, chunk by chunk.

    Raises ChatUnavailable when there is no key, the API fails, or the whole
    reply takes longer than TIMEOUT_SECONDS. The caller then shows a fallback.
    """
    if settings is None:
        raise ChatUnavailable("not configured")
    if client is None:
        from openai import OpenAI  # imported lazily so the page works without the package
        client = OpenAI(api_key=settings.api_key, base_url=settings.base_url,
                        timeout=TIMEOUT_SECONDS, max_retries=0)
    messages = build_messages(history, ui_lang, system_prompt or build_system_prompt())
    deadline = time.monotonic() + TIMEOUT_SECONDS
    try:
        stream = client.chat.completions.create(model=settings.model, messages=messages,
                                                max_tokens=MAX_OUTPUT_TOKENS, temperature=0.3,
                                                stream=True)
        for chunk in stream:
            if time.monotonic() > deadline:
                raise ChatUnavailable("timeout")
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except ChatUnavailable:
        raise
    except Exception as exc:  # any SDK, network or provider error; never log the content
        raise ChatUnavailable(type(exc).__name__) from None
