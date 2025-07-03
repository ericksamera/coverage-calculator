# streamlit_app.py

import streamlit as st
from interface.main_app import run as run_calculator_ui

APP_NAME = "Coverage Calculator"
APP_VERSION = "0.1.0"
APP_AUTHOR = "Erick Samera"
APP_COMMENT = "Streamlined sequencing coverage calculator"

# Define pages using st.Page
pages = [
    st.Page(run_calculator_ui, title="Calculator",, default=True),
    # Add more pages here as needed
]

# Set up navigation
selected_page = st.navigation(pages)

# Optional: Set consistent page config across all pages
st.set_page_config(page_title=APP_NAME, page_icon="", layout="wide")

# Sidebar branding
with st.sidebar:
    st.title(f"{APP_NAME}")
    st.caption(f"@{APP_AUTHOR} | v{APP_VERSION}")
    st.caption(APP_COMMENT)
    st.markdown("---")

# Run the selected page
selected_page.run()
