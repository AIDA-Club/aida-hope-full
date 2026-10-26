r"""Check the Dockerfile's COPY sources without Docker.

For every COPY in the Dockerfile (except multi-stage --from copies) this verifies that the
source exists, is tracked by git (Render builds from the repository, not this folder), and is
not excluded by .dockerignore. With --assemble DIR it also copies the runtime stage's files into
DIR exactly as the image would lay them out under /app, for a local smoke test.

    .venv\Scripts\python.exe scripts\check_docker_context.py [--assemble DIR]
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ignore_rules() -> list[tuple[bool, str]]:
    rules = []
    for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        negate = line.startswith("!")
        rules.append((negate, line.lstrip("!").rstrip("/")))
    return rules


def _matches(pattern: str, path: str) -> bool:
    """Docker-style match: root-anchored, `**` spans directories, a match also covers children."""
    regex = re.escape(pattern).replace(r"\*\*/", "(?:.*/)?").replace(r"\*\*", ".*")
    regex = regex.replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
    return re.fullmatch(regex + "(?:/.*)?", path) is not None


def ignored(path: str, rules: list[tuple[bool, str]]) -> bool:
    result = False
    for negate, pattern in rules:
        if _matches(pattern, path):
            result = not negate
    return result


def copy_instructions() -> list[tuple[list[str], str, str | None, int]]:
    """(sources, destination, --from stage or None, stage number) for each COPY."""
    copies, text = [], (ROOT / "Dockerfile").read_text(encoding="utf-8")
    stages = 0
    for line in text.replace("\\\n", " ").splitlines():
        line = line.strip()
        if line.upper().startswith("FROM "):
            stages += 1
        if not line.upper().startswith("COPY "):
            continue
        parts = shlex.split(line[5:])
        stage = next((p.split("=", 1)[1] for p in parts if p.startswith("--from=")), None)
        parts = [p for p in parts if not p.startswith("--")]
        copies.append((parts[:-1], parts[-1], stage, stages))
    return copies


def tracked(path: str) -> bool:
    out = subprocess.run(["git", "ls-files", "--", path], cwd=ROOT, capture_output=True, text=True)
    return bool(out.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assemble", type=Path)
    args = parser.parse_args()
    rules, problems = ignore_rules(), []
    copies = copy_instructions()
    last_stage = max(stage for *_, stage in copies)
    for sources, dest, from_stage, stage in copies:
        if from_stage:
            continue
        for source in sources:
            path = ROOT / source
            label = source.rstrip("/")
            if not path.exists():
                problems.append(f"missing: {source}")
            elif ignored(label, rules):
                problems.append(f"excluded by .dockerignore: {source}")
            elif not tracked(label):
                problems.append(f"not tracked by git (Render would not see it): {source}")
            if path.is_dir():
                for child in path.rglob("*"):
                    rel = child.relative_to(ROOT).as_posix()
                    if child.is_file() and not ignored(rel, rules) and not tracked(rel) and "node_modules" not in rel \
                            and "/dist/" not in rel and "__pycache__" not in rel:
                        problems.append(f"untracked file inside a COPY'd folder: {rel}")
            if args.assemble and stage == last_stage:
                target = args.assemble / dest.lstrip("./").replace("/app/", "")
                if path.is_dir():
                    shutil.copytree(path, target if dest.endswith("/") else target, dirs_exist_ok=True,
                                    ignore=lambda d, names: [n for n in names
                                                             if ignored((Path(d) / n).relative_to(ROOT).as_posix(), rules)])
                else:
                    (target if dest.endswith("/") else target.parent).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target / path.name if dest.endswith("/") else target)
    for secret in (".streamlit/secrets.toml", ".streamlit", ".venv", "frontend/node_modules", ".git"):
        if not ignored(secret, rules):
            problems.append(f".dockerignore does not exclude {secret}")
    for line in problems:
        print("PROBLEM", line)
    count = sum(len(s) for s, _, f, _ in copies if not f)
    print(f"{count} COPY sources checked, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
