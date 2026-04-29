from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.ui import build_page_context, render_comparability_note

# =========================================================
# Load context and dataframe (MUST COME FIRST)
# =========================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"]

# =========================================================
# Page header
# =========================================================
st.markdown("## Plant Scale and Crop Context")

st.markdown(
    """
This section summarizes crop presence, average recorded plant counts across systems,
and tower planting activity for the Towers system only.
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
# Prepare data safely
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
k1, k2, k3 = st.columns(3)

# KPI 1: Average recorded plants (all systems)
k1.metric(
    "Avg Recorded Plants (All Systems)",
    f"{df['plant_count_clean'].mean():,.1f}",
)

# KPI 2: Average towers planted (Towers only)
if mask_towers.any():
    k2.metric(
        "Avg Towers Planted (Towers System)",
        f"{df.loc[mask_towers, 'plant_count_clean'].mean():,.1f}",
    )
else:
    k2.metric(
        "Avg Towers Planted (Towers System)",
        "N/A",
    )

# KPI 3: Capacity reference
k3.metric(
    "Towers Capacity (Reference)",
    "24 towers",
)

# =========================================================
# Crop types across systems
# =========================================================
st.markdown("### Crop Types Across Systems")

if "crop_tokens" in df.columns and df["crop_tokens"].notna().any():
    crop_df = (
        df.explode("crop_tokens")
        .loc[lambda x: x["crop_tokens"].notna() & (x["crop_tokens"] != "")]
    )

    crop_counts = (
        crop_df.groupby(["system", "crop_tokens"])
        .size()
        .reset_index(name="count")
    )

    fig_crop = px.bar(
        crop_counts,
        x="system",
        y="count",
        color="crop_tokens",
        title="Observed Crop Tokens by System",
        labels={
            "count": "Observations",
            "crop_tokens": "Crop Type",
            "system": "System",
        },
    )

    st.plotly_chart(fig_crop, use_container_width=True)
else:
    st.info("No crop data available under the selected filters.")

# =========================================================
# Average recorded plant count per system
# =========================================================
st.markdown("### Average Recorded Plant Count per System")

avg_plants_system = (
    df.groupby("system", as_index=False)["plant_count_clean"]
    .mean()
)

fig_avg = px.bar(
    avg_plants_system,
    x="system",
    y="plant_count_clean",
    title="Average Recorded Plant Count by System",
    labels={
        "plant_count_clean": "Avg Recorded Plants",
        "system": "System",
    },
)

st.plotly_chart(fig_avg, use_container_width=True)

# =========================================================
# Towers planted over time (TOWERS ONLY)
# =========================================================
st.markdown("### Towers Planted Over Time (Towers System Only)")

if mask_towers.any():
    towers_trend = (
        df.loc[mask_towers]
        .groupby("observation_date", as_index=False)["plant_count_clean"]
        .mean()
    )

    if not towers_trend.empty:
        fig_towers = px.line(
            towers_trend,
            x="observation_date",
            y="plant_count_clean",
            markers=True,
            title="Towers Planted Over Time",
            labels={
                "plant_count_clean": "Towers Planted",
                "observation_date": "Date",
            },
        )

