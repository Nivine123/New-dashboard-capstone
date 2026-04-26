"""System comparison page."""

from __future__ import annotations

import streamlit as st

from utils.charts import (
    risk_confidence_scatter,
    score_bar_chart,
    score_radar_chart,
    system_score_heatmap,
)
from utils.metrics import build_trust_matrix, compute_system_summary, format_num, format_pct
from utils.scoring import build_system_scorecard
from utils.ui import (
    build_page_context,
    render_badge,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

context = build_page_context("System Comparison")
df = context["df"]

render_hero(
    "System Comparison",
    (
        "Compare greenhouse systems using day-normalized efficiency, stability, risk, workload, and confidence metrics. "
        "The comparison is intentionally confidence-aware so weak evidence is shown as weak evidence rather than as a clean rank."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

summary = compute_system_summary(df)
scorecard, components = build_system_scorecard(
    summary, mixed_types=df["system_type"].nunique() > 1
)
trust_matrix = build_trust_matrix(df, summary, scorecard)

best_efficiency = scorecard.sort_values("efficiency_score", ascending=False).iloc[0]
best_stability = scorecard.sort_values("stability_score", ascending=False).iloc[0]
highest_risk = scorecard.sort_values("risk_score", ascending=False).iloc[0]
highest_confidence = scorecard.sort_values("confidence_score", ascending=False).iloc[0]

top_cards = [
    (
        "Apparent efficiency leader",
        str(best_efficiency["system"]),
        f"Score {best_efficiency['efficiency_score']:.0f}. {best_efficiency['efficiency_measurement_status']} with {best_efficiency['efficiency_label'].lower()}.",
    ),
    (
        "Best stability signal",
        str(best_stability["system"]),
        f"Score {best_stability['stability_score']:.0f}. {best_stability['stability_explanation']}",
    ),
    (
        "Highest operational risk",
        str(highest_risk["system"]),
        f"Risk score {highest_risk['risk_score']:.0f}. {highest_risk['risk_breakdown']}",
    ),
    (
        "Strongest evidence base",
        str(highest_confidence["system"]),
        f"Confidence score {highest_confidence['confidence_score']:.0f}. {highest_confidence['confidence_explanation']}",
    ),
]

card_cols = st.columns(4, gap="medium")
for column, card in zip(card_cols, top_cards):
    with column:
        render_metric_card(*card)

st.markdown("### Comparison badges")
badge_cols = st.columns(len(scorecard), gap="small")
for column, (_, row) in zip(badge_cols, scorecard.iterrows()):
    with column:
        tone = (
            "risk"
            if row["efficiency_measurement_status"] == "Unsupported efficiency"
            else "warn"
            if row["efficiency_measurement_status"] == "Estimated efficiency"
            else "good"
        )
        st.markdown(f"**{row['system']}**")
        render_badge(row["warning_badge"], tone=tone)

st.markdown("### Rebuilt system comparison table")
st.markdown(
    "<div class='section-caption'>All core burden metrics are normalized by active days. Efficiency is split from efficiency confidence so missing nutrient data reduces trust rather than falsely improving the score.</div>",
    unsafe_allow_html=True,
)

comparison_table = scorecard[
    [
        "system",
        "system_type",
        "efficiency_score",
        "efficiency_confidence",
        "efficiency_label",
        "efficiency_measurement_status",
        "stability_score",
        "stability",
        "risk_score",
        "risk",
        "workload_score",
        "workload",
        "confidence_score",
        "confidence_label",
        "analytical_readout",
    ]
].copy()

comparison_table = comparison_table.rename(
    columns={
        "system": "System",
        "system_type": "System type",
        "efficiency_score": "Efficiency score",
        "efficiency_confidence": "Efficiency confidence",
        "efficiency_label": "Efficiency reliability",
        "efficiency_measurement_status": "Efficiency basis",
        "stability_score": "Stability score",
        "stability": "Stability",
        "risk_score": "Risk score",
        "risk": "Risk",
        "workload_score": "Workload score",
        "workload": "Workload",
        "confidence_score": "Confidence score",
        "confidence_label": "Confidence",
        "analytical_readout": "Analytical readout",
    }
)

st.dataframe(
    comparison_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Efficiency score": st.column_config.NumberColumn(
            format="%.1f",
            help="Composite of water per active day, nutrient per active day when measured, intervention burden, and stability. Missing nutrient data is not treated as zero.",
        ),
        "Efficiency confidence": st.column_config.NumberColumn(
            format="%.1f",
            help="Confidence in the efficiency score itself, driven mainly by water coverage and nutrient quantity capture.",
        ),
        "Stability score": st.column_config.NumberColumn(
            format="%.1f",
            help="Uses coefficient of variation, rolling variance, day-to-day change consistency, and clean day-level support.",
        ),
        "Risk score": st.column_config.NumberColumn(
            format="%.1f",
            help="Composite of issue-day frequency, leak-day frequency, leak severity, and manual intervention burden, all normalized per active day.",
        ),
        "Workload score": st.column_config.NumberColumn(
            format="%.1f",
            help="Operational burden score based on manual intervention days, manual watering days, nutrient-addition days, and water-addition duration per day.",
        ),
        "Confidence score": st.column_config.NumberColumn(
            format="%.1f",
            help="System-level confidence based on analysis-ready coverage, estimated values, missing core measures, warning flags, and imputed values.",
        ),
        "Analytical readout": st.column_config.TextColumn(width="large"),
    },
)

warning_rows = scorecard[
    scorecard["efficiency_measurement_status"] != "Measured efficiency"
][["system", "efficiency_warning"]]
if not warning_rows.empty:
    st.markdown("### Efficiency warnings")
    for _, row in warning_rows.iterrows():
        st.warning(f"{row['system']}: {row['efficiency_warning']}")

viz_left, viz_right = st.columns(2, gap="large")

with viz_left:
    fig1 = score_bar_chart(scorecard)
    fig1.update_layout(title="Multi-Dimensional System Performance Comparison")
    st.plotly_chart(fig1, use_container_width=True)
    render_chart_conclusion(
        "The main comparison dimensions for each system on a common 0-100 score scale.",
        "No single bar should decide the winner; the most defensible choice depends on whether efficiency, stability, risk, or confidence matters most.",
    )

with viz_right:
    fig2 = risk_confidence_scatter(scorecard)
    fig2.update_layout(title="Risk vs Confidence: Reliability-Aware System Evaluation")
    st.plotly_chart(fig2, use_container_width=True)
    render_chart_conclusion(
        "Operational risk plotted against evidence confidence, with observation volume shown by marker size.",
        "High-risk systems with moderate or strong confidence are priority review targets because the evidence is strong enough to act on.",
    )

profile_left, profile_right = st.columns(2, gap="large")
with profile_left:
    st.plotly_chart(score_radar_chart(scorecard), use_container_width=True)
    render_chart_conclusion(
        "Each system's shape across efficiency, stability, risk, workload, and confidence.",
        "The radar view makes trade-offs visible: a system can be efficient but still carry workload or risk pressure.",
    )
with profile_right:
    st.plotly_chart(system_score_heatmap(scorecard), use_container_width=True)
    render_chart_conclusion(
        "A dense score matrix for quickly scanning high and low dimensions by system.",
        "The heatmap is useful for presentation because it turns the scorecard into an immediate strengths-and-risks map.",
    )
    
st.markdown("### Can we trust this?")
st.dataframe(trust_matrix, use_container_width=True, hide_index=True)

with st.expander("How the scoring works", expanded=False):
    st.markdown(
        """
        **Scoring design principles**

        - `compute_efficiency()`: combines water use per active day, nutrient use per active day when measured, manual intervention burden, and stability. Missing nutrient quantities reduce efficiency confidence instead of being treated as zero.
        - `compute_stability()`: combines coefficient of variation, rolling variance, day-to-day change consistency, and the number of clean daily observations left after excluding aggregate and estimated rows.
        - `compute_risk()`: combines issue-day frequency, leak-day frequency, observed leak severity, and manual intervention days, all normalized by active day.
        - `compute_confidence()`: uses `% analysis_ready_water_use_flag`, `% estimated_value_flag`, `% core_measurement_missing`, `% sanity_warning_flag`, and `% imputed values`.

        **Interpretation note**

        Efficiency is the weakest conclusion whenever nutrient measurement is incomplete or the filter scope mixes hydroponic and soil systems. Stability is usually the cleanest comparative signal because it depends on direct daily water behavior rather than on cross-system nutrient bookkeeping.
        """
    )

    component_view = components[
        [
            "system",
            "observations_per_active_day",
            "water_use_per_active_day_l",
            "water_use_per_observation_l",
            "issue_days_per_active_day",
            "manual_days_per_active_day",
            "leak_days_per_active_day",
            "leak_reported_day_share",
            "nutrient_quantity_capture_rate",
            "efficiency_confidence",
            "stability_score",
            "risk_score",
            "confidence_score",
        ]
    ].copy()

    component_view = component_view.rename(
        columns={
            "system": "System",
            "observations_per_active_day": "Observations / active day",
            "water_use_per_active_day_l": "Water use / active day (L)",
            "water_use_per_observation_l": "Water use / observation (L)",
            "issue_days_per_active_day": "Issue days / active day",
            "manual_days_per_active_day": "Manual days / active day",
            "leak_days_per_active_day": "Leak days / active day",
            "leak_reported_day_share": "Leak reporting day share",
            "nutrient_quantity_capture_rate": "Nutrient quantity capture",
            "efficiency_confidence": "Efficiency confidence",
            "stability_score": "Stability score",
            "risk_score": "Risk score",
            "confidence_score": "Confidence score",
        }
    )
    st.dataframe(component_view, use_container_width=True, hide_index=True)

st.markdown("### Confidence-aware interpretation")
st.markdown(
    f"""
    - **Apparent efficiency:** {best_efficiency['system']} currently leads the apparent efficiency score, but the result is classified as **{best_efficiency['efficiency_measurement_status']}** with **{best_efficiency['efficiency_label']}**.
    - **Most stable system:** {best_stability['system']} is the strongest stability signal because {best_stability['stability_explanation'].lower()}
    - **Risk priority:** {highest_risk['system']} should be the first operational review target because {highest_risk['risk_breakdown'].lower()}
    - **Most defensible comparison:** {highest_confidence['system']} has the strongest overall confidence base under the current filter scope.
    """
)
