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

# --------------------------------------------------
# Page context
# --------------------------------------------------
context = build_page_context("Crop / Plant Insights")
df = context["df"]

render_hero(
    "Crop / Plant Insights",
    (
        "Explore plant count, crop diversity, growth stages, age distributions, and the crop-system combinations "
        "that appear linked to higher risk or resource intensity. Interpret associations cautiously and avoid causal claims."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

# --------------------------------------------------
# Detect tower column SAFELY
# --------------------------------------------------
TOWER_CANDIDATES = [
    "tower",
    "tower_id",
    "tower_label",
    "tower_name",
    "unit",
    "module",
]

tower_col = next((c for c in TOWER_CANDIDATES if c in df.columns), None)

# --------------------------------------------------
# Precompute summaries
# --------------------------------------------------
summary = compute_system_summary(df)
crop_counts = compute_crop_counts(df)

# --------------------------------------------------
# KPI cards
# --------------------------------------------------
cards = [
    (
        "Average recorded plant count",
        format_num(df["plant_count"].mean()),
        "Average plant count where the field is populated.",
    ),
    (
        "Distinct crop combinations",
        f"{crop_counts['crop_type'].nunique() if not crop_counts.empty else 0}",
        "Unique crop tokens observed after splitting mixed crop fields.",
    ),
    (
        "Known plant-name share",
        format_pct(df["plant_name_known_flag"].mean()),
        "Rows where the plant name is explicit rather than unknown.",
    ),
    (
        "Known growth-stage share",
        format_pct(df["growth_stage_known_flag"].mean()),
        "Rows where growth stage is populated well enough to analyze.",
    ),
]

cols = st.columns(4, gap="medium")
for col, card in zip(cols, cards):
    with col:
        render_metric_card(*card)

# --------------------------------------------------
# Metadata coverage warning
# --------------------------------------------------
metadata_gap_systems = summary.loc[
    summary[["crop_known_share", "plant_known_share", "growth_known_share"]]
    .fillna(0)
    .mean(axis=1)
    < 0.35,
    "system",
].astype(str).tolist()

if metadata_gap_systems:
    st.info(
        "Plant-level metadata is sparse for "
        + ", ".join(metadata_gap_systems)
        + ". Treat those insights as directional rather than definitive."
    )

# --------------------------------------------------
# Plant count & crop mix
# --------------------------------------------------
st.markdown("### Plant count and crop mix")

left, right = st.columns(2, gap="large")

with left:
    plant_count_view = (
        df.groupby("system", as_index=False)["plant_count"]
        .mean()
        .rename(columns={"plant_count": "average_plant_count"})
    )

    fig = px.bar(
        plant_count_view,
        x="system",
        y="average_plant_count",
        title="Average plant count by system",
        color="system",
    )

    fig.update_layout(
        template="plotly_white",
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    render_chart_conclusion(
        "Average recorded plant count by system.",
        "Counts provide scale context only and should not be interpreted as productivity."
    )

with right:
    if crop_counts.empty:
        st.info("No crop tokens remain after the current filters.")
    else:
        st.plotly_chart(crop_heatmap(crop_counts), use_container_width=True)

# --------------------------------------------------
# Growth stage & age
# --------------------------------------------------
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
        stage_fig = px.bar(
            stage_df,
            x="system",
            y="count",
            color="growth_stage",
            title="Growth-stage distribution",
        )
        st.plotly_chart(stage_fig, use_container_width=True)

with stage_right:
    age_df = df[df["age_days"].notna()]

    if age_df.empty:
        st.info("No age data available.")
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

# --------------------------------------------------
# ✅ Planting behavior over time (TOWERS WHEN AVAILABLE)
# --------------------------------------------------
st.markdown("### Planting behavior over time")

if tower_col is None:
    # System-level fallback
    planting_df = (
        df[df["plant_count"].notna()]
        .groupby(["system", "observation_date"], as_index=False)["plant_count"]
        .mean()
        .rename(columns={"plant_count": "average_plant_count"})
    )

    if planting_df.empty:
        st.info("Plant-count data not sufficient for a trend.")
    else:
        fig = px.line(
            planting_df,
            x="observation_date",
            y="average_plant_count",
            color="system",
            markers=True,
            title="Plant-count trend by system",
        )
        st.plotly_chart(fig, use_container_width=True)

        render_chart_conclusion(
            "Plant-count trend by system.",
            "Tower-level data is not available in this dataset."
        )

else:
    # ✅ Tower-level trend
    planting_df = (
        df[df["plant_count"].notna()]
        .groupby(
            ["system", tower_col, "observation_date"],
            as_index=False,
        )["plant_count"]
        .mean()
        .rename(columns={"plant_count": "average_plant_count"})
    )

    if planting_df.empty:
        st.info("Plant-count data not sufficient for a trend.")
    else:
        fig = px.line(
            planting_df,
            x="observation_date",
            y="average_plant_count",
            color="system",
            line_group=tower_col,
            hover_data=[tower_col],
            title="Plant-count trend by tower and system",
        )

        fig.update_traces(opacity=0.35)
        st.plotly_chart(fig, use_container_width=True)

        render_chart_conclusion(
            "Plant-count trend by tower and system.",
            "Each line represents a tower; drops often indicate harvests or data dropouts."
        )

# --------------------------------------------------
# Crop-system associations
# --------------------------------------------------
st.markdown("### Crop-system associations")

rows = []
exploded = df.explode("crop_tokens")
exploded = exploded[exploded["crop_tokens"].notna() & exploded["crop_tokens"].ne("")]

for (system, crop), group in exploded.groupby(["system", "crop_tokens"]):
    if len(group) < 5:
        continue

    rows.append(
        {
            "System": system,
            "Crop": crop,
