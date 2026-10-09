import streamlit as st

import aida_chat as chat
from booth import language, t, translations


def live_settings() -> chat.Settings | None:
    """API settings from .streamlit/secrets.toml, or None (the page then works offline)."""
    try:
        return chat.settings_from(st.secrets)
    except Exception:
        return None


def answer(history: list[dict], question: str, settings: chat.Settings | None) -> str:
    """Stream a live reply; on no key, error or timeout show the matching hand-written answer."""
    try:
        reply = st.write_stream(chat.call_llm(history, language(), settings))
        if isinstance(reply, str) and reply.strip():
            return reply
        raise chat.ChatUnavailable("empty reply")
    except chat.ChatUnavailable:
        lang = "ar" if chat.is_arabic(question) else language()
        note = translations(lang)["chat_offline"]
        try:
            fallback = chat.fallback_sections(lang)[chat.match_topic(question)]
        except (OSError, KeyError):
            fallback = translations(lang)["kb_missing"]
        st.info(note)
        st.markdown(fallback)
        return f"_{note}_\n\n{fallback}"


st.title(t("ask_title"))
st.write(t("ask_intro"))
st.warning(t("chat_disclaimer"))

# Quick buttons: always work offline, from kb/fallback_<lang>.md.
topics = chat.TOPICS
for column, topic in zip(st.columns(4), topics):
    if column.button(t(topic), key=topic, width="stretch"):
        st.session_state["ask_topic"] = topic

topic = st.session_state.get("ask_topic")
if topic:
    st.subheader(t(topic))
    try:
        st.markdown(chat.fallback_sections(language())[topic])
    except (OSError, KeyError):
        st.error(t("kb_missing"))
else:
    st.info(t("ask_prompt"))

# Free-text chat. History lives only in this browser session (never on disk).
st.subheader(t("chat_heading"))
settings = live_settings()
history = st.session_state.setdefault("chat_history", [])
for message in history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

left = chat.turns_left(history)
if left == 0:
    st.info(t("chat_turn_limit"))
question = st.chat_input(t("chat_placeholder"), key="chat_question", max_chars=chat.MAX_MESSAGE_CHARS,
                         disabled=left == 0)
if question:
    problem = chat.check_message(question)
    if problem:
        st.error(t(problem, limit=chat.MAX_MESSAGE_CHARS))
    elif chat.turns_left(history) == 0:
        st.info(t("chat_turn_limit"))
    else:
        history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            history.append({"role": "assistant", "content": answer(history, question, settings)})
        st.caption(t("chat_turns_left", left=chat.turns_left(history)))

st.caption(t("live_note") if settings else t("offline_note"))
