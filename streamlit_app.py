# streamlit_app.py

from __future__ import annotations

import streamlit as st

from interface.main_app import run as run_calculator_ui
from coverage_calculator.utils.query_state import share_and_load_ui

APP_NAME = "Sequencing Calculator"
APP_VERSION = "1.1.0"
APP_AUTHOR = "Erick Samera"
APP_COMMENT = (
    "For calculating samples per flowcell, necessary depth, or supported genome size"
)

st.set_page_config(
    page_title=f"ES | {APP_NAME}",
    page_icon=":material/calculate:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

pages = [
    st.Page(
        run_calculator_ui, title="Calculator", icon=":material/calculate:", default=True
    ),
]
selected_page = st.navigation(pages)


selected_page.run()

with st.sidebar:
    st.title(APP_NAME)
    st.caption(f"@{APP_AUTHOR} | v{APP_VERSION}")
    st.caption(APP_COMMENT)
    st.markdown("---")
    share_and_load_ui()
