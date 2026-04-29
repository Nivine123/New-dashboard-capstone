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
# CONSTANTS (KNOWN FROM BC / DOCUMENTATION)
# ==================================================
PLANTS_PER_TOWER = 42
MAX_TOWERS = 24
MAX_PLANTS = MAX_TOWERS * PLANTS_PER_TOWER

# ==================================================
# LOAD CONTEXT
# ==================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"].copy()

render_hero(
    "Crop / Plant Insights",
    (
        "This page analyzes planting scale using tower counts. "
        "The dataset records the number of towers planted (not individual plants). "
        f"Each tower contains {PLANTS_PER_TOWER} plants."
    ),
)

if df.empty:
    st.warning("No data available after the current filters.")
    st.stop()

render_comparability_note(context["comparability_note"])

# ==================================================
# CLEAN AND DERIVE VARIABLES
# ==================================================
df["towers_planted"] = (
    pd.to_numeric(df["plant_count"], errors="coerce")
    .fillna(0)
    .clip(lower=0)
)

df["plants_estimated"] = df["towers_planted"] * PLANTS_PER_TOWER

# ==================================================
# KPI CARDS
# ==================================================
cards = [
    (
        "Avg towers planted",
        format_num(df["towers_planted"].mean()),
        "Average number of towers planted per observation.",
    ),
    (
        "Avg estimated plants",
        format_num(df["plants_estimated"].mean()),
        "Estimated plants (42 plants per tower).",
    ),
    (
        "Max capacity",
        f"{MAX_TOWERS} towers",
        f"Equivalent to {MAX_PLANTS} plants.",
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
# TOWERS PLANTED BY SYSTEM
# ==================================================
st.markdown("### Towers planted by system")

system_df = (
    df.groupby("system", as_index=False)["towers_planted"]
    .mean()
)

fig = px.bar(
    system_df,
    x="system",
    y="towers_planted",
    title="Average number of towers planted by system",
    color="system",
)

fig.update_layout(template="plotly_white", showlegend=False)
st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Tower utilization by system.",
    "Values represent the number of planted towers, not individual plants.",
)

# ==================================================
# PLANTING BEHAVIOR OVER TIME (CORRECT & STABLE)
# ==================================================
st.markdown("### Planting behavior over time")

trend_df = (
    df.groupby(["system", "observation_date"], as_index=False)["towers_planted"]
    .mean()
)

fig = px.line(
    trend_df,
    x="observation_date",
    y="towers_planted",
    color="system",
    markers=True,
    title="Towers planted over time",
    labels={
        "towers_planted": "Towers planted",
        "observation_date": "Date",
    },
)

st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Towers planted over time.",
    "This chart reflects total tower rollout. Tower-level or unit-level detail "
    "is not recorded in the source data.",
)

# ==================================================
# ESTIMATED PLANTS OVER TIME
# ==================================================
st.markdown("### Estimated plants over time")

plant_trend_df = (
    df.groupby(["system", "observation_date"], as_index=False)["plants_estimated"]
    .mean()
)

fig = px.line(
    plant_trend_df,
    x="observation_date",
    y="plants_estimated",
    color="system",
    markers=True,
    title="Estimated plants over time (42 plants per tower)",
)

st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Estimated plant count over time.",
    f"Plant counts are derived as towers planted × {PLANTS_PER_TOWER}.",
)

# ==================================================
# GROWTH STAGE AND AGE
# ==================================================
stage_left, stage_right = st.columns(2, gap="large")

with stage_left:
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
            title="Growth-stage distribution",
        )
        st.plotly_chart(fig, use_container_width=True)

with stage_right:
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
# METHODOLOGY NOTE
# ==================================================
with st.expander("Methodology note"):
    st.markdown(
        f"""
        - The dataset records the **number of towers planted**, not individual plants.
        - Each tower is assumed to contain **{PLANTS_PER_TOWER} plants**.
        - Estimated plant counts are derived deterministically.
        - Tower-unit (L1/L2/R1/R2) breakdowns are described in documentation but not encoded in the data.
        """
    )
