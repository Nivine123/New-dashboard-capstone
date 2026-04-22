"""Trends over time page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.charts import line_trend_chart, weekly_multi_metric_chart
from utils.metrics import compute_daily_metrics, compute_weekly_metrics
from utils.ui import build_page_context, render_comparability_note, render_hero

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
    st.plotly_chart(activity_fig, use_container_width=True)
with top_right:
    st.plotly_chart(
        weekly_multi_metric_chart(
            weekly,
            metric="weekly_water_use_l",
            title="Weekly water-use trend",
            y_title="Liters per week",
        ),
        use_container_width=True,
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
        use_container_width=True,
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
    st.plotly_chart(issue_weekly_fig, use_container_width=True)

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
        use_container_width=True,
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
        use_container_width=True,
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
        use_container_width=True,
    )
with bottom_right:
    st.plotly_chart(
        weekly_multi_metric_chart(
            weekly,
            metric="rolling_4w_water_use_l",
            title="4-week smoothed water-use trend",
            y_title="Liters",
        ),
        use_container_width=True,
    )

with st.expander("Temporal analysis note", expanded=False):
    st.markdown(
        """
        - Daily charts preserve event timing but can still reflect weekend aggregation if those rows are included.
        - Weekly summaries are useful for thesis-level storytelling because they reduce noise and highlight broader operating phases.
        - Trend direction should be interpreted alongside the Data Quality page because shorter histories naturally weaken certainty.
        """
    )
