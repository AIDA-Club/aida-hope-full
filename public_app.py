"""Public entry point: Ask AIDA and About only.

Run with: python -m streamlit run public_app.py

This is the file to deploy publicly (e.g. Streamlit Community Cloud). It never
loads the booth challenge, the Tweak the Tumor model, data/booth_set.json,
the answer key or data/results.csv. Only the two page files below are served,
and scripts/export_public.py copies exactly the files they need.
"""
import streamlit as st

from booth import footer, frame, t

st.set_page_config(page_title=t("brand"), page_icon="🎗️", layout="wide")
frame()


def home() -> None:
    st.markdown(f'<div class="booth-eyebrow">{t("eyebrow")}</div>', unsafe_allow_html=True)
    st.title(t("brand"))
    st.header(t("home_headline"))
    st.write(t("public_home_intro"))
    with st.container(border=True):
        st.subheader(t("ask_title"))
        st.write(t("ask_description"))
        if st.button(t("ask_title"), key="home_ask", type="primary", width="stretch"):
            st.switch_page("pages/3_Ask_AIDA.py")


page = st.navigation([
    st.Page(home, title=t("home_title"), default=True, url_path="home"),
    st.Page("pages/3_Ask_AIDA.py", title=t("ask_title"), url_path="ask"),
    st.Page("pages/4_About.py", title=t("about_title"), url_path="about"),
])
try:
    page.run()
finally:
    footer()
