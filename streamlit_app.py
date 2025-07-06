# streamlit_app.py

import streamlit as st
from interface.main_app import run as run_calculator_ui

APP_NAME = "Coverage Calculator"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Erick Samera"
APP_COMMENT = "Sequencing coverage calculator"

pages = [
    st.Page(run_calculator_ui, title="Calculator", default=True),
]

selected_page = st.navigation(pages)

st.set_page_config(page_title=APP_NAME, page_icon="", layout="wide")

with st.sidebar:
    st.title(f"{APP_NAME}")
    st.caption(f"@{APP_AUTHOR} | v{APP_VERSION}")
    st.caption(APP_COMMENT)
    st.markdown("---")

selected_page.run()