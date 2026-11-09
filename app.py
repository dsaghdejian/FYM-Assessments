import streamlit as st
import streamlit.components.v1 as components
from pathlib import Path

st.set_page_config(
    page_title="FYM Hospitality Group - Candidate Assessment",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

html_path = Path(__file__).parent / "assessment.html"
html_code = html_path.read_text(encoding="utf-8")

components.html(
    html_code,
    height=1800,
    scrolling=True,
)
