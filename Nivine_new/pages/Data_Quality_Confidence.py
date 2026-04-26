"""Data quality and confidence page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.charts import (
    completeness_heatmap,
    confidence_band_chart,
    row_confidence_chart,
    stacked_quality_chart,
)
from utils.metrics import (
    build_trust_matrix,
    compute_quality_summary,
    compute_system_summary,
    format_pct,
)
from utils.scoring import build_system_scorecard
from utils.ui import (
    build_page_context,
    render_badge,
    render_callout,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

context = build_page_context("Data Quality & Confidence")
df = context["df"]

render_hero(
    "Data Quality & Confidence",
    (
        "Assess how much of the dashboard rests on strong evidence, where estimates or aggregate rows weaken interpretation, "
        "and which comparisons remain reliable, directional, or not yet reliable enough."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

quality = compute_quality_summary(df)
summary = compute_system_summary(df)
scorecard, _ = build_system_scorecard(
    summary, mixed_types=df["system_type"].nunique() > 1
)
trust_matrix = build_trust_matrix(df, summary, scorecard)

cards = [
    ("Usable rows", f"{df['usable_row_flag'].sum():,}", "Rows explicitly marked usable."),
    ("Aggregate rows", f"{df['weekend_or_aggregate_flag'].sum():,}", "Weekend or aggregate observations."),
    ("Estimated rows", f"{df['estimated_value_flag'].sum():,}", "Rows with estimated values."),
    ("Analysis-ready rows", f"{df['analysis_ready_water_use_flag'].sum():,}", "Rows marked analysis-ready for water use."),
    ("Imputed rows", f"{df['age_days_imputed'].sum():,}", "Rows carrying imputed age values."),
    ("Leak reporting coverage", format_pct(df["leak_reported_flag"].mean()), "Share of rows with explicit yes/no leak status."),
]

for start in range(0, len(cards), 3):
    columns = st.columns(3, gap="medium")
    for column, card in zip(columns, cards[start : start + 3]):
        with column:
            render_metric_card(*card)

st.markdown("### Confidence badges by system")
badge_cols = st.columns(len(scorecard), gap="small")
for column, (_, row) in zip(badge_cols, scorecard.iterrows()):
    with column:
        st.markdown(f"**{row['system']}**")
        tone = "good" if row["confidence_label"] == "Strong" else "warn" if row["confidence_label"] == "Moderate" else "risk"
        render_badge(f"{row['confidence_label']} confidence", tone=tone)

st.markdown("### Evidence structure")
quality_left, quality_right = st.columns(2, gap="large")
with quality_left:
    st.plotly_chart(
        stacked_quality_chart(quality["status_by_system"]),
        use_container_width=True,
    )
    render_chart_conclusion(
        "The composition of quality statuses by system.",
        "A system with many review-required, estimated, or aggregate rows should be interpreted more cautiously than one dominated by usable rows.",
    )
with quality_right:
    st.plotly_chart(row_confidence_chart(df), use_container_width=True)
    render_chart_conclusion(
        "The share of rows in each evidence-strength band.",
        "The selected slice supports stronger conclusions when strong evidence is the largest share.",
    )

st.markdown("### Missingness and completeness")
st.plotly_chart(
    completeness_heatmap(quality["completeness"]),
    use_container_width=True,
)
render_chart_conclusion(
    "Completeness of core analytical fields by system.",
    "Sparse fields identify where the data collection process must improve before a claim becomes defensible.",
)

st.markdown("### System-level confidence scoring")
st.plotly_chart(confidence_band_chart(scorecard), use_container_width=True)
render_chart_conclusion(
    "System-level confidence scores grouped by comparison strength.",
    "Confidence is not the same as performance; it tells you how much trust to place in each system's metrics.",
)

flag_long = summary[
    [
        "system",
        "analysis_ready_share",
        "estimated_share",
        "core_missing_share",
        "warning_share",
        "imputed_share",
    ]
].melt(id_vars="system", var_name="flag", value_name="share")
flag_labels = {
    "analysis_ready_share": "Analysis-ready share",
    "estimated_share": "Estimated share",
    "core_missing_share": "Core missing share",
    "warning_share": "Sanity warning share",
    "imputed_share": "Imputed share",
}
flag_long["flag"] = flag_long["flag"].map(flag_labels)
flag_fig = px.bar(
    flag_long,
    x="system",
    y="share",
    color="flag",
    barmode="group",
    title="Confidence framework inputs by system",
)
flag_fig.update_layout(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(255,255,255,0.88)",
)
st.plotly_chart(flag_fig, use_container_width=True)
render_chart_conclusion(
    "The quality-flag inputs behind the confidence framework.",
    "The confidence score falls when estimated rows, warning flags, missing core measures, or imputation become material.",
)

st.markdown("### Can we trust this?")
st.dataframe(trust_matrix, use_container_width=True, hide_index=True)

trust_left, trust_center, trust_right = st.columns(3, gap="medium")
trust_groups = {
    "Reliable": trust_left,
    "Directional only": trust_center,
    "Not reliable enough": trust_right,
}
for label, column in trust_groups.items():
    subset = trust_matrix[trust_matrix["Reliability"] == label]
    body = (
        " ".join(subset["Why"].tolist())
        if not subset.empty
        else f"No comparison areas currently fall into the '{label}' band."
    )
    tone = "default" if label == "Reliable" else "warning" if label == "Directional only" else "risk"
    with column:
        render_callout(label, body, tone=tone)

st.markdown("### Confidence explanations by system")
confidence_view = scorecard[
    [
        "system",
        "confidence_score",
        "confidence_label",
        "confidence_explanation",
        "efficiency_confidence",
        "efficiency_measurement_status",
        "efficiency_warning",
    ]
].rename(
    columns={
        "system": "System",
        "confidence_score": "Confidence score",
        "confidence_label": "Confidence",
        "confidence_explanation": "Why",
        "efficiency_confidence": "Efficiency confidence",
        "efficiency_measurement_status": "Efficiency basis",
        "efficiency_warning": "Efficiency warning",
    }
)
st.dataframe(confidence_view, use_container_width=True, hide_index=True)

with st.expander("Interpretation standards used on this page", expanded=False):
    st.markdown(
        """
        - **Reliable**: enough usable support exists to defend the comparison in front of a thesis committee.
        - **Directional only**: a pattern is visible, but uneven measurement or structural differences mean the comparison should guide follow-up rather than settle the question.
        - **Not reliable enough**: the data gap is large enough that the app should not promote a firm conclusion.
        """
    )
