"""Run with: python -m streamlit run Home.py"""
import streamlit as st

from booth import footer, frame, t

st.set_page_config(page_title=t("brand"), page_icon="🎗️", layout="wide")
frame()


def home() -> None:
    st.markdown(f'<div class="booth-eyebrow">{t("eyebrow")}</div>', unsafe_allow_html=True)
    st.title(t("brand"))
    st.header(t("home_headline"))
    st.write(t("home_intro"))
    st.write("")
    destinations = (("challenge_title", "challenge_description", "pages/1_Challenge_Reveal.py", "01"),
                    ("tweak_title", "tweak_description", "pages/2_Tweak_the_Tumor.py", "02"),
                    ("ask_title", "ask_description", "pages/3_Ask_AIDA.py", "03"))
    for column, (title, description, destination, number) in zip(st.columns(3), destinations):
        with column, st.container(border=True):
            st.caption(number)
            st.subheader(t(title))
            st.write(t(description))
            if st.button(t(title), key=f"home_{number}", type="primary", width="stretch"):
                st.switch_page(destination)
    st.info(t("home_hint"))


page = st.navigation([
    st.Page(home, title=t("home_title"), default=True, url_path="home"),
    st.Page("pages/1_Challenge_Reveal.py", title=t("challenge_title"), url_path="challenge"),
    st.Page("pages/2_Tweak_the_Tumor.py", title=t("tweak_title"), url_path="tweak"),
    st.Page("pages/3_Ask_AIDA.py", title=t("ask_title"), url_path="ask"),
])
try:
    page.run()
finally:
    footer()
