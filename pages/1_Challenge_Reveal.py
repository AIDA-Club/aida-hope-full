import html

import streamlit as st

from booth import (BoothError, CLASSES, asset_path, choose_answer, keep_answer,
                   load_cases, next_visitor, save_round, set_phase, start_round, t)
from booth_keyboard import shortcuts


def what_we_learned() -> None:
    """Closing panel after the truth is revealed: what AI and doctors are each good at."""
    with st.container(border=True, key="what_we_learned"):
        st.subheader(t("learn_heading"))
        ai_side, doctor_side = st.columns(2, gap="large")
        with ai_side:
            st.markdown(f"**{t('learn_ai_title')}**")
            st.markdown(t("learn_ai_points"))
        with doctor_side:
            st.markdown(f"**{t('learn_doctor_title')}**")
            st.markdown(t("learn_doctor_points"))
        st.markdown('<div class="booth-learn">' + html.escape(t("learn_line")) + '</div>',
                    unsafe_allow_html=True)


def challenge() -> None:
    st.title(t("challenge_title"))
    try:
        cases = load_cases()
    except BoothError as exc:
        st.error(exc.ui_message())
        return
    
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
            st.markdown('<div class="booth-prediction">' + html.escape(
                t("ai_prediction", prediction=t(case["ai_pred"]))) + '</div>', unsafe_allow_html=True)
            if not case["correct"]:
                st.markdown('<div class="booth-error-note">' + html.escape(t("ai_error_note"))
                            + '</div>', unsafe_allow_html=True)
            st.caption(t("confidence_note"))
        with confidence:
            for label in CLASSES:
                st.progress(float(case["ai_probs"][label]),
                            text=t("confidence", label=t(label), percent=case["ai_probs"][label] * 100))
    
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
        visitor_right, ai_right = active["final_answer"] == case["truth"], case["correct"]
        message = ("both_right" if visitor_right and ai_right else "visitor_right" if visitor_right
                   else "ai_right" if ai_right else "both_wrong")
        st.markdown('<div class="booth-result" role="status"><div class="booth-result-truth">'
                    + html.escape(t("truth_heading", truth=t(case["truth"]))) + '</div>' + html.escape(t(message))
                    + '</div>', unsafe_allow_html=True)
        overlap = case["cam_mask_overlap"]
        if case["truth"] != "normal" and overlap is not None:
            answer = "overlap_yes" if overlap >= 0.3 else "overlap_partly" if overlap >= 0.1 else "overlap_no"
            st.write(t("overlap_question", answer=t(answer)))
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


challenge()
