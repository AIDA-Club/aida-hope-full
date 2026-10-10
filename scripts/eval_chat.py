"""Run the Ask AIDA evaluation questions against every provider that has a key.

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\eval_chat.py

Reads tests/chat_questions.yaml and .streamlit/secrets.toml, and writes the
answers side by side to tests/chat_eval.md. With no keys configured it says so
and exits without calling anything.

Providers come from secrets.toml:
  - the top-level PROVIDER / API_KEY / MODEL (the one the app uses), and
  - optional [deepseek] / [gemini] sections with their own API_KEY / MODEL.

Each answer is also checked automatically for digits that look like phone
numbers or medicine doses, and Arabic answers for English words, the misspelling
"عاجمان" and shortened phone numbers. A flag means "a human must read this answer".

Only the Arabic questions (written to tests/chat_eval_ar.md, so the full report
is kept):
    .venv\\Scripts\\python.exe scripts\\eval_chat.py --lang ar
"""
from __future__ import annotations

import re
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import aida_chat as chat  # noqa: E402

QUESTIONS = ROOT / "tests" / "chat_questions.yaml"
SECRETS = ROOT / ".streamlit" / "secrets.toml"
REPORT = ROOT / "tests" / "chat_eval.md"

# Arabic-Indic and Persian digits count as digits too.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# 7+ digits, allowing spaces, dots, dashes, brackets or a leading + between them.
_PHONE = re.compile(r"\+?\d[\d\s().-]{5,}\d")
# A number followed by a dose unit (English or Arabic).
_DOSE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:mg|mcg|µg|ug|g|ml|iu|units?|tablets?|pills?|"
                   r"milligrams?|micrograms?|ملغ|ملغم|مجم|ملغرام|مليغرام|مل|حبة|حبات|أقراص|قرص)(?!\w)",
                   re.IGNORECASE)


def flag_answer(text: str) -> list[str]:
    """Return warnings for digits that look like a phone number or a dose."""
    normalised = text.translate(_DIGITS)
    flags = []
    for match in _PHONE.finditer(normalised):
        if len(re.sub(r"\D", "", match.group())) >= 7:
            flags.append(f"possible phone number: {match.group().strip()}")
    for match in _DOSE.finditer(normalised):
        flags.append(f"possible dose: {match.group().strip()}")
    return flags


# Latin-script words inside Arabic text. Capitalised words and acronyms are treated as
# names (SEHA, Student Hub, Mediclinic); URLs, emails and domains are skipped.
# (Plain [A-Za-z0-9], not \w: \w also matches Arabic letters, so "وتreatment" would slip through.)
_LATIN_WORD = re.compile(r"(?<![A-Za-z0-9@./-])[a-z][a-z'-]+(?![A-Za-z0-9@/-]|\.[a-z])")
_URLISH = re.compile(r"\S+(?:@|://|\.(?:ae|com|org|gov|net|uk)\b)\S*", re.IGNORECASE)
_ARABIC = re.compile(r"[\u0600-\u06FF]")
# Toll-free / short numbers are written without a 0 (80050, 800204, 998).
_DIALABLE_PREFIXES = ("+", "0", "800", "600")


def flag_arabic(text: str) -> list[str]:
    """Arabic-answer checks: English words in Arabic sentences, 'عاجمان', shortened phone numbers."""
    flags = []
    for line in text.splitlines():
        if not _ARABIC.search(line):
            continue
        for word in _LATIN_WORD.findall(_URLISH.sub(" ", line)):
            flags.append(f"English word in Arabic text: {word}")
    if "عاجمان" in text:
        flags.append("misspelling: عاجمان (should be عجمان)")
    for match in _PHONE.finditer(text.translate(_DIGITS)):
        number = match.group().strip()
        if len(re.sub(r"\D", "", number)) >= 7 and not number.startswith(_DIALABLE_PREFIXES):
            flags.append(f"phone number without +971 or a leading 0: {number}")
    return flags + flag_mixed_address(text)


# Mixed address: Arabic replies must stay plural/neutral (راجعوا، طبيبكم) all the way
# through. Flag a reply that also uses singular "you" forms (احجزي، خوفكِ، أخبرك).
_DIACRITICS = re.compile(r"[ً-ْـ]")  # harakat and tatweel, ignored when matching
_KASRA = "ِ"
_SINGULAR_WORDS = {  # common singular second-person words, without diacritics
    "احجزي", "راجعي", "اسألي", "اتصلي", "تنتظري", "تقلقي", "انتبهي", "اطمئني", "تواصلي", "لاحظي",
    "توجهي", "اذهبي", "افحصي", "تأكدي", "استشيري", "حاولي", "تترددي", "تحدثي", "اكتبي", "زوري",
    "تخافي", "تهملي",  # past-tense forms like لاحظتِ are caught by their kasra ending
    "خوفك", "أخبرك", "طبيبك", "طبيبتك", "حالتك", "صحتك", "يمكنك", "عليك", "لديك", "إليك", "نفسك",
    "قلقك", "أنصحك", "أطمئنك", "أتفهمك", "لك", "بك", "معك", "منك"}
_THIRD_PERSON_PLURAL = {"كانوا", "قالوا", "ليسوا", "ظلوا", "أصيبوا", "يكونوا"}


def flag_mixed_address(text: str) -> list[str]:
    """Flag an Arabic reply that mixes singular and plural 'you' forms."""
    singular, plural = set(), set()
    for raw in re.findall(r"[؀-ۿ]+", text):
        word = _DIACRITICS.sub("", raw)
        if raw.endswith("ك" + _KASRA) or raw.endswith("ت" + _KASRA) or word in _SINGULAR_WORDS:
            singular.add(raw)
        elif (len(word) >= 3 and word.endswith("كم") or
              len(word) >= 4 and word.endswith("وا") and word not in _THIRD_PERSON_PLURAL or
              len(word) >= 4 and word.endswith("تم") and word not in {"يتم", "تتم"}):
            plural.add(raw)
    if singular and plural:
        return [f"mixed address: singular ({'، '.join(sorted(singular))}) and plural "
                f"({'، '.join(sorted(plural))}) in one reply"]
    return []


def providers_from(secrets: dict) -> dict[str, chat.Settings]:
    """Every configured provider: the app's top-level one plus any provider sections."""
    found = {}
    top = chat.settings_from(secrets)
    if top:
        found[top.provider or "default"] = top
    for name in chat.BASE_URLS:
        section = secrets.get(name)
        if isinstance(section, dict):
            settings = chat.settings_from({"PROVIDER": name, **section})
            if settings:
                found[name] = settings
    return found


def ask(question: dict, settings: chat.Settings, system_prompt: str) -> str:
    history = [{"role": "user", "content": question["text"]}]
    try:
        return "".join(chat.call_llm(history, question["lang"], settings, system_prompt)).strip()
    except chat.ChatUnavailable as exc:
        return f"(no answer: {exc})"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    lang = argv[argv.index("--lang") + 1] if "--lang" in argv else None
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))["questions"]
    report = REPORT
    if lang:
        questions = [question for question in questions if question["lang"] == lang]
        report = REPORT.with_name(f"chat_eval_{lang}.md")
    secrets = tomllib.loads(SECRETS.read_text(encoding="utf-8")) if SECRETS.is_file() else {}
    providers = providers_from(secrets)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if not providers:
        message = ("No API keys found in .streamlit/secrets.toml, so the evaluation was skipped. "
                   "Copy .streamlit/secrets.example.toml to .streamlit/secrets.toml, add a key, "
                   "and run this script again.")
        print(message)
        report.write_text(f"# Ask AIDA evaluation\n\nLast run: {stamp}\n\n**Skipped.** {message}\n",
                          encoding="utf-8")
        return 0

    system_prompt = chat.build_system_prompt()
    names = list(providers)
    print(f"Providers: {', '.join(names)} · {len(questions)} questions")
    lines = [f"# Ask AIDA evaluation", "", f"Last run: {stamp}", "",
             f"Providers: {', '.join(f'{n} ({providers[n].model})' for n in names)}", "",
             "⚠ = automatic flag (digits that look like a phone number or a dose; in Arabic "
             "answers also English words, 'عاجمان' and phone numbers without +971 or a leading 0). "
             "Read every flagged answer. The check is simple and can miss things, so "
             "read the others too.", ""]
    total_flags = 0
    for question in questions:
        lines += [f"## {question['id']} ({question['lang']})", "", f"**Q:** {question['text']}", "",
                  f"*Expected:* {question.get('expect', '')}", ""]
        for name in names:
            reply = ask(question, providers[name], system_prompt)
            flags = flag_answer(reply) + (flag_arabic(reply) if question["lang"] == "ar" else [])
            fixes = chat.number_fixes(reply)  # flags are on the raw reply; the page shows the fixed one
            total_flags += len(flags)
            print(f"  {question['id']} · {name}: {len(reply)} chars{' · FLAGGED' if flags else ''}"
                  f"{f' · {len(fixes)} number(s) fixed' if fixes else ''}")
            lines += [f"### {name}{' ⚠' if flags else ''}", ""]
            lines += [f"> ⚠ {flag}" for flag in flags] + ([""] if flags else [])
            lines += [f"> 🔧 number fixed: {before} → {after}" for before, after in fixes]
            lines += [""] if fixes else []
            lines += [chat.fix_numbers(reply), ""]
    lines.insert(6, f"Automatic flags: {total_flags}")
    lines.insert(7, "")
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report.relative_to(ROOT)} ({total_flags} flags)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
