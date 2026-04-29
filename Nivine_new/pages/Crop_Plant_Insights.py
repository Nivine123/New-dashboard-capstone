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
# CONSTANTS (REAL SETUP)
# ==================================================
PLANTS_PER_TOWER = 42
TOWER_GROUP_LABELS = ["L1", "L2", "R1", "R2"]

# ==================================================
# PAGE CONTEXT
# ==================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"]

render_hero(
    "Crop / Plant Insights",
    (
        "This page analyzes tower utilization and estimated plant capacity. "
        "The dataset records the number of TOWERS planted (not individual plants). "
        "Each tower is assumed to hold 42 plants."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters.")
    st.stop()

render_comparability_note(context["comparability_note"])

df = df.copy()

# ==================================================
# ✅ DETECT / DERIVE TOWER GROUP (L1 / L2 / R1 / R2)
# ==================================================
tower_group_col = None

# (A) Look for an existing column that already contains L1/L2/R1/R2
for col in df.columns:
    unique_vals = df[col].astype(str).str.upper().unique()
    if any(val in unique_vals for val in TOWER_GROUP_LABELS):
        tower_group_col = col
        break

# (B) Otherwise extract from system text (e.g. "Towers L1")
if tower_group_col is None:
    extracted = (
        df["system"]
        .astype(str)
        .str.upper()
        .str.extract(r"\b(L1|L2|R1|R2)\b")
    )
    if extracted.notna().any().bool():
        df["tower_group"] = extracted[0]
        tower_group_col = "tower_group"

# (C) Final safety check
if tower_group_col is None:
    st.error(
        "Could not find tower groups (L1, L2, R1, R2) in the dataset.\n\n"
        "Please ensure they appear either:\n"
        "- in a dedicated column, or\n"
        "- inside the system name (e.g. 'Towers L1')."
    )
    st.stop()

# ==================================================
# ✅ INTERPRET PLANT_COUNT CORRECTLY
# ==================================================
df["towers_planted"] = df["plant_count"]
df["plants_estimated"] = df["towers_planted"] * PLANTS_PER_TOWER

# ==================================================
# SUMMARY VIEWS
# ==================================================
summary = compute_system_summary(df)
crop_counts = compute_crop_counts(df)

# ==================================================
# KPI CARDS
# ==================================================
cards = [
    (
        "Avg towers planted",
        format_num(df["towers_planted"].mean()),
        "Average number of towers planted per record.",
    ),
    (
        "Avg estimated plants",
        format_num(df["plants_estimated"].mean()),
        "Estimated plants (42 plants per tower).",
    ),
    (
        "Max capacity (Towers)",
        "24 towers",
        "4 groups × 6 towers per group.",
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
# TOWER UTILIZATION BY SYSTEM
# ==================================================
st.markdown("### Tower utilization by system")

util_df = (
    df.groupby("system", as_index=False)["towers_planted"]
    .mean()
    .rename(columns={"towers_planted": "avg_towers_planted"})
)

fig = px.bar(
    util_df,
    x="system",
    y="avg_towers_planted",
    title="Average towers planted by system",
    color="system",
)

fig.update_layout(template="plotly_white", showlegend=False)
st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Average number of towers planted.",
    "These values indicate utilization, not individual plant counts.",
)

# ==================================================
# ✅ PLANTING BEHAVIOR OVER TIME (THIS WILL APPEAR)
# ==================================================
st.markdown("### Planting behavior over time (by tower group)")

trend_df = (
    df.groupby(
        ["system", tower_group_col, "observation_date"],
        as_index=False,
    )["towers_planted"]
    .mean()
)

fig = px.line(
    trend_df,
    x="observation_date",
    y="towers_planted",
    color=tower_group_col,
    markers=True,
    title="Towers planted over time (L1 / L2 / R1 / R2)",
    labels={
        "towers_planted": "Towers planted",
        tower_group_col: "Tower group",
        "observation_date": "Date",
    },
)

st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Tower rollout over time by group.",
    "Each line represents one group of six towers (L1, L2, R1, R2). "
    "Individual physical towers are not recorded separately in the dataset.",
)

# ==================================================
# GROWTH STAGE + AGE
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
# CROP-SYSTEM ASSOCIATIONS
# ==================================================
st.markdown("### Crop-system associations")

rows = []
exploded = df.explode("crop_tokens")
exploded = exploded[
    exploded["crop_tokens"].notna()
    & exploded["crop_tokens"].ne("")
]

for (system, crop), group in exploded.groupby(["system", "crop_tokens"]):
    if len(group) < 5:
        continue

    rows.append(
        {
            "System": system,
            "Crop": crop,
            "Median towers planted": group["towers_planted"].median(),
            "Median estimated plants": group["plants_estimated"].median(),
        }
    )

assoc_df = pd.DataFrame(rows)

if assoc_df.empty:
    st.info("No crop-system combinations meet the evidence threshold.")
else:
    st.dataframe(assoc_df, use_container_width=True, hide_index=True)

with st.expander("Interpretation caution"):
    st.markdown(
        """
        - The dataset records **number of towers planted**, not individual plants.
        - Estimated plant totals assume **42 plants per tower**.
        - Visualizations reflect **tower utilization and rollout**, not yield.
        """
    )
