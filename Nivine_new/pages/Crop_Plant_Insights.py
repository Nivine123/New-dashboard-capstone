"""Crop and plant insights page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.charts import crop_heatmap, crop_sunburst_chart, histogram_chart
from utils.metrics import (
    compute_crop_counts,
    compute_system_summary,
    format_num,
    format_pct,
)
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

# ==================================================
# Constants (REAL-WORLD MODEL)
# ==================================================
PLANTS_PER_TOWER = 42
TOWERS_PER_GROUP = 6           # L1, L2, R1, R2 each
TOWER_GROUPS = ["L1", "L2", "R1", "R2"]

# ==================================================
# Page context
# ==================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"]

render_hero(
    "Crop / Plant Insights",
    (
        "Explore tower utilization, estimated plant counts, crop diversity, growth stages, "
        "age distributions, and crop-system associations. "
        "Plant counts are derived from tower counts (42 plants per tower)."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters.")
    st.stop()

render_comparability_note(context["comparability_note"])

# ==================================================
# Build tower identifiers (L1/L2/R1/R2 + tower index)
# ==================================================
if {"tower_group", "tower_index"}.issubset(df.columns):
    df["tower_id"] = (
        df["tower_group"].astype(str).str.strip()
        + "-"
        + df["tower_index"].astype(str).str.strip()
    )
else:
    df["tower_id"] = None

# ==================================================
# Derive estimated plant counts
# Excel value = towers planted
# ==================================================
df["towers_planted"] = df["plant_count"]
df["plants_estimated"] = df["towers_planted"] * PLANTS_PER_TOWER

# ==================================================
# Summaries
# ==================================================
summary = compute_system_summary(df)
crop_counts = compute_crop_counts(df)

# ==================================================
# KPI Cards
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
        "Distinct crop tokens",
        str(crop_counts["crop_type"].nunique() if not crop_counts.empty else 0),
        "Unique crop labels observed.",
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
# Plant count (TOWERS) + Crop mix
# ==================================================
st.markdown("### Tower utilization and crop mix")

left, right = st.columns(2, gap="large")

with left:
    tower_view = (
        df.groupby("system", as_index=False)["towers_planted"]
        .mean()
        .rename(columns={"towers_planted": "avg_towers_planted"})
    )

    fig = px.bar(
        tower_view,
        x="system",
        y="avg_towers_planted",
        title="Average towers planted by system",
        color="system",
    )

    fig.update_layout(template="plotly_white", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    render_chart_conclusion(
        "Average towers planted by system.",
        "Values represent tower utilization, not number of plants.",
    )

with right:
    if crop_counts.empty:
        st.info("No crop tokens remain after filtering.")
    else:
        st.plotly_chart(crop_heatmap(crop_counts), use_container_width=True)

# ==================================================
# Growth stage and age
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
# ✅ PLANTING BEHAVIOR OVER TIME — TOWER LEVEL
# ==================================================
st.markdown("### Planting behavior over time (tower level)")

if df["tower_id"].isna().all():
    st.warning(
        "Tower identifiers are not available, so trends are shown at the system level."
    )

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
        title="Towers planted over time (system average)",
    )

else:
    trend_df = (
        df.groupby(
            ["system", "tower_id", "observation_date"],
            as_index=False,
        )["towers_planted"]
        .mean()
    )

    fig = px.line(
        trend_df,
        x="observation_date",
        y="towers_planted",
        color="system",
        line_group="tower_id",
        hover_data=["tower_id"],
        title="Towers planted over time (L1/L2/R1/R2 × 6 towers)",
    )

    fig.update_traces(opacity=0.35)

st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Tower planting behavior over time.",
    "Each line represents a physical tower. "
    "Plant totals are derived as towers planted × 42 plants.",
)

# ==================================================
# Crop-system associations
# ==================================================
st.markdown("### Crop-system associations")

rows = []
exploded = df.explode("crop_tokens")
exploded = exploded[
    exploded["crop_tokens"].notna() & exploded["crop_tokens"].ne("")
]

for (system, crop), group in exploded.groupby(["system", "crop_tokens"]):
    if len(group) < 5:
        continue

    rows.append(
        {
            "System": system,
            "Crop": crop,
            "Observations": len(group),
            "Median towers planted": group["towers_planted"].median(),
            "Median estimated plants": group["plants_estimated"].median(),
        }
    )

assoc_df = pd.DataFrame(rows)

if assoc_df.empty:
    st.info("No crop-system combinations meet the minimum evidence threshold.")
else:
    st.dataframe(assoc_df, use_container_width=True, hide_index=True)

with st.expander("Interpretation caution"):
    st.markdown(
        """
        - The dataset records **number of towers planted**, not plant counts.
        - Estimated plants are derived assuming **42 plants per tower**.
        - Results represent operational capacity and rollout, not yield.
        """
    )
