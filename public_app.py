"""Public entry point: Can you beat the AI?, Tweak the Tumor, Ask AIDA and About.

Run with: python -m streamlit run public_app.py

This is the file to deploy publicly (e.g. Streamlit Community Cloud). It runs the booth's
pages in public mode (booth.public_mode()): the Challenge has no staff controls, no answer
key and no "next visitor" flow, and nothing is ever written to disk (no results log, no
uploads). scripts/export_public.py copies exactly the files these pages need.
"""
import streamlit as st

from booth import footer, frame, t

st.set_page_config(page_title=t("brand"), page_icon="🎗️", layout="wide")
st.session_state["public_mode"] = True  # set on every run, before any page code
frame()

CHALLENGE, TWEAK, ASK = "pages/1_Challenge_Reveal.py", "pages/2_Tweak_the_Tumor.py", "pages/3_Ask_AIDA.py"


def home() -> None:
    st.markdown(f'<div class="booth-eyebrow">{t("eyebrow")}</div>', unsafe_allow_html=True)
    st.title(t("brand"))
    st.header(t("home_headline"))
    st.write(t("public_home_intro"))
    destinations = (("public_challenge_title", "public_challenge_description", CHALLENGE, "challenge"),
                    ("tweak_title", "tweak_description", TWEAK, "tweak"),
                    ("ask_title", "ask_description", ASK, "ask"))
    for title, description, destination, key in destinations:
        with st.container(border=True):
            st.subheader(t(title))
            st.write(t(description))
            if st.button(t(title), key=f"home_{key}", type="primary", width="stretch"):
                st.switch_page(destination)


page = st.navigation([
    st.Page(home, title=t("home_title"), default=True, url_path="home"),
    st.Page(CHALLENGE, title=t("public_challenge_title"), url_path="challenge"),
    st.Page(TWEAK, title=t("tweak_title"), url_path="tweak"),
    st.Page(ASK, title=t("ask_title"), url_path="ask"),
    st.Page("pages/4_About.py", title=t("about_title"), url_path="about"),
])
try:
    page.run()
finally:
    footer()
