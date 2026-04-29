"""Crop and plant insights page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.charts import crop_heatmap, histogram_chart
from utils.metrics import format_num, format_pct
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

# ==================================================
# CONSTANTS (FROM BC / DOCUMENTATION)
# ==================================================
PLANTS_PER_TOWER = 42
MAX_TOWERS = 24

# ==================================================
# LOAD CONTEXT
# ==================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"].copy()

render_hero(
    "Crop / Plant Insights",
    (
        "This page analyzes planting scale in the Towers system. "
        "The dataset records the NUMBER OF TOWERS planted (not individual plants). "
        f"Each tower contains {PLANTS_PER_TOWER} plants."
    ),
)

if df.empty:
    st.warning("No data available after the current filters.")
    st.stop()

render_comparability_note(context["comparability_note"])

# ==================================================
# ✅ INTERPRET COLUMN BF CORRECTLY (TOWERS ONLY)
# ==================================================
df["towers_planted"] = 0.0

mask_towers = df["system"].astype(str).str.lower() == "towers"

df.loc[mask_towers, "towers_planted"] = (
    pd.to_numeric(df.loc[mask_towers, "plant_count"], errors="coerce")
    .fillna(0)
)

# Optional derived metric (clearly labeled)
df["plants_estimated"] = df["towers_planted"] * PLANTS_PER_TOWER

# ==================================================
# KPI CARDS (TOWERS CONTEXT)
# ==================================================
cards = [
    (
        "Avg towers planted (Towers)",
        format_num(df.loc[mask_towers, "towers_planted"].mean()),
        "Average number of towers planted per observation.",
    ),
    (
        "Avg estimated plants",
        format_num(df.loc[mask_towers, "plants_estimated"].mean()),
        "Estimated plants (towers × 42).",
    ),
    (
        "Max tower capacity",
        f"{MAX_TOWERS} towers",
        "Used as a reference limit only.",
    ),
    (
        "Known growth-stage share",
        format_pct(df["growth_stage_known_flag"].mean()),
        "Rows with usable growth-stage metadata.",
    ),
]

cols = st.columns(4, gap="medium")
for col, card in zip(cols, cards):
    with col:
        render_metric_card(*card)

# ==================================================
# ✅ TOWERS PLANTED OVER TIME (CORRECT & NON-ZERO)
# ==================================================
st.markdown("### Towers planted over time")

trend_df = (
    df.loc[mask_towers]
    .groupby("observation_date", as_index=False)["towers_planted"]
    .mean()
)

if trend_df.empty:
    st.info("No tower data available for the selected filters.")
else:
    fig = px.line(
        trend_df,
        x="observation_date",
        y="towers_planted",
        markers=True,
        title="Towers planted over time",
        labels={
            "towers_planted": "Towers planted",
            "observation_date": "Date",
        },
    )

    fig.add_hline(
        y=MAX_TOWERS,
        line_dash="dash",
        annotation_text="Max capacity (24 towers)",
        annotation_position="top left",
    )

    st.plotly_chart(fig, use_container_width=True)

    render_chart_conclusion(
        "Tower rollout over time.",
        "Values reflect the number of towers planted. "
        "This analysis applies only to the Towers system.",
    )

# ==================================================
# OPTIONAL: ESTIMATED PLANTS OVER TIME
# ==================================================
st.markdown("### Estimated plants over time (Towers only)")

plant_trend_df = (
    df.loc[mask_towers]
    .groupby("observation_date", as_index=False)["plants_estimated"]
    .mean()
)

if not plant_trend_df.empty:
    fig = px.line(
        plant_trend_df,
        x="observation_date",
        y="plants_estimated",
        markers=True,
        title="Estimated plants over time (42 plants per tower)",
    )

    st.plotly_chart(fig, use_container_width=True)

    render_chart_conclusion(
        "Estimated plant scale.",
        "Plant totals are derived deterministically as towers planted × 42.",
    )

# ==================================================
# OTHER CONTEXTUAL CHARTS (ALL SYSTEMS)
# ==================================================
st.markdown("### Growth stage distribution")

stage_df = (
    df[df["growth_stage_known_flag"]]
    .groupby(["system", "growth_stage"], as_index=False)
    .size()
    .rename(columns={"size": "count"})
)

if stage_df.empty:
    st.info("Growth-stage data is too sparse.")
else:
    fig = px.bar(
        stage_df,
        x="system",
        y="count",
        color="growth_stage",
        title="Growth-stage distribution by system",
    )

    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Age distribution")

age_df = df[df["age_days"].notna()]
if age_df.empty:
    st.info("Age data is not available.")
else:
    st.plotly_chart(
        histogram_chart(
            age_df,
            x="age_days",
            color="system",
            title="Age distribution by system",
            bins=20,
        ),
        use_container_width=True,
    )

# ==================================================
# METHODOLOGY NOTE (IMPORTANT FOR BC)
# ==================================================
with st.expander("Methodology note"):
    st.markdown(
        """
        - Column BF records the **number of towers planted**.
        - This interpretation applies **only** to the **Towers** system.
        - Other systems (e.g., Conventional) are **not** treated as towers.
        - Estimated plant counts are derived as **towers × 42 plants per tower**.
        - The value **24 towers** represents maximum capacity and is used only for reference.
        """
    )
