"""Crop and plant insights page (tower-units derived from total towers)."""

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
# CONSTANTS (REAL-WORLD RULES)
# ==================================================
PLANTS_PER_TOWER = 42
TOWERS_PER_UNIT = 6
TOWER_UNITS = ["L1", "L2", "R1", "R2"]

# ==================================================
# Load context
# ==================================================
context = build_page_context("Crop / Plant Insights")
df = context["df"].copy()

render_hero(
    "Crop / Plant Insights",
    (
        "This page analyzes tower utilization and estimated plant capacity. "
        "The dataset records the TOTAL NUMBER OF TOWERS planted. "
        "Tower-unit values (L1, L2, R1, R2) are derived deterministically "
        "based on a capacity of 6 towers per unit."
    ),
)

if df.empty:
    st.warning("No data available after filters.")
    st.stop()

render_comparability_note(context["comparability_note"])

# ==================================================
# Interpret plant_count correctly
# ==================================================
df["towers_planted"] = df["plant_count"]
df["plants_estimated"] = df["towers_planted"] * PLANTS_PER_TOWER

# ==================================================
# ✅ DERIVE UNIT-LEVEL TOWERS (KEY FIX)
# ==================================================
def distribute_towers(total: int) -> dict:
    remaining = int(total)
    allocation = {}
    for unit in TOWER_UNITS:
        allocated = min(TOWERS_PER_UNIT, remaining)
        allocation[unit] = allocated
        remaining -= allocated
    return allocation

unit_rows = []

for _, row in df.iterrows():
    allocation = distribute_towers(row["towers_planted"])
    for unit, count in allocation.items():
        unit_rows.append(
            {
                "system": row["system"],
                "tower_unit": unit,
                "observation_date": row["observation_date"],
                "towers_planted": count,
                "plants_estimated": count * PLANTS_PER_TOWER,
            }
        )

unit_df = pd.DataFrame(unit_rows)

# ==================================================
# KPI CARDS
# ==================================================
cards = [
    (
        "Avg towers planted",
        format_num(df["towers_planted"].mean()),
        "Average total towers planted (out of 24).",
    ),
    (
        "Avg estimated plants",
        format_num(df["plants_estimated"].mean()),
        "Estimated plants (42 plants per tower).",
    ),
    (
        "Max capacity",
        "24 towers",
        "4 units × 6 towers per unit.",
    ),
    (
        "Known growth-stage share",
        format_pct(df["growth_stage_known_flag"].mean()),
        "Rows with usable growth-stage data.",
    ),
]

cols = st.columns(4, gap="medium")
for col, card in zip(cols, cards):
    with col:
        render_metric_card(*card)

# ==================================================
# PLANTING BEHAVIOR OVER TIME (NOW WORKS)
# ==================================================
st.markdown("### Tower-unit planting behavior over time")

trend_df = (
    unit_df.groupby(["tower_unit", "observation_date"], as_index=False)["towers_planted"]
    .mean()
)

fig = px.line(
    trend_df,
    x="observation_date",
    y="towers_planted",
    color="tower_unit",
    markers=True,
    title="Towers planted over time by unit (L1, L2, R1, R2)",
    labels={
        "towers_planted": "Towers planted",
        "tower_unit": "Tower unit",
        "observation_date": "Date",
    },
)

st.plotly_chart(fig, use_container_width=True)

render_chart_conclusion(
    "Derived tower-unit behavior.",
    "Each line represents a unit of six towers. Values are derived from total towers planted "
    "using a deterministic allocation rule.",
)

# ==================================================
# OPTIONAL: Estimated plants over time
# ==================================================
st.markdown("### Estimated plants over time by unit")

plant_trend_df = (
    unit_df.groupby(["tower_unit", "observation_date"], as_index=False)["plants_estimated"]
    .mean()
)

fig2 = px.line(
    plant_trend_df,
    x="observation_date",
    y="plants_estimated",
    color="tower_unit",
    markers=True,
    title="Estimated plants over time (42 plants per tower)",
)

st.plotly_chart(fig2, use_container_width=True)

# ==================================================
# Interpretation disclaimer
# ==================================================
with st.expander("Methodology note"):
    st.markdown(
        """
        - The dataset records the **total number of towers planted**.
        - Tower-unit values (L1/L2/R1/R2) are **derived**, not directly observed.
        - Each unit has a maximum of **6 towers**.
        - Each tower holds **42 plants**.
        - This approach preserves total counts while enabling unit-level insight.
        """
    )
