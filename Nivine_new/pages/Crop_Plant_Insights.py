from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.ui import build_page_context, render_comparability_note

# =========================================================
# Load context and dataframe
# =========================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"]

# =========================================================
# Page header
# =========================================================
st.markdown("## Plant Scale and Crop Context")

st.markdown(
    """
This section summarizes crop presence, growth stages, average recorded plant counts
across systems, and tower planting activity for the Towers system only.
"""
)

if df.empty:
    st.warning("No data available after the current filters.")
    st.stop()

render_comparability_note(context.get("comparability_note"))

# =========================================================
# Ensure required columns exist
# =========================================================
required_cols = {"system", "plant_count", "observation_date"}
missing = required_cols - set(df.columns)

if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

# =========================================================
# Prepare data
# =========================================================
df = df.copy()

df["plant_count_clean"] = (
    pd.to_numeric(df["plant_count"], errors="coerce")
    .fillna(0)
)

# Identify Towers system robustly
mask_towers = (
    df["system"]
    .astype(str)
    .str.lower()
    .str.contains("tower", na=False)
)

# =========================================================
# KPI Row
# =========================================================
