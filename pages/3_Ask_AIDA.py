import re

import streamlit as st

from booth import ROOT, language, t


def call_llm(prompt: str, lang: str) -> str:
    """FUTURE LLM INTEGRATION POINT.

    Replace this stub with your provider call and a reviewed educational system
    prompt. Do not send personal health information. It is intentionally never
    called by the offline quick-button flow.
    """
    raise NotImplementedError("LLM integration is not configured.")


def fallback_sections(lang: str) -> dict[str, str]:
    """Stable Markdown headings are identifiers; headings are not displayed."""
    content = (ROOT / "kb" / f"fallback_{lang}.md").read_text(encoding="utf-8")
    parts = re.split(r"^## ([a-z_]+)\s*$", content, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts), 2)}


st.title(t("ask_title"))
st.write(t("ask_intro"))
topics = ("know_signs", "myth_fact", "explain_term", "get_help")
for column, topic in zip(st.columns(4), topics):
    if column.button(t(topic), key=topic, width="stretch"):
        st.session_state["ask_topic"] = topic

topic = st.session_state.get("ask_topic")
if topic:
    st.subheader(t(topic))
    try:
        st.markdown(fallback_sections(language())[topic])
    except (OSError, KeyError):
        st.error(t("kb_missing"))
else:
    st.info(t("ask_prompt"))
st.caption(t("offline_note"))
