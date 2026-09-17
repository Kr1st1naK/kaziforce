"""
Streamlit demonstration interface.

Run with: streamlit run src/app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(page_title="KaziForce", layout="wide")
st.title("KaziForce — Explainable Worker–Job Matching")
st.caption(
    "Knowledge graph-enhanced recommender for informal gig worker–job matching in Kenya"
)

st.info("Interface under construction — see Sprint 5 (Explainability Module & Interface).")

# TODO(Sprint 5):
#   - Worker profile / job posting input forms
#   - Ranked match results table
#   - Explanation panel (graph paths + score breakdown)
