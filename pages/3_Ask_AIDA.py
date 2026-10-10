import streamlit as st

import aida_chat as chat
from booth import language, t, translations


def live_settings() -> tuple[chat.Settings | None, str | None]:
    """API settings from .streamlit/secrets.toml, or None (the page then works offline)."""
    try:
        settings = chat.settings_from(st.secrets)
        return settings, chat.configuration_reason(st.secrets) if settings is None else None
    except Exception as exc:
        return None, chat.exception_category(exc)


def answer(history: list[dict], question: str, settings: chat.Settings | None,
           unavailable_reason: str | None) -> str:
    """Stream a live reply; on failure show safe guidance in the question's language.

    After streaming, the bubble is redrawn with chat.fix_numbers() applied (reversed
    phone numbers repaired, numbers kept left-to-right in Arabic), and that fixed text
    is what goes into the session history.
    """
    bubble = st.empty()
    try:
        if settings is None:
            raise chat.ChatUnavailable(unavailable_reason or "no secrets")
        reply = ""
        for piece in chat.call_llm(history, language(), settings):
            reply += piece
            bubble.html(chat.message_html(reply))
        if not reply.strip():
            raise chat.ChatUnavailable("ChatUnavailable")
        fixed = chat.fix_numbers(reply)
        bubble.html(chat.message_html(fixed))
        return fixed
    except Exception as exc:
        reason = str(exc) if isinstance(exc, chat.ChatUnavailable) else chat.exception_category(exc)
        chat.log_fallback(reason)
        bubble.empty()  # discard a partial live answer before presenting offline guidance
        lang = "ar" if chat.is_mainly_arabic(question) else "en"
        note = translations(lang)["chat_offline"]
        try:
            fallback = chat.fix_numbers(chat.offline_answer(question, translations(lang)))
        except (OSError, KeyError):
            # The safety guidance still appears even if a KB file is unavailable.
            guidance = "chat_symptom_guidance" if chat.mentions_symptom(question) else "chat_offline_generic"
            fallback = chat.fix_numbers(translations(lang)[guidance])
        st.html(chat.message_html(note, notice=True))
        st.html(chat.message_html(fallback))
        return f"_{note}_\n\n{fallback}"


st.title(t("ask_title"))
st.write(t("ask_intro"))
st.warning(t("chat_disclaimer"))
st.html("""<style>
.aida-message {overflow-wrap:anywhere;font-size:1.25rem;line-height:1.65;}
.aida-message[dir="rtl"] :is(p,ul,ol,li,blockquote,h1,h2,h3,h4) {direction:rtl;text-align:right;}
.aida-message[dir="ltr"] :is(p,ul,ol,li,blockquote,h1,h2,h3,h4) {direction:ltr;text-align:left;}
.aida-message :is(ul,ol) {padding-inline-start:1.5em;padding-inline-end:0;list-style-position:outside;}
.aida-offline-notice {background:#e8f4fd;border-radius:0.5rem;padding:0.8rem 1rem;margin-bottom:1rem;}
.aida-offline-notice p:last-child {margin-bottom:0;}
</style>""")

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
settings, unavailable_reason = live_settings()
history = st.session_state.setdefault("chat_history", [])
for message in history:
    with st.chat_message(message["role"]):
        st.html(chat.message_html(message["content"]))

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
            st.html(chat.message_html(question))
        with st.chat_message("assistant"):
            history.append({"role": "assistant", "content": answer(history, question, settings, unavailable_reason)})
        st.caption(t("chat_turns_left", left=chat.turns_left(history)))

st.caption(t("live_note") if settings else t("offline_note"))
