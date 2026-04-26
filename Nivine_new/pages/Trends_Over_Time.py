"""Trends over time page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.charts import line_trend_chart, weekday_density_heatmap, weekly_multi_metric_chart
from utils.metrics import compute_daily_metrics, compute_weekly_metrics
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
)

context = build_page_context("Trends Over Time")
df = context["df"]

render_hero(
    "Trends Over Time",
    (
        "Track greenhouse activity through time using daily and weekly summaries of water use, nutrient additions, leaks, issues, "
        "and rolling stability indicators."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

daily = compute_daily_metrics(df)
weekly = compute_weekly_metrics(df)

activity_df = (
    df.groupby(["system", "observation_date"], as_index=False)
    .size()
    .rename(columns={"size": "observations"})
)

top_left, top_right = st.columns(2, gap="large")
with top_left:
    activity_fig = px.line(
        activity_df,
        x="observation_date",
        y="observations",
        color="system",
        markers=True,
        title="Observation activity over time",
    )
    activity_fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
    )
    st.plotly_chart(activity_fig, width="stretch")
    render_chart_conclusion(
        "Observation counts through time by system.",
        "Uneven logging intensity can shape apparent trends, so activity volume should be checked before reading performance movement.",
    )
with top_right:
    st.plotly_chart(
        weekly_multi_metric_chart(
            weekly,
            metric="weekly_water_use_l",
            title="Weekly water-use trend",
            y_title="Liters per week",
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "Weekly water-use totals by system.",
        "Weekly aggregation reduces noise and makes broader operating phases easier to see.",
    )

mid_left, mid_right = st.columns(2, gap="large")
with mid_left:
    st.plotly_chart(
        weekly_multi_metric_chart(
            weekly,
            metric="weekly_nutrient_ml",
            title="Weekly nutrient additions",
            y_title="mL per week",
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "Weekly nutrient addition totals by system.",
        "Nutrient spikes can indicate operational interventions, dosing changes, or incomplete logging depending on data quality.",
    )
with mid_right:
    incident_long = weekly.melt(
        id_vars=["system", "observation_week"],
        value_vars=["issue_events", "leak_events"],
        var_name="incident_type",
        value_name="events",
    )
    issue_weekly_fig = px.line(
        incident_long,
        x="observation_week",
        y="events",
        color="system",
        line_dash="incident_type",
        markers=True,
        title="Weekly incident trend",
    )
    issue_weekly_fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
        yaxis_title="Events per week",
        xaxis_title="",
    )
    st.plotly_chart(issue_weekly_fig, width="stretch")
    render_chart_conclusion(
        "Weekly issue and leak event trends.",
        "Clusters identify periods for root-cause review and help connect operational events to water or workload patterns.",
    )

st.markdown("### Rolling stability signals")
st.markdown(
    "<div class='section-caption'>Rolling averages help distinguish enduring operational shifts from short-lived spikes or aggregate weekend entries.</div>",
    unsafe_allow_html=True,
)

roll_left, roll_right = st.columns(2, gap="large")
with roll_left:
    st.plotly_chart(
        line_trend_chart(
            daily.dropna(subset=["rolling_7d_water_use_l"]),
            x="observation_date",
            y="rolling_7d_water_use_l",
            title="7-day rolling water-use average",
            y_title="Liters",
            rolling=True,
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "A rolling 7-day water-use average.",
        "Sustained shifts are more decision-relevant than one-day spikes, especially when aggregate rows are present.",
    )
with roll_right:
    st.plotly_chart(
        line_trend_chart(
            daily.dropna(subset=["rolling_14d_issue_rate"]),
            x="observation_date",
            y="rolling_14d_issue_rate",
            title="14-day rolling issue intensity",
            y_title="Average issue events",
            rolling=True,
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "A rolling 14-day issue intensity signal.",
        "An upward rolling line suggests recurring operating pressure rather than isolated incidents.",
    )

bottom_left, bottom_right = st.columns(2, gap="large")
with bottom_left:
    st.plotly_chart(
        weekly_multi_metric_chart(
            weekly,
            metric="manual_events",
            title="Weekly manual interventions",
            y_title="Manual events per week",
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "Manual intervention events summarized weekly.",
        "Workload trends show whether a system is becoming easier or harder to operate over time.",
    )
with bottom_right:
    st.plotly_chart(
        weekly_multi_metric_chart(
            weekly,
            metric="rolling_4w_water_use_l",
            title="4-week smoothed water-use trend",
            y_title="Liters",
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "A 4-week smoothed water-use view.",
        "This is the cleanest chart for thesis storytelling because it emphasizes broader directional movement.",
    )

st.markdown("### Observation rhythm")
st.plotly_chart(weekday_density_heatmap(df), width="stretch")
render_chart_conclusion(
    "Observation density by weekday and system.",
    "Strong weekday concentration can reflect measurement routine rather than system behavior, so it should temper temporal conclusions.",
)

with st.expander("Temporal analysis note", expanded=False):
    st.markdown(
        """
        - Daily charts preserve event timing but can still reflect weekend aggregation if those rows are included.
        - Weekly summaries are useful for thesis-level storytelling because they reduce noise and highlight broader operating phases.
        - Trend direction should be interpreted alongside the Data Quality page because shorter histories naturally weaken certainty.
        """
    )
