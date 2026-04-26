from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.ui import build_page_context, render_chart_conclusion, render_hero


# -----------------------------
# Page setup and data
# -----------------------------
context = build_page_context("Cost Optimization")
df = context["df"]

render_hero(
    "Cost Optimization & Resource Burden",
    (
        "Estimate relative cost pressure using operational proxies for water use, nutrient tracking, manual workload, leaks, "
        "and issue events. These are sensitivity assumptions, not accounting records."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()


# -----------------------------
# Helper functions
# -----------------------------
def to_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.lower()
        .str.strip()
        .isin(["true", "yes", "y", "1"])
    )


def get_column(data: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in data.columns:
            return col
    return None


def normalize_score(series: pd.Series, higher_is_worse: bool = True) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").fillna(0)

    if s.max() == s.min():
        return pd.Series(50, index=s.index)

    normalized = 100 * (s - s.min()) / (s.max() - s.min())

    if higher_is_worse:
        return normalized

    return 100 - normalized


# -----------------------------
# Column detection
# -----------------------------
system_col = get_column(df, ["system_display", "system", "system_label"])
date_col = get_column(df, ["observation_date", "date_only", "observation_date_dt"])
water_col = get_column(df, ["water_use_l", "water_consumed_l", "watered_amount_l"])
nutrient_col = get_column(df, ["nutrient_effective_ml", "nutrient_total_ml", "nutrient_use_ml", "nutrient_ml"])
ph_col = get_column(df, ["ph_down_effective_ml", "ph_down_ml", "ph_down_milliliters"])
plant_col = get_column(df, ["plant_count", "plant_count_filled"])
manual_col = get_column(df, ["manual_intervention_flag", "manual_water_addition"])
leak_col = get_column(df, ["leak_flag", "leak_flag_bool"])
issue_col = get_column(df, ["issue_flag", "issue_flag_bool"])
duration_col = get_column(df, ["water_addition_duration_min"])
quality_col = get_column(df, ["data_quality_status", "quality_label"])

if system_col is None:
    st.error("No system column found.")
    st.stop()

df = df.copy()
df["system_name"] = df[system_col].fillna("Unknown").astype(str)

if date_col:
    df["date_clean"] = pd.to_datetime(df[date_col], errors="coerce").dt.date
else:
    df["date_clean"] = np.nan

df["water_l"] = pd.to_numeric(df[water_col], errors="coerce").fillna(0) if water_col else 0
df["nutrient_ml"] = pd.to_numeric(df[nutrient_col], errors="coerce").fillna(0) if nutrient_col else 0
df["ph_down_ml"] = pd.to_numeric(df[ph_col], errors="coerce").fillna(0) if ph_col else 0
df["plant_count_clean"] = pd.to_numeric(df[plant_col], errors="coerce") if plant_col else np.nan

df["manual_flag"] = to_bool(df[manual_col]) if manual_col else False
df["leak_flag_clean"] = to_bool(df[leak_col]) if leak_col else False
df["issue_flag_clean"] = to_bool(df[issue_col]) if issue_col else False
df["duration_min"] = pd.to_numeric(df[duration_col], errors="coerce").fillna(0) if duration_col else 0


# -----------------------------
# Sidebar assumptions
# -----------------------------
st.sidebar.header("Cost model assumptions")

water_cost_per_l = st.sidebar.number_input(
    "Water cost per liter ($)",
    min_value=0.0,
    value=0.0,
    step=0.0005,
    format="%.4f",
)

nutrient_cost_per_ml = st.sidebar.number_input(
    "Nutrient cost per mL ($)",
    min_value=0.0,
    value=0.0,
    step=0.001,
    format="%.4f",
)

ph_down_cost_per_ml = st.sidebar.number_input(
    "pH-down cost per mL ($)",
    min_value=0.0,
    value=0.0,
    step=0.001,
    format="%.4f",
)

duration_cost_per_min = st.sidebar.number_input(
    "Operating duration cost per minute ($)",
    min_value=0.0,
    value=0.0,
    step=0.25,
)

manual_intervention_cost = st.sidebar.number_input(
    "Manual intervention cost per event ($)",
    min_value=0.0,
    value=0.0,
    step=0.50,
)

leak_cost = st.sidebar.number_input(
    "Leak / loss cost per event ($)",
    min_value=0.0,
    value=0.0,
    step=0.50,
)

issue_cost = st.sidebar.number_input(
    "Operational issue cost per event ($)",
    min_value=0.0,
    value=0.0,
    step=0.50,
)

st.sidebar.caption(
    "Enter local assumptions for sensitivity analysis. Defaults are zero so the app does not invent costs."
)


# -----------------------------
# Cost calculations
# -----------------------------
df["water_cost"] = df["water_l"] * water_cost_per_l
df["nutrient_cost"] = df["nutrient_ml"] * nutrient_cost_per_ml
df["ph_adjustment_cost"] = df["ph_down_ml"] * ph_down_cost_per_ml
df["duration_cost"] = df["duration_min"] * duration_cost_per_min
df["workload_cost"] = df["manual_flag"].astype(int) * manual_intervention_cost
df["risk_loss_cost"] = (
    df["leak_flag_clean"].astype(int) * leak_cost
    + df["issue_flag_clean"].astype(int) * issue_cost
)

df["estimated_cost"] = (
    df["water_cost"]
    + df["nutrient_cost"]
    + df["ph_adjustment_cost"]
    + df["duration_cost"]
    + df["workload_cost"]
    + df["risk_loss_cost"]
)


# -----------------------------
# System-level summary
# -----------------------------
summary = (
    df.groupby("system_name", as_index=False)
    .agg(
        observations=("system_name", "size"),
        active_days=("date_clean", "nunique"),
        total_water_l=("water_l", "sum"),
        total_nutrient_ml=("nutrient_ml", "sum"),
        total_ph_down_ml=("ph_down_ml", "sum"),
        manual_interventions=("manual_flag", "sum"),
        leak_events=("leak_flag_clean", "sum"),
        issue_events=("issue_flag_clean", "sum"),
        water_cost=("water_cost", "sum"),
        nutrient_cost=("nutrient_cost", "sum"),
        ph_adjustment_cost=("ph_adjustment_cost", "sum"),
        duration_cost=("duration_cost", "sum"),
        workload_cost=("workload_cost", "sum"),
        risk_loss_cost=("risk_loss_cost", "sum"),
        total_estimated_cost=("estimated_cost", "sum"),
        avg_duration_min=("duration_min", "mean"),
    )
)

summary["active_days"] = summary["active_days"].replace(0, np.nan)
summary["cost_per_active_day"] = summary["total_estimated_cost"] / summary["active_days"]
summary["water_per_active_day"] = summary["total_water_l"] / summary["active_days"]
summary["nutrient_per_active_day"] = summary["total_nutrient_ml"] / summary["active_days"]
summary["manual_rate_pct"] = 100 * summary["manual_interventions"] / summary["observations"]
summary["leak_rate_pct"] = 100 * summary["leak_events"] / summary["observations"]
summary["issue_rate_pct"] = 100 * summary["issue_events"] / summary["observations"]

summary["risk_score"] = (
    0.35 * summary["issue_rate_pct"]
    + 0.35 * summary["leak_rate_pct"]
    + 0.30 * summary["manual_rate_pct"]
).clip(0, 100)

summary["cost_burden_score"] = normalize_score(
    summary["total_estimated_cost"], higher_is_worse=True
)

summary["cost_efficiency_score"] = normalize_score(
    summary["total_estimated_cost"], higher_is_worse=False
)

cost_components = summary[
    [
        "system_name",
        "water_cost",
        "nutrient_cost",
        "ph_adjustment_cost",
        "duration_cost",
        "workload_cost",
        "risk_loss_cost",
    ]
].melt(
    id_vars="system_name",
    var_name="cost_component",
    value_name="cost_value",
)

component_labels = {
    "water_cost": "Water",
    "nutrient_cost": "Nutrients",
    "ph_adjustment_cost": "pH adjustment",
    "duration_cost": "Operating duration",
    "workload_cost": "Workload",
    "risk_loss_cost": "Risk / Losses",
}
cost_components["cost_component"] = cost_components["cost_component"].map(component_labels)

summary["top_cost_driver"] = summary[
    [
        "water_cost",
        "nutrient_cost",
        "ph_adjustment_cost",
        "duration_cost",
        "workload_cost",
        "risk_loss_cost",
    ]
].idxmax(axis=1).map(component_labels)


# -----------------------------
# KPI row
# -----------------------------
st.markdown("## Executive Cost View")

total_cost = summary["total_estimated_cost"].sum()
highest_cost_row = summary.loc[summary["total_estimated_cost"].idxmax()]
lowest_cost_row = summary.loc[summary["total_estimated_cost"].idxmin()]
highest_risk_row = summary.loc[summary["risk_score"].idxmax()]

k1, k2, k3, k4 = st.columns(4)

k1.metric("Estimated Total Cost", f"${total_cost:,.2f}")
k2.metric("Highest Cost System", highest_cost_row["system_name"])
k3.metric("Lowest Cost System", lowest_cost_row["system_name"])
k4.metric("Highest Risk System", highest_risk_row["system_name"])


st.info(
    "Cost is estimated using only the assumptions entered in the sidebar and observed operational proxies: water, nutrients, pH-down, duration, workload, leaks, and issues."
)
if total_cost == 0:
    st.warning(
        "All cost assumptions are currently zero. Enter local unit costs in the sidebar to turn this page into a sensitivity analysis."
    )


# -----------------------------
# Chart 1: Cost burden by system
# -----------------------------
st.markdown("## Cost Burden by System")

fig_cost_bar = px.bar(
    summary.sort_values("total_estimated_cost", ascending=False),
    x="system_name",
    y="total_estimated_cost",
    text="total_estimated_cost",
    title="Estimated Total Cost by System",
    labels={
        "system_name": "System",
        "total_estimated_cost": "Estimated Cost ($)",
    },
)

fig_cost_bar.update_traces(texttemplate="$%{text:,.2f}", textposition="outside")
fig_cost_bar.update_layout(yaxis_tickprefix="$", showlegend=False)

st.plotly_chart(fig_cost_bar, width="stretch")
render_chart_conclusion(
    "Estimated total cost by system under the current sidebar assumptions.",
    "When assumptions are zero, the chart intentionally shows no cost burden; once real values are entered, the highest bar becomes the first cost-review target.",
)


# -----------------------------
# Chart 2: Cost breakdown by system
# -----------------------------
st.markdown("## Cost Breakdown per System")

fig_breakdown = px.bar(
    cost_components,
    x="system_name",
    y="cost_value",
    color="cost_component",
    title="Estimated Cost Breakdown by System",
    labels={
        "system_name": "System",
        "cost_value": "Estimated Cost ($)",
        "cost_component": "Cost Driver",
    },
)

fig_breakdown.update_layout(
    barmode="stack",
    yaxis_tickprefix="$",
    legend_title_text="Cost Driver",
)

st.plotly_chart(fig_breakdown, width="stretch")
render_chart_conclusion(
    "Estimated cost split into water, nutrients, pH adjustment, duration, workload, and risk/loss components.",
    "The largest segment in each bar points to the cost driver that should be optimized first.",
)

if total_cost > 0:
    st.markdown("## Cost Driver Treemap")
    fig_treemap = px.treemap(
        cost_components[cost_components["cost_value"] > 0],
        path=["system_name", "cost_component"],
        values="cost_value",
        color="cost_component",
        title="Cost Driver Hierarchy",
    )
    fig_treemap.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_treemap, width="stretch")
    render_chart_conclusion(
        "A hierarchical view of which systems and cost components consume the modeled budget.",
        "Large rectangles identify where a practical optimization plan can have the biggest financial impact.",
    )


# -----------------------------
# Chart 3: Cost vs risk
# -----------------------------
st.markdown("## Cost vs Risk Trade-off")

fig_cost_risk = px.scatter(
    summary,
    x="total_estimated_cost",
    y="risk_score",
    size="cost_burden_score",
    color="system_name",
    text="system_name",
    title="Cost vs Operational Risk",
    labels={
        "total_estimated_cost": "Estimated Cost ($)",
        "risk_score": "Operational Risk Score",
        "system_name": "System",
    },
    hover_data={
        "total_estimated_cost": ":,.2f",
        "risk_score": ":.1f",
        "cost_burden_score": ":.1f",
        "top_cost_driver": True,
    },
)

fig_cost_risk.update_traces(textposition="top center")
fig_cost_risk.update_layout(xaxis_tickprefix="$")

st.plotly_chart(fig_cost_risk, width="stretch")
render_chart_conclusion(
    "Estimated cost compared with operational risk score.",
    "Systems that sit high on both axes deserve priority because they combine cost pressure with reliability or maintenance concerns.",
)


# -----------------------------
# Chart 4: Workload vs cost
# -----------------------------
st.markdown("## Workload vs Cost")

fig_workload = px.scatter(
    summary,
    x="manual_interventions",
    y="total_estimated_cost",
    size="risk_score",
    color="system_name",
    text="system_name",
    title="Manual Intervention Burden vs Estimated Cost",
    labels={
        "manual_interventions": "Manual Interventions",
        "total_estimated_cost": "Estimated Cost ($)",
    },
)

fig_workload.update_traces(textposition="top center")
fig_workload.update_layout(yaxis_tickprefix="$")

st.plotly_chart(fig_workload, width="stretch")
render_chart_conclusion(
    "Manual intervention burden compared with estimated cost.",
    "A positive relationship suggests automation, monitoring, or process redesign could reduce both labor pressure and modeled cost.",
)

if total_cost > 0:
    st.markdown("## Portfolio Cost Waterfall")
    driver_totals = (
        cost_components.groupby("cost_component", as_index=False)["cost_value"]
        .sum()
        .sort_values("cost_value", ascending=False)
    )
    fig_waterfall = go.Figure(
        go.Waterfall(
            name="Cost drivers",
            orientation="v",
            measure=["relative"] * len(driver_totals) + ["total"],
            x=driver_totals["cost_component"].tolist() + ["Total"],
            y=driver_totals["cost_value"].tolist() + [driver_totals["cost_value"].sum()],
            connector={"line": {"color": "#CBD5E1"}},
        )
    )
    fig_waterfall.update_layout(
        title="Modeled cost build-up by driver",
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis_tickprefix="$",
    )
    st.plotly_chart(fig_waterfall, width="stretch")
    render_chart_conclusion(
        "How each entered cost driver contributes to the total modeled cost.",
        "The waterfall is useful for capstone decision support because it makes the budget impact of each assumption transparent.",
    )


# -----------------------------
# Cost summary table
# -----------------------------
st.markdown("## Cost Optimization Table")

table = summary[
    [
        "system_name",
        "observations",
        "active_days",
        "total_water_l",
        "total_nutrient_ml",
        "total_ph_down_ml",
        "manual_interventions",
        "leak_events",
        "issue_events",
        "water_cost",
        "nutrient_cost",
        "ph_adjustment_cost",
        "duration_cost",
        "workload_cost",
        "risk_loss_cost",
        "total_estimated_cost",
        "cost_burden_score",
        "cost_efficiency_score",
        "risk_score",
        "top_cost_driver",
    ]
].copy()

table = table.rename(
    columns={
        "system_name": "System",
        "observations": "Observations",
        "active_days": "Active Days",
        "total_water_l": "Water Use (L)",
        "total_nutrient_ml": "Nutrient Use (mL)",
        "total_ph_down_ml": "pH-down Use (mL)",
        "manual_interventions": "Manual Interventions",
        "leak_events": "Leak Events",
        "issue_events": "Issue Events",
        "water_cost": "Water Cost ($)",
        "nutrient_cost": "Nutrient Cost ($)",
        "ph_adjustment_cost": "pH Adjustment Cost ($)",
        "duration_cost": "Duration Cost ($)",
        "workload_cost": "Workload Cost ($)",
        "risk_loss_cost": "Risk / Loss Cost ($)",
        "total_estimated_cost": "Total Estimated Cost ($)",
        "cost_burden_score": "Cost Burden Score",
        "cost_efficiency_score": "Cost Efficiency Score",
        "risk_score": "Risk Score",
        "top_cost_driver": "Top Cost Driver",
    }
)

st.dataframe(table, width="stretch", hide_index=True)


# -----------------------------
# Insights
# -----------------------------
st.markdown("## Cost Optimization Insights")

highest_driver = highest_cost_row["top_cost_driver"]

insights = [
    f"**{highest_cost_row['system_name']}** has the highest estimated cost burden.",
    f"The main cost driver for **{highest_cost_row['system_name']}** is **{highest_driver}**.",
    f"**{lowest_cost_row['system_name']}** has the lowest estimated cost burden under the current assumptions.",
    f"**{highest_risk_row['system_name']}** has the highest operational risk score, meaning cost optimization should also consider reliability and maintenance burden.",
    "Cost optimization should focus on reducing inefficiencies, not simply minimizing inputs.",
]

for item in insights:
    st.markdown(f"- {item}")


# -----------------------------
# Recommendations
# -----------------------------
st.markdown("## Business Recommendations")

recommendations = []

if total_cost == 0:
    recommendations.append(
        "Enter local cost assumptions in the sidebar before using this page for cost-ranking decisions."
    )
else:
    high_cost_high_risk = summary[
        (summary["cost_burden_score"] >= summary["cost_burden_score"].median())
        & (summary["risk_score"] >= summary["risk_score"].median())
    ]

    if not high_cost_high_risk.empty:
        systems = ", ".join(high_cost_high_risk["system_name"].tolist())
        recommendations.append(
            f"Prioritize **{systems}** for cost and risk reduction because they show both high cost burden and elevated operational risk."
        )

    for _, row in summary.iterrows():
        if row["top_cost_driver"] == "Risk / Losses":
            recommendations.append(
                f"For **{row['system_name']}**, focus on leak prevention and issue reduction because risk-related losses are the dominant cost driver."
            )
        elif row["top_cost_driver"] == "Workload":
            recommendations.append(
                f"For **{row['system_name']}**, reduce manual intervention through better monitoring, maintenance routines, or automation."
            )
        elif row["top_cost_driver"] == "Water":
            recommendations.append(
                f"For **{row['system_name']}**, investigate water-use efficiency and possible sources of water waste."
            )
        elif row["top_cost_driver"] == "Nutrients":
            recommendations.append(
                f"For **{row['system_name']}**, improve nutrient tracking and dosing control to reduce input waste."
            )
        elif row["top_cost_driver"] == "pH adjustment":
            recommendations.append(
                f"For **{row['system_name']}**, review pH adjustment frequency and dosing consistency because pH-down is the dominant modeled driver."
            )
        elif row["top_cost_driver"] == "Operating duration":
            recommendations.append(
                f"For **{row['system_name']}**, investigate cycle duration and operating routines because duration assumptions dominate the modeled cost."
            )

    recommendations.append(
        "Use the cost assumptions as a sensitivity tool: changing unit costs helps test whether conclusions remain stable."
    )

for rec in recommendations:
    st.markdown(f"- {rec}")


# -----------------------------
# Methodology note
# -----------------------------
st.markdown("## Methodology Note")

st.warning(
    """
This page uses a **proxy cost model**, not full accounting data.  
Estimated cost is calculated from water use, nutrient use, manual intervention burden, and operational risk signals.
The purpose is to identify relative cost pressure and optimization priorities across systems.
"""
)
