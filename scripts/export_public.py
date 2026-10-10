"""Copy exactly the files public_app.py needs into public_deploy/ (a folder you can push to a public repo).

Run from the project folder (Windows):
    .venv\\Scripts\\python.exe scripts\\export_public.py

The list below is an allowlist: nothing else is copied. The script then scans the
result and stops if a booth-only file, a secret or a results file slipped in.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "public_deploy"

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
FORBIDDEN = ("booth_set", "results.csv", "booth_key", "secrets.toml", "predictions.csv",
             "Challenge", "Tweak", "models/", "gradcam", "print_out", "answer")


def main() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    plan = dict(FILES) | {name: name for name in KB}
    for source, target in plan.items():
        source_path = ROOT / source
        if not source_path.is_file():
            sys.exit(f"Missing file: {source}")
        (DEST / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, DEST / target)
    copied = sorted(path.relative_to(DEST).as_posix() for path in DEST.rglob("*") if path.is_file())
    bad = [name for name in copied if any(word in name for word in FORBIDDEN)
           and name != ".streamlit/secrets.example.toml"]
    if bad:
        sys.exit(f"Refusing: forbidden files in the public folder: {bad}")
    print(f"{len(copied)} files in {DEST.relative_to(ROOT)}/:")
    for name in copied:
        print("  " + name)


if __name__ == "__main__":
    main()
