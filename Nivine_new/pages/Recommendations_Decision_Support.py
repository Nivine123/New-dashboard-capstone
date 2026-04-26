"""Recommendations and decision support page."""

from __future__ import annotations

import plotly.express as px
import streamlit as st

from utils.charts import risk_confidence_scatter, score_bar_chart
from utils.metrics import build_trust_matrix, compute_system_summary
from utils.recommendations import (
    build_decision_summary,
    build_key_findings,
    generate_recommendation_table,
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

context = build_page_context("Recommendations & Decision Support")
df = context["df"]

render_hero(
    "Recommendations & Decision Support",
    (
        "Convert the analytical evidence into practical next steps for greenhouse operations, monitoring, and future decision-making. "
        "Recommendations are deliberately confidence-aware and written to survive thesis-defense scrutiny."
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
trust_matrix = build_trust_matrix(df, summary, scorecard)
recommendations = generate_recommendation_table(scorecard, summary, trust_matrix)
decision_summary = build_decision_summary(
    scorecard, summary, context["comparability_note"]
)
findings = build_key_findings(scorecard, summary, context["comparability_note"])

decision_cards = [
    (
        "Best system for efficiency",
        decision_summary["best_efficiency"],
        "Read as an apparent efficiency signal, not as a settled conclusion when nutrient data is incomplete.",
    ),
    (
        "Best system for stability",
        decision_summary["best_stability"],
        "The strongest operational consistency signal in the current slice.",
    ),
    (
        "Highest operational risk",
        decision_summary["highest_operational_risk"],
        "The system that should receive the strongest operational attention first.",
    ),
]

card_cols = st.columns(3, gap="medium")
for column, card in zip(card_cols, decision_cards):
    with column:
        render_metric_card(*card)

st.markdown("### Confidence badges")
badge_cols = st.columns(len(scorecard), gap="small")
for column, (_, row) in zip(badge_cols, scorecard.iterrows()):
    with column:
        st.markdown(f"**{row['system']}**")
        tone = "risk" if row["confidence_label"] == "Weak" else "warn" if row["efficiency_measurement_status"] != "Measured efficiency" else "good"
        render_badge(row["warning_badge"], tone=tone)

st.markdown("### Top strategic findings")
finding_cols = st.columns(min(4, len(findings) or 1), gap="medium")
for column, finding in zip(finding_cols, findings):
    with column:
        tone = (
            "risk"
            if "risk" in finding["title"].lower() or "burden" in finding["title"].lower()
            else "warning"
            if "caution" in finding["title"].lower() or "efficiency" in finding["title"].lower()
            else "default"
        )
        render_callout(finding["title"], finding["body"], tone=tone)

st.markdown("### Decision charts")
chart_left, chart_right = st.columns(2, gap="large")
with chart_left:
    decision_fig = score_bar_chart(scorecard)
    decision_fig.update_layout(title="Decision dimensions by system")
    st.plotly_chart(decision_fig, width="stretch")
    render_chart_conclusion(
        "The same decision dimensions used to generate the recommendations.",
        "Recommendations are strongest when the score pattern and evidence confidence point in the same direction.",
    )
with chart_right:
    risk_fig = risk_confidence_scatter(scorecard)
    risk_fig.update_layout(title="Action priority: risk versus confidence")
    st.plotly_chart(risk_fig, width="stretch")
    render_chart_conclusion(
        "Which systems combine operational risk with enough confidence to justify action.",
        "The best first actions target visible risk where the data quality is strong enough to support intervention.",
    )

st.markdown("### Recommendation table")
st.dataframe(recommendations, width="stretch", hide_index=True)

if not recommendations.empty and "Confidence level" in recommendations.columns:
    rec_counts = (
        recommendations.groupby("Confidence level", as_index=False)
        .size()
        .rename(columns={"size": "recommendations"})
    )
    rec_fig = px.pie(
        rec_counts,
        names="Confidence level",
        values="recommendations",
        hole=0.45,
        title="Recommendation confidence mix",
        color="Confidence level",
        color_discrete_map={"High": "#2563EB", "Moderate": "#D97706", "Low": "#DC2626"},
    )
    rec_fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(rec_fig, width="stretch")
    render_chart_conclusion(
        "The recommendation list grouped by confidence level.",
        "A recommendation portfolio with more high-confidence items is safer to act on immediately; moderate items are better for follow-up validation.",
    )

st.markdown("### Can we trust this before acting?")
st.dataframe(trust_matrix, width="stretch", hide_index=True)

st.markdown("### System-specific recommendations")
system_cols = st.columns(len(summary), gap="medium")
for column, (_, row) in zip(system_cols, scorecard.iterrows()):
    with column:
        if row["risk_score"] >= 67:
            action = "Immediate operational remediation and root-cause analysis."
            tone = "risk"
        elif row["efficiency_measurement_status"] == "Unsupported efficiency":
            action = "Do not scale based on efficiency yet; first close the nutrient-measurement gap."
            tone = "warning"
        elif row["stability_score"] >= 67:
            action = "Use this system as a stability benchmark and process-control reference."
            tone = "default"
        else:
            action = "Monitor closely and improve logging before drawing stronger conclusions."
            tone = "warning"
        render_callout(str(row["system"]), action, tone=tone)

st.markdown("### Final decision-support summary")
st.markdown(
    f"""
    - **Most reliable conclusion:** {decision_summary['most_reliable_conclusion']}
    - **What should NOT be concluded yet:** {decision_summary['what_not_to_conclude']}
    - **What should be validated before a real business decision:** {decision_summary['validate_before_decision']}
    """
)

with st.expander("Decision-support methodology", expanded=False):
    st.markdown(
        """
        - Efficiency recommendations are confidence-gated. A system can lead the apparent efficiency score without being promoted as the definitive efficiency winner.
        - Stability is prioritized more heavily in final decision support when efficiency inputs are only partially measured.
        - Risk recommendations use day-normalized issue, leak, and intervention burden rather than raw counts.
        """
    )
