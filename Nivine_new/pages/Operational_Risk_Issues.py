"""Operational risk and issues page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.charts import (
    heatmap_chart,
    horizontal_ranking_chart,
    issue_timeline_chart,
    leak_coverage_chart,
    risk_treemap,
)
from utils.metrics import (
    compute_daily_metrics,
    compute_incident_heatmap,
    compute_leak_location_counts,
    compute_problem_category_counts,
    compute_system_summary,
    format_pct,
)
from utils.scoring import build_system_scorecard
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

context = build_page_context("Operational Risk & Issues")
df = context["df"]

render_hero(
    "Operational Risk & Issues",
    (
        "Surface the maintenance burden of each system using day-normalized leak frequency, issue-day frequency, "
        "observed leak severity, and manual intervention pressure."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

summary = compute_system_summary(df)
scorecard, _ = build_system_scorecard(
    summary, mixed_types=df["system_type"].nunique() > 1
)
daily = compute_daily_metrics(df)
problem_counts = compute_problem_category_counts(df)
leak_locations = compute_leak_location_counts(df)
issue_heatmap = compute_incident_heatmap(df, "issue_incident_flag")
leak_heatmap = compute_incident_heatmap(df, "leak_incident_flag")

cards = [
    (
        "Issue days / active day",
        format_pct(summary["issue_days_per_active_day"].mean()),
        "Average share of active days carrying at least one issue flag.",
    ),
    (
        "Manual days / active day",
        format_pct(summary["manual_days_per_active_day"].mean()),
        "Average share of active days requiring manual intervention.",
    ),
    (
        "Observed leak days / active day",
        format_pct(summary["leak_days_per_active_day"].mean()),
        "Lower-bound leak-day rate because missing leak status is not treated as no leak.",
    ),
    (
        "Low leak-coverage systems",
        f"{(summary['leak_reported_day_share'].fillna(0) < 0.5).sum()}",
        "Systems where leak evidence is too partial for a definitive low-risk interpretation.",
    ),
]

card_cols = st.columns(4, gap="medium")
for column, card in zip(card_cols, cards):
    with column:
        render_metric_card(*card)

st.markdown("### Risk summary by system")
summary_view = scorecard[
    [
        "system",
        "risk_score",
        "risk",
        "risk_breakdown",
        "confidence_label",
    ]
].rename(
    columns={
        "system": "System",
        "risk_score": "Risk score",
        "risk": "Risk band",
        "risk_breakdown": "Risk breakdown",
        "confidence_label": "Confidence",
    }
)
st.dataframe(summary_view, width="stretch", hide_index=True)

risk_left, risk_right = st.columns(2, gap="large")
with risk_left:
    leak_summary = summary[
        ["system", "leak_days_per_active_day", "leak_reported_day_share"]
    ].rename(
        columns={
            "leak_days_per_active_day": "leak_rate_observed",
            "leak_reported_day_share": "leak_reporting_coverage",
        }
    )
    st.plotly_chart(leak_coverage_chart(leak_summary), width="stretch")
    render_chart_conclusion(
        "Observed leak rate compared with leak-reporting coverage by system.",
        "Leak risk is only convincing when coverage is high; low coverage means the observed leak rate is a lower-bound estimate.",
    )
with risk_right:
    severity_df = (
        df.groupby(["system", "leak_severity"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    severity_fig = px.bar(
        severity_df,
        x="system",
        y="count",
        color="leak_severity",
        barmode="stack",
        title="Leak severity breakdown",
    )
    severity_fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
    )
    st.plotly_chart(severity_fig, width="stretch")
    render_chart_conclusion(
        "Leak records split by severity class for each system.",
        "Severity mix helps distinguish occasional minor events from systems with more serious water-loss risk.",
    )

rank_left, rank_right = st.columns(2, gap="large")
with rank_left:
    overall_problem_rank = (
        problem_counts.groupby("problem_category", as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=False)
    )
    st.plotly_chart(
        horizontal_ranking_chart(
            overall_problem_rank,
            category_col="problem_category",
            value_col="count",
            title="Most common problem categories",
            color="#DC2626",
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "The most frequent operational issue categories across the current filter scope.",
        "High-frequency categories should become the first checklist items for maintenance review.",
    )
with rank_right:
    overall_leak_rank = (
        leak_locations.groupby("leak_location", as_index=False)["count"]
        .sum()
        .sort_values("count", ascending=False)
    )
    st.plotly_chart(
        horizontal_ranking_chart(
            overall_leak_rank,
            category_col="leak_location",
            value_col="count",
            title="Most common leak locations",
            color="#2563EB",
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "The most common leak-location tokens among rows where leaks are reported.",
        "Repeated locations suggest targeted inspection points rather than broad, unfocused troubleshooting.",
    )

if not problem_counts.empty:
    st.plotly_chart(risk_treemap(problem_counts), width="stretch")
    render_chart_conclusion(
        "Operational issue composition nested by system and issue category.",
        "The treemap shows which systems and issue families dominate the risk narrative in one view.",
    )

timeline_left, timeline_right = st.columns(2, gap="large")
with timeline_left:
    st.plotly_chart(issue_timeline_chart(daily), width="stretch")
    render_chart_conclusion(
        "Issue and leak events through time by system.",
        "Clusters in the timeline point to operating periods that deserve root-cause review.",
    )
with timeline_right:
    issue_heatmap_fig = heatmap_chart(
        issue_heatmap,
        x="weekday_name",
        y="system",
        z="rate",
        title="Issue rate heatmap by weekday",
        color_scale="YlOrRd",
    )
    st.plotly_chart(issue_heatmap_fig, width="stretch")
    render_chart_conclusion(
        "Issue rates by weekday and system.",
        "Weekday concentration may indicate routine-driven problems, staffing patterns, or repeated observation timing.",
    )

st.markdown("### Leak timing heatmap")
st.plotly_chart(
    heatmap_chart(
        leak_heatmap,
        x="weekday_name",
        y="system",
        z="rate",
        title="Leak rate heatmap by weekday",
        color_scale="YlOrBr",
    ),
    width="stretch",
)
render_chart_conclusion(
    "Leak rates by weekday and system.",
    "Persistent weekday patterns are useful for scheduling inspections, but missing leak reporting can weaken this signal.",
)

with st.expander("Risk interpretation note", expanded=False):
    st.markdown(
        """
        - Risk is normalized by active day rather than by raw counts.
        - Leak burden is treated as an observed lower bound whenever leak status is not recorded on every active day.
        - Issue and manual intervention signals are often more complete than leak signals, so they should anchor the risk narrative when leak coverage is weak.
        """
    )
