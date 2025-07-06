# streamlit_app.py

import streamlit as st
from interface.main_app import run as run_calculator_ui

APP_NAME = "Sequencing Calculator"
APP_VERSION = "1.0.1"
APP_AUTHOR = "Erick Samera"
APP_COMMENT = "For calculating samples per flowcell, necessary depth, or supported genome size"

pages = [
    st.Page(run_calculator_ui, title="Calculator", default=True),
]

selected_page = st.navigation(pages)

st.set_page_config(page_title=f"ES | {APP_NAME}", page_icon=":material/calculate:", layout="wide")

with st.sidebar:
    st.title(f"{APP_NAME}")
    st.caption(f"@{APP_AUTHOR} | v{APP_VERSION}")
    st.caption(APP_COMMENT)
    st.markdown("---")

selected_page.run()