"""Can you beat the AI?: the rules shared by the Streamlit page and the web API.

No Streamlit here. Functions return translation keys; callers translate them, so the
page (pages/1_Challenge_Reveal.py) and api/ always pick exactly the same line.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROUND_SIZE = 5
# The six patient folders (print_content.yaml), in folder order: four real AI errors, one
# right-for-the-wrong-reason case and one it got right. Folders 1-5 are booth cards; folder 6
# is not, so its data lives in data/folders/folder6.json. Texts: the wrong_<id>_* keys.
FOLDER_CASES = ("17", "25", "26", "28", "04", "folder6")


def overlap_label(case: dict) -> str | None:
    overlap = case["cam_mask_overlap"]
    if case["truth"] == "normal" or overlap is None:
        return None
    return "overlap_yes" if overlap >= 0.3 else "overlap_partly" if overlap >= 0.1 else "overlap_no"


def heatmap_target(case: dict) -> str:
    """For an AI mistake: "_off_target" (overlap under 0.1), "_on_target" (0.5 or more), else ""."""
    overlap = case["cam_mask_overlap"]
    if case["truth"] == "normal" or overlap is None:
        return ""
    return "_off_target" if overlap < 0.1 else "_on_target" if overlap >= 0.5 else ""


def explanation_key(case: dict) -> str:
    """The translation key of the one line on what this case shows about the AI.

    Format it with pred, truth (translated class names) and percent (the AI's confidence
    in its own prediction, 0-100): see explanation_values().
    """
    if case["error_type"] == "false_negative":
        return "explain_missed" + heatmap_target(case)
    if case["error_type"] == "false_positive":
        return "explain_false_alarm" + heatmap_target(case)
    if not case["correct"]:
        return "explain_saw_lump" if case["truth"] == "normal" else "explain_mixed"
    if case["truth"] == "normal":
        return "explain_right_normal"
    # "Right answer, wrong reason" only from a measured overlap under 0.1 (never for normal tissue).
    return {"overlap_yes": "explain_right_on_target", "overlap_partly": "explain_right_partly",
            "overlap_no": "explain_right_wrong_place", None: "explain_right"}[overlap_label(case)]


def explanation_percent(case: dict) -> float:
    return case["ai_probs"][case["ai_pred"]] * 100


def outcome_key(case: dict, answer: str) -> str:
    """Who got it right: the visitor's (final) answer and the AI, both against the dataset label."""
    visitor_right, ai_right = answer == case["truth"], case["correct"]
    return ("both_right" if visitor_right and ai_right else "visitor_right" if visitor_right
            else "ai_right" if ai_right else "both_wrong")


def score(cases: list[dict], answers: list[str]) -> tuple[int, int, int]:
    """(visitor right, AI right, cases played); a case counts once its truth has been revealed."""
    played = cases[:len(answers)]
    you = sum(answer == case["truth"] for answer, case in zip(answers, played))
    return you, sum(case["correct"] for case in played), len(played)


def folder_case(cid: str, cases: dict) -> dict:
    if cid in cases:
        return cases[cid]
    return json.loads((ROOT / "data" / "folders" / f"{cid}.json").read_text(encoding="utf-8"))
