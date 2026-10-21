"""Challenge the AI. At the booth: staff load a visitor's card and the round is logged anonymously.

On the public website (booth.public_mode()): visitors play a 5-case round or type their card
number. No staff controls, no answer key, no logging, nothing written to disk.
"""
import html
import random

import streamlit as st

from booth import (BoothError, CLASSES, PUBLIC_ASSET_FIELDS, asset_path, booth_set_note, card_case_id,
                   choose_answer, keep_answer, load_cases, next_visitor, public_mode, save_round, set_phase,
                   start_round, t, zoomable_image)
from challenge_logic import (FOLDER_CASES, ROUND_SIZE, explanation_key, explanation_percent, folder_case,
                             outcome_key, overlap_label)
from challenge_logic import score as score_answers


def what_we_learned(stacked: bool = False) -> None:
    """Closing panel after the truth is revealed: what AI and doctors are each good at."""
    with st.container(border=True, key="what_we_learned"):
        st.subheader(t("learn_heading"))
        ai_side, doctor_side = (st.container(), st.container()) if stacked else st.columns(2, gap="large")
        with ai_side:
            st.markdown(f"**{t('learn_ai_title')}**")
            st.markdown(t("learn_ai_points"))
        with doctor_side:
            st.markdown(f"**{t('learn_doctor_title')}**")
            st.markdown(t("learn_doctor_points"))
        st.markdown('<div class="booth-learn">' + html.escape(t("learn_line")) + '</div>',
                    unsafe_allow_html=True)


def ai_prediction(case: dict) -> None:
    """The AI's answer, an error note if it was wrong, and its confidence per class."""
    st.markdown('<div class="booth-prediction">' + html.escape(
        t("ai_prediction", prediction=t(case["ai_pred"]))) + '</div>', unsafe_allow_html=True)
    if not case["correct"]:
        st.markdown('<div class="booth-error-note">' + html.escape(t("ai_error_note"))
                    + '</div>', unsafe_allow_html=True)
    st.caption(t("confidence_note"))


def confidence_bars(case: dict) -> None:
    for label in CLASSES:
        st.progress(float(case["ai_probs"][label]),
                    text=t("confidence", label=t(label), percent=case["ai_probs"][label] * 100))


def result_box(case: dict, answer: str) -> None:
    message = outcome_key(case, answer)
    st.markdown('<div class="booth-result" role="status"><div class="booth-result-truth">'
                + html.escape(t("truth_heading", truth=t(case["truth"]))) + '</div>' + html.escape(t(message))
                + '</div>', unsafe_allow_html=True)


def heatmap_disclaimer() -> None:
    """The line under every heatmap (the truth overlay is drawn on the heatmap too)."""
    st.caption(t("heatmap_disclaimer"))


def honesty_note() -> None:
    note = booth_set_note()
    if note:
        st.caption(note)


def explanation(case: dict) -> str:
    """One line on what this case shows about the AI (rules in challenge_logic.py)."""
    return t(explanation_key(case), pred=t(case["ai_pred"]), truth=t(case["truth"]),
             percent=explanation_percent(case))


# ---------------------------------------------------------------------------
# Booth (staff-run, logged)
# ---------------------------------------------------------------------------
def booth_challenge(cases: dict) -> None:
    from booth_keyboard import shortcuts  # staff keyboard shortcuts: booth only

    active = st.session_state.get("round")
    with st.form("choose_case"):
        entry, load = st.columns([1, 2], vertical_alignment="bottom")
        with entry:
            number = st.text_input(t("case_number"), key="case_number", max_chars=2,
                                   placeholder=t("case_placeholder"), help=t("case_help"),
                                   disabled=active is not None)
        with load:
            submitted = st.form_submit_button(t("show_image"), type="primary", width="stretch",
                                              disabled=active is not None)
    if submitted and active is None:
        cid = number.strip().zfill(2)
        if cid not in cases:
            st.error(t("case_invalid"))
        else:
            start_round(cases[cid])
            st.rerun()
    st.caption(t("keyboard_hint"))
    shortcuts()
    if active is None:
        st.info(t("challenge_intro"))
        return

    case, phase = active["case"], active["phase"]
    steps = ("step_first", "step_ai", "step_final", "step_truth")
    index = {"first": 0, "ai": 1, "decide": 2, "change": 2, "truth": 3, "done": 3}[phase]
    st.write(t("case_stage", case_id=case["case_id"], label=t(steps[index])))
    ai_visible = phase in ("decide", "change", "truth", "done")

    if ai_visible:
        prediction, confidence = st.columns([1, 1.2], gap="large")
        with prediction:
            ai_prediction(case)
        with confidence:
            confidence_bars(case)

    views = [("image", "original_image")]
    if ai_visible:
        views.append(("heatmap", "heatmap_image"))
    if phase == "done":
        views.append(("mask_overlay", "truth_overlay"))

    if ai_visible:
        for column, (field, caption) in zip(st.columns(len(views), gap="large"), views):
            with column:
                st.image(str(asset_path(case[field], case["case_id"], field)), caption=t(caption),
                         width=320 if phase == "done" else 420)
        heatmap_disclaimer()
    else:
        picture, choice = st.columns([1, 1.2], gap="large")
        with picture:
            st.image(str(asset_path(case["image"], case["case_id"], "image")),
                     caption=t("original_image"), width="stretch")
        with choice:
            if phase == "first":
                st.subheader(t("first_question"))
                for column, answer in zip(st.columns(3), CLASSES):
                    column.button(t(answer), key=f"first_{answer}", width="stretch",
                                  on_click=choose_answer, args=(answer,))
            else:
                st.info(t("first_choice", answer=t(active["first_answer"])))
                st.write(t("ready_ai"))
                st.button(t("reveal_ai"), key="reveal_ai", type="primary", width="stretch",
                          on_click=set_phase, args=("decide",))

    if ai_visible and phase != "done":
        st.caption(t("first_choice", answer=t(active["first_answer"])))
    if phase == "decide":
        st.subheader(t("final_question"))
        keep, change = st.columns(2)
        keep.button(t("keep_answer"), key="keep_answer", width="stretch", on_click=keep_answer)
        change.button(t("change_answer"), key="change_answer", width="stretch",
                      on_click=set_phase, args=("change",))
    elif phase == "change":
        st.subheader(t("change_question"))
        for column, answer in zip(st.columns(3), CLASSES):
            column.button(t(answer), key=f"final_{answer}", width="stretch",
                          on_click=choose_answer, args=(answer, True))
    elif phase == "truth":
        st.info(t("final_choice", answer=t(active["final_answer"])))
        st.button(t("reveal_truth"), key="reveal_truth", type="primary", width="stretch",
                  on_click=set_phase, args=("done",))
    elif phase == "done":
        result_box(case, active["final_answer"])
        overlap = overlap_label(case)
        if overlap:
            st.write(t("overlap_question", answer=t(overlap)))
        st.caption(t("answer_summary", first=t(active["first_answer"]), final=t(active["final_answer"])))
        what_we_learned()
        try:
            save_round(active)
            st.caption(t("round_saved"))
        except (OSError, BoothError):
            st.error(t("log_error"))
            st.button(t("retry_save"), key="retry_save", width="stretch")

    st.button(t("next_visitor"), key="next_visitor", type="primary", width="stretch",
              on_click=next_visitor, disabled=phase == "done" and not active["logged"])


# ---------------------------------------------------------------------------
# Public website (visitor-run, nothing saved). State lives only in the browser session.
# ---------------------------------------------------------------------------
def start_public_round(case_ids: list[str], cases: dict) -> None:
    st.session_state["public_round"] = {"cases": [cases[cid] for cid in case_ids], "index": 0,
                                        "phase": "choose", "answer": None, "answers": []}


def start_random_round(cases: dict) -> None:
    start_public_round(random.sample(sorted(cases), ROUND_SIZE), cases)


def pick(answer: str) -> None:
    st.session_state["public_round"]["answer"] = answer


def public_step(phase: str) -> None:
    state = st.session_state["public_round"]
    if phase == "truth" and state["phase"] == "ai":
        state["answers"].append(state["answer"])  # scored once, when the truth is revealed
    state["phase"] = phase


def next_public_case() -> None:
    state = st.session_state["public_round"]
    state.update(index=state["index"] + 1, phase="choose", answer=None)


def end_public_round() -> None:
    st.session_state.pop("public_round", None)


def score(state: dict) -> tuple[int, int, int]:
    return score_answers(state["cases"], state["answers"])


def public_start(cases: dict) -> None:
    st.write(t("public_challenge_intro"))
    honesty_note()
    with st.container(border=True):
        st.subheader(t("play_round_title"))
        st.write(t("play_round_text", n=ROUND_SIZE))
        st.button(t("play_round"), key="play_round", type="primary", width="stretch",
                  on_click=start_random_round, args=(cases,))
    with st.container(border=True):
        st.subheader(t("card_title"))
        st.write(t("card_text"))
        with st.form("card_form", border=False):
            number = st.text_input(t("card_number"), key="card_number", max_chars=3,
                                   placeholder=t("card_placeholder"))
            submitted = st.form_submit_button(t("play_card"), type="primary", width="stretch")
        if submitted:
            cid = card_case_id(number)
            if cid is None or cid not in cases:
                st.error(t("card_invalid"))
            else:
                start_public_round([cid], cases)
                st.rerun()
    wrong_cases(cases)


def wrong_cases(cases: dict) -> None:
    """The booth's six patient folders (mostly the AI's real mistakes), shown only when asked for."""
    st.subheader(t("wrong_title"))
    st.write(t("wrong_intro"))
    if not st.toggle(t("wrong_show"), key="show_wrong"):
        return
    for number, cid in enumerate(FOLDER_CASES, start=1):
        case = folder_case(cid, cases)
        label = f"{t('folder_label', n=number)} · {t(f'wrong_{cid}_title')}"
        if cid in cases:
            label += f" · {t('card_label', card=int(cid))}"
        with st.container(border=True):
            st.markdown(f"**{html.escape(label, quote=False)}**")
            st.write(t("wrong_summary", pred=t(case["ai_pred"]), truth=t(case["truth"]),
                       percent=case["ai_probs"][case["ai_pred"]] * 100))
            zoomable_image(asset_path(case["mask_overlay"], cid, "mask_overlay"), t("truth_overlay"),
                           key=f"wrong{cid}")
            heatmap_disclaimer()
            st.write(t(f"wrong_{cid}_text"))


def public_case(state: dict) -> None:
    case, phase = state["cases"][state["index"]], state["phase"]
    cid, total = case["case_id"], len(state["cases"])
    st.caption(t("round_progress", current=state["index"] + 1, total=total, card=int(cid)))
    if phase == "choose":
        zoomable_image(asset_path(case["image"], cid, "image"), t("original_image"), key=f"image{cid}")
        st.subheader(t("pick_prompt"))
        for answer in CLASSES:
            chosen = state["answer"] == answer
            st.button(("✓ " if chosen else "") + t(answer), key=f"pick_{answer}", width="stretch",
                      on_click=pick, args=(answer,))
        if state["answer"] is None:
            st.caption(t("reveal_locked"))
        st.button(t("reveal_ai"), key="public_reveal_ai", type="primary", width="stretch",
                  disabled=state["answer"] is None, on_click=public_step, args=("ai",))
        return
    st.info(t("your_answer", answer=t(state["answer"])))
    ai_prediction(case)
    confidence_bars(case)
    if phase == "ai":
        zoomable_image(asset_path(case["heatmap"], cid, "heatmap"), t("heatmap_image"), key=f"heat{cid}")
        heatmap_disclaimer()
        st.button(t("reveal_truth"), key="public_reveal_truth", type="primary", width="stretch",
                  on_click=public_step, args=("truth",))
        return
    result_box(case, state["answer"])
    st.markdown(f"**{html.escape(explanation(case), quote=False)}**")
    zoomable_image(asset_path(case["mask_overlay"], cid, "mask_overlay"), t("truth_overlay"), key=f"truth{cid}")
    heatmap_disclaimer()
    you, ai, played = score(state)
    st.markdown('<div class="booth-score" role="status">'
                + html.escape(t("score_line", you=you, ai=ai, total=played)) + '</div>', unsafe_allow_html=True)
    last = state["index"] + 1 >= total
    st.button(t("see_score" if last else "next_case"), key="public_next", type="primary", width="stretch",
              on_click=next_public_case)


def public_end(state: dict) -> None:
    you, ai, played = score(state)
    st.subheader(t("end_title"))
    st.markdown('<div class="booth-score" role="status">'
                + html.escape(t("score_line", you=you, ai=ai, total=played)) + '</div>', unsafe_allow_html=True)
    honesty_note()
    st.markdown('<div class="booth-station">' + html.escape(t("station_message"), quote=False) + '</div>',
                unsafe_allow_html=True)
    what_we_learned(stacked=True)
    st.button(t("play_again"), key="play_again", type="primary", width="stretch", on_click=end_public_round)


def public_challenge(cases: dict) -> None:
    st.session_state["footer_credits"] = "case_credits"
    state = st.session_state.get("public_round")
    if state is None:
        public_start(cases)
    elif state["index"] >= len(state["cases"]):
        public_end(state)
    else:
        public_case(state)


def challenge() -> None:
    public = public_mode()
    st.title(t("public_challenge_title" if public else "challenge_title"))
    try:
        cases = load_cases(PUBLIC_ASSET_FIELDS) if public else load_cases()
    except BoothError as exc:
        st.error(exc.ui_message())
        return
    if public:
        public_challenge(cases)
    else:
        booth_challenge(cases)


challenge()
