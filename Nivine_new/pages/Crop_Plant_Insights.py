"""Crop and plant insights page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.charts import crop_heatmap, crop_sunburst_chart, histogram_chart
from utils.metrics import compute_crop_counts, compute_system_summary, format_num, format_pct
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

context = build_page_context("Crop / Plant Insights")
df = context["df"]

render_hero(
    "Crop / Plant Insights",
    (
        "Explore plant count, crop diversity, growth stages, age distributions, and the crop-system combinations that appear linked "
        "to higher risk or resource intensity. Interpret associations cautiously and avoid causal claims."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

summary = compute_system_summary(df)
crop_counts = compute_crop_counts(df)

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

card_cols = st.columns(4, gap="medium")
for column, card in zip(card_cols, cards):
    with column:
        render_metric_card(*card)

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
        + ". Treat those crop insights as directional rather than definitive."
    )

st.markdown("### Plant count and crop mix")
plant_left, plant_right = st.columns(2, gap="large")
with plant_left:
    plant_count_view = (
    df[df["plant_count"].notna()]
    .groupby("system", as_index=False)
    .agg(
        average_plant_count=("plant_count", "mean"),
        plant_count_records=("plant_count", "count"),
    )
)
    plant_fig = px.bar(
        plant_count_view,
        x="system",
        y="average_plant_count",
        title="Average plant count by system",
        color="system",
    )
    plant_fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
        showlegend=False,
    )
    st.plotly_chart(plant_fig, width="stretch")
    render_chart_conclusion(
        "Average recorded plant count by system.",
        "Plant-count differences provide useful scale context, but they should not be turned into productivity claims unless coverage is consistent.",
    )
with plant_right:
    if crop_counts.empty:
        st.info("No crop tokens remain after the current filters.")
    else:
        st.plotly_chart(crop_heatmap(crop_counts), width="stretch")
        render_chart_conclusion(
            "Crop-token counts across systems.",
            "Crop mix explains why some system comparisons are not perfectly like-for-like.",
        )

if not crop_counts.empty:
    st.plotly_chart(crop_sunburst_chart(crop_counts), width="stretch")
    render_chart_conclusion(
        "Crop hierarchy nested by system.",
        "The sunburst makes crop concentration visible and helps separate broad crop diversity from system-specific crop focus.",
    )

stage_left, stage_right = st.columns(2, gap="large")
with stage_left:
    growth_stage_df = (
        df[df["growth_stage_known_flag"]]
        .groupby(["system", "growth_stage"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    if growth_stage_df.empty:
        st.info("Growth-stage fields are too sparse for the current filter scope.")
    else:
        stage_fig = px.bar(
            growth_stage_df,
            x="system",
            y="count",
            color="growth_stage",
            title="Growth-stage distribution",
        )
        stage_fig.update_layout(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(255,255,255,0.88)",
        )
        st.plotly_chart(stage_fig, width="stretch")
        render_chart_conclusion(
            "Growth-stage distribution by system.",
            "Uneven growth-stage mix can affect water demand and risk, so it should be considered before comparing systems directly.",
        )

with stage_right:
    age_df = df[df["age_days"].notna()].copy()
    if age_df.empty:
        st.info("Age data is not available for the current filter scope.")
    else:
        st.plotly_chart(
            histogram_chart(
                age_df,
                x="age_days",
                color="system",
                title="Age distribution by system",
                bins=20,
            ),
            width="stretch",
        )
        render_chart_conclusion(
            "Age distribution of plants where age is available.",
            "Age spread provides lifecycle context; sparse or single-system age data should stay descriptive.",
        )

st.markdown("### Planting behavior over time")
planting_df = (
    df[df["plant_count"].notna()]
    .groupby(["system", "observation_date"], as_index=False)["plant_count"]
    .mean()
    .rename(columns={"plant_count": "average_plant_count"})
)
if planting_df.empty:
    st.info("Plant-count data is not sufficient for a time trend under the current filters.")
else:
    planting_fig = px.line(
        planting_df,
        x="observation_date",
        y="average_plant_count",
        color="system",
        markers=True,
        title="Plant-count trend by system",
    )
    planting_fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
    )
    st.plotly_chart(planting_fig, width="stretch")
    render_chart_conclusion(
        "Plant-count trend through time by system.",
        "Changes in plant count can explain shifts in water use or workload, especially around planting and harvest periods.",
    )

st.markdown("### Crop-system associations")
crop_assoc_rows = []
exploded_crop_df = df.explode("crop_tokens")
exploded_crop_df = exploded_crop_df[
    exploded_crop_df["crop_tokens"].notna() & exploded_crop_df["crop_tokens"].ne("")
]

for (system, crop_type), group in exploded_crop_df.groupby(["system", "crop_tokens"]):
    if not crop_type or len(group) < 5:
        continue
    crop_assoc_rows.append(
        {
            "System": system,
            "Crop": crop_type,
            "Observations": len(group),
            "Issue incidence": group["issue_incident_flag"].mean(),
            "Observed leak rate": group.loc[group["leak_reported_flag"], "leak_incident_flag"].mean(),
            "Median water use (L)": group.loc[group["water_use_l"].notna(), "water_use_l"].median(),
            "Interpretation": (
                "Association only; this pattern may reflect crop mix, stage, or operating conditions rather than a crop effect."
            ),
        }
    )

crop_assoc_df = pd.DataFrame(crop_assoc_rows).sort_values(
    ["Issue incidence", "Observations"], ascending=[False, False]
) if crop_assoc_rows else pd.DataFrame()

if crop_assoc_df.empty:
    st.info("No crop-system combinations meet the minimum evidence threshold of five observations.")
else:
    st.dataframe(crop_assoc_df, width="stretch", hide_index=True)

with st.expander("Interpretation caution", expanded=False):
    st.markdown(
        """
        - Crop and plant patterns should be read as observed associations, not causal relationships.
        - Plant-count coverage is uneven across systems, so the dashboard avoids per-plant productivity claims.
        - Hydroponic systems contain much weaker plant-name and growth-stage coverage than the Conventional system, which limits direct crop-level comparison.
        """
    )
