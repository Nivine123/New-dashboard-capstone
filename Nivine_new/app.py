"""Executive overview page for the greenhouse thesis dashboard."""

from __future__ import annotations

import streamlit as st

from utils.charts import risk_confidence_scatter, score_bar_chart
from utils.metrics import (
    build_trust_matrix,
    compute_overview_metrics,
    compute_system_summary,
    format_num,
    format_pct,
)
from utils.recommendations import (
    build_decision_summary,
    build_dimension_confidence_summary,
    build_dashboard_tells_us,
    build_executive_summary,
    build_key_cautions,
    build_key_findings,
)
from utils.scoring import build_system_scorecard
from utils.ui import (
    build_page_context,
    render_badge,
    render_callout,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

context = build_page_context("Executive Overview")
df = context["df"]

render_hero(
    "Greenhouse Systems Operational Intelligence Dashboard",
    (
        "A thesis-grade decision-support platform for evaluating greenhouse system performance, "
        "resource behavior, operational burden, and evidence strength using the cleaned greenhouse observation log."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

overview = compute_overview_metrics(df)
summary = compute_system_summary(df)
scorecard, _ = build_system_scorecard(
    summary, mixed_types=df["system_type"].nunique() > 1
)
trust_matrix = build_trust_matrix(df, summary, scorecard)
findings = build_key_findings(
    scorecard, summary, context["comparability_note"], include_caution=False
)
decision_summary = build_decision_summary(
    scorecard, summary, context["comparability_note"]
)
efficiency_row = scorecard.sort_values("efficiency_score", ascending=False).iloc[0]
dimension_confidence = build_dimension_confidence_summary(trust_matrix)

st.markdown("### Project framing")
st.markdown(
    "<div class='section-caption'>The dashboard combines operational analytics, business interpretation, and data-quality discipline so the conclusions are presentation-ready for a thesis defense and realistic for executive use.</div>",
    unsafe_allow_html=True,
)

left, right = st.columns([1.2, 1], gap="large")
with left:
    st.markdown(
        """
        **Research / business objective**

        Evaluate which greenhouse system shows the strongest operational profile under the observed conditions, identify where resource efficiency and stability diverge, and separate strong evidence from weaker directional signals before recommending action.
        """
    )
with right:
    st.markdown(
        f"""
        **Current scope**

        The active slice contains **{overview['total_observations']} observations**, spanning **{overview['active_date_range']}**, across **{overview['system_count']} greenhouse systems**.
        """
    )

metric_items = [
    ("Total observations", f"{overview['total_observations']:,}", "Rows currently in scope after sidebar filtering."),
    ("Active date range", overview["active_date_range"], "Earliest to latest observation in the filtered slice."),
    ("Greenhouse systems", f"{overview['system_count']}", "Distinct systems represented in the current selection."),
    ("Average water use", format_num(overview["average_water_use_l"], suffix=" L"), "Mean observed water use where the metric is available."),
    ("Leak incidence rate", format_pct(overview["leak_incidence_rate"]), "Calculated only on rows where leak status was explicitly reported."),
    ("Issue incidence rate", format_pct(overview["issue_incidence_rate"]), "Share of rows with recorded operational issues."),
    ("Average plant count", format_num(overview["average_plant_count"]), "Average recorded plant count in the current slice."),
    ("Rows marked usable", f"{overview['rows_marked_usable']:,}", "Rows classified as usable in the cleaned dataset."),
    ("% analysis-ready rows", format_pct(overview["analysis_ready_share"]), "Rows marked ready for water-use analysis."),
    ("% warnings / estimated", format_pct(overview["warning_or_estimated_share"]), "Rows carrying an estimate or sanity warning flag."),
]

for row_start in range(0, len(metric_items), 5):
    columns = st.columns(5, gap="medium")
    for column, item in zip(columns, metric_items[row_start : row_start + 5]):
        with column:
            render_metric_card(*item)

st.markdown("### System comparison snapshot")
st.markdown(
    "<div class='section-caption'>These views condense the relative balance of efficiency, risk, stability, workload, and evidence quality before you drill into the dedicated pages.</div>",
    unsafe_allow_html=True,
)

chart_left, chart_right = st.columns(2, gap="large")
with chart_left:
    st.plotly_chart(score_bar_chart(scorecard), use_container_width=True)
with chart_right:
    st.plotly_chart(risk_confidence_scatter(scorecard), use_container_width=True)

st.markdown("### Top findings")
badge_left, badge_mid, badge_right, badge_far = st.columns(4, gap="small")
with badge_left:
    render_badge(
        f"Efficiency confidence: {dimension_confidence['efficiency']}",
        tone="risk"
        if dimension_confidence["efficiency"] == "Not reliable enough"
        else "warn"
        if dimension_confidence["efficiency"] == "Directional only"
        else "good",
    )
with badge_mid:
    render_badge(
        f"Stability confidence: {dimension_confidence['stability']}",
        tone="risk"
        if dimension_confidence["stability"] == "Not reliable enough"
        else "warn"
        if dimension_confidence["stability"] == "Directional only"
        else "good",
    )
with badge_right:
    render_badge(
        f"Risk confidence: {dimension_confidence['risk']}",
        tone="risk"
        if dimension_confidence["risk"] == "Not reliable enough"
        else "warn"
        if dimension_confidence["risk"] == "Directional only"
        else "good",
    )
with badge_far:
    render_badge(
        f"Overall read: {dimension_confidence['overall']}",
        tone="warn"
        if dimension_confidence["overall"] in {"Mixed", "Moderate", "Dimension-dependent"}
        else "good",
    )

finding_columns = st.columns(min(4, len(findings) or 1), gap="medium")
for column, finding in zip(finding_columns, findings):
    with column:
        tone = "risk" if "burden" in finding["title"].lower() else "warning" if "caution" in finding["title"].lower() else "default"
        render_callout(finding["title"], finding["body"], tone=tone)

st.markdown("### Risk and confidence callouts")
callout_left, callout_right = st.columns(2, gap="large")

with callout_left:
    low_leak_systems = summary.loc[
        summary["leak_reported_day_share"].fillna(0) < 0.5, "system"
    ].astype(str)
    leak_gap_text = (
        f"Leak comparisons are weakest for {', '.join(low_leak_systems.tolist())} because leak status is often missing."
        if not low_leak_systems.empty
        else "Leak coverage is generally usable within the current filter scope."
    )
    render_callout(
        "Operational risk lens",
        (
            "Issue frequency and manual intervention are observable across the dataset, "
            "but leak risk must be read together with leak-reporting coverage. "
            f"{leak_gap_text}"
        ),
        tone="risk",
    )

with callout_right:
    strong_areas = trust_matrix[trust_matrix["Reliability"] == "Reliable"][
        "Dimension"
    ].tolist()
    weak_areas = trust_matrix[trust_matrix["Reliability"] == "Not reliable enough"][
        "Dimension"
    ].tolist()
    confidence_text = (
        f"Strongest comparison areas: {', '.join(strong_areas)}. "
        if strong_areas
        else "No area reaches strong-comparison status in the current slice. "
    )
    if weak_areas:
        confidence_text += f"Weakest areas: {', '.join(weak_areas)}."
    render_callout(
        "Confidence lens",
        (
            f"Evidence strength is dimension-dependent. Stability is {dimension_confidence['stability'].lower()}, "
            f"operational risk is {dimension_confidence['risk'].lower()}, and efficiency is {dimension_confidence['efficiency'].lower()}. "
            + confidence_text
        ),
        tone="warning",
    )

st.markdown("### Executive summary")
st.write(
    build_executive_summary(
        overview, scorecard, summary, trust_matrix, context["comparability_note"]
    )
)

st.markdown("### Can we trust this?")
st.dataframe(trust_matrix, use_container_width=True, hide_index=True)

summary_left, summary_right = st.columns(2, gap="large")
with summary_left:
    st.markdown("#### What this dashboard tells us")
    tells_us = build_dashboard_tells_us(
        scorecard, summary, trust_matrix, context["comparability_note"]
    )
    st.markdown("\n".join(f"- {item}" for item in tells_us))

with summary_right:
    st.markdown("#### Key cautions before interpreting results")
    cautions = build_key_cautions(summary, trust_matrix)
    st.markdown("\n".join(f"- {item}" for item in cautions))

st.markdown("### Decision-support takeaway")
st.markdown(
    f"""
    - **Efficiency:** {decision_summary['efficiency_takeaway']}
    - **Stability:** {decision_summary['stability_takeaway']}
    - **Operational Risk:** {decision_summary['risk_takeaway']}
    - **Most Reliable Insight:** {decision_summary['most_reliable_insight']}
    - **Not Yet Defensible:** {decision_summary['not_yet_defensible']}
    """
)
