"""Copy exactly the files public_app.py needs into public_deploy/ (a folder you can push to a public repo).

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\export_public.py

The list below is an allowlist: nothing else is copied. The script then scans the
result and stops if a booth-only file, a secret or a results file slipped in.
kb/help_uae.md is written with its "Not yet confirmed" part and its Sources list
removed (aida_chat.confirmed_help), the same text the chatbot sees.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public_deploy"
sys.path.insert(0, str(ROOT))
from aida_chat import confirmed_help  # noqa: E402

# source (relative to the project) -> destination (relative to public_deploy/)
FILES = {
    "public_app.py": "public_app.py",
    "booth.py": "booth.py",              # shared helpers (language, theme, footer)
    "aida_chat.py": "aida_chat.py",
    "pages/3_Ask_AIDA.py": "pages/3_Ask_AIDA.py",
    "pages/4_About.py": "pages/4_About.py",
    "i18n/en.json": "i18n/en.json",
    "i18n/ar.json": "i18n/ar.json",
    "data/reports/metrics.json": "data/reports/metrics.json",
    "data/reports/confusion_matrix.png": "data/reports/confusion_matrix.png",
    ".streamlit/config.toml": ".streamlit/config.toml",
    ".streamlit/secrets.example.toml": ".streamlit/secrets.example.toml",
    "requirements-public.txt": "requirements.txt",
}
KB = sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "kb").glob("*.md"))
# Files rewritten on the way out instead of copied as they are.
TRANSFORMS = {"kb/help_uae.md": confirmed_help}
FORBIDDEN = ("booth_set", "results.csv", "booth_key", "secrets.toml", "predictions.csv",
             "Challenge", "Tweak", "models/", "gradcam", "print_out", "answer", "docs/")
# Anything that looks like a real API key (DeepSeek/OpenAI "sk-...", Google "AIza...").
KEY_PATTERN = re.compile(r"sk-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{30,}")


def export(dest: Path = DEST) -> list[str]:
    """Build dest/ from the allowlist and return the copied paths. Exits on any problem."""
    if dest.exists():
        shutil.rmtree(dest)
    plan = dict(FILES) | {name: name for name in KB}
    for source, target in plan.items():
        source_path = ROOT / source
        if not source_path.is_file():
            sys.exit(f"Missing file: {source}")
        (dest / target).parent.mkdir(parents=True, exist_ok=True)
        if source in TRANSFORMS:
            text = TRANSFORMS[source](source_path.read_text(encoding="utf-8"))
            (dest / target).write_text(text, encoding="utf-8")
        else:
            shutil.copy2(source_path, dest / target)
    copied = sorted(path.relative_to(dest).as_posix() for path in dest.rglob("*") if path.is_file())
    bad = [name for name in copied if any(word in name for word in FORBIDDEN)
           and name != ".streamlit/secrets.example.toml"]
    if bad:
        sys.exit(f"Refusing: forbidden files in the public folder: {bad}")
    leaked = [name for name in copied if (dest / name).suffix in (".py", ".md", ".toml", ".txt", ".json")
              and KEY_PATTERN.search((dest / name).read_text(encoding="utf-8", errors="ignore"))]
    if leaked:
        shutil.rmtree(dest)
        sys.exit(f"Refusing: something that looks like an API key is in {leaked}. Remove it and rotate the key.")
    return copied


def main() -> None:
    copied = export()
    print(f"{len(copied)} files in {DEST.relative_to(ROOT)}/:")
    for name in copied:
        print("  " + name)


if __name__ == "__main__":
    main()
