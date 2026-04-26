"""Methodology and Capstone notes page."""

from __future__ import annotations

import streamlit as st

from utils.charts import pipeline_flow_chart
from utils.data_loader import load_cleaning_outputs
from utils.metrics import compute_system_summary
from utils.scoring import build_system_scorecard
from utils.ui import build_page_context, render_chart_conclusion, render_hero

context = build_page_context("Methodology / Thesis Notes")
df = context["df"]

render_hero(
    "Methodology / Thesis Notes",
    (
        "A thesis-appendix style summary of objective, preprocessing assumptions, metric definitions, scoring logic, "
        "limitations, and interpretation cautions used throughout the upgraded decision-grade dashboard."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

summary = compute_system_summary(df)
scorecard, _ = build_system_scorecard(
    summary, mixed_types=df["system_type"].nunique() > 1
)
artifacts = load_cleaning_outputs()
frames = artifacts["frames"]
metadata = artifacts["metadata"]

st.markdown("### Project objective")
st.markdown(
    """
    The dashboard is designed to answer six central questions:

    1. Which greenhouse system performs best operationally?
    2. Which system appears most resource-efficient?
    3. Which system shows the most stable behavior over time?
    4. Which system carries the greatest operational risk?
    5. Which findings are strongly supported versus weakened by data quality?
    6. What should decision-makers do next?
    """
)

st.markdown("### Dataset description")
st.markdown(
    f"""
    - Current filtered slice: **{len(df):,} rows**
    - Systems in scope: **{df['system'].nunique()}**
    - System types represented: **{', '.join(sorted(df['system_type'].unique().tolist()))}**
    - Observation window in scope: **{df['observation_date'].min():%Y-%m-%d} to {df['observation_date'].max():%Y-%m-%d}**
    - Source file used by the app: **{context['dataset_path'].name}**
    """
)

st.markdown("### Cleaning pipeline diagram")
st.plotly_chart(
    pipeline_flow_chart(
        cleaned_rows=len(context["source_df"]),
        validation_rows=len(frames.get("validation_report", [])),
        quality_rows=len(frames.get("data_quality_summary", [])),
        review_rows=len(frames.get("rows_needing_review", [])),
        dictionary_rows=len(frames.get("data_dictionary", [])),
        has_metadata=bool(metadata),
    ),
    width="stretch",
)
render_chart_conclusion(
    "The cleaning workflow from raw workbook through notebook artifacts into the deployed dashboard.",
    "The methodology is reproducible because the dashboard reads the notebook's cleaned outputs rather than changing the original raw file.",
)

with st.expander("Preprocessing assumptions", expanded=True):
    st.markdown(
        """
        - The app parses `observation_date` and `observation_timestamp` into analysis-ready datetime fields.
        - Boolean-like operational flags are normalized into `True` / `False`.
        - Numeric operational measures are coerced safely, with invalid values treated as missing.
        - Nutrient quantities are unified into `nutrient_effective_ml` by taking the generic total when present, then falling back to generic A/B quantities, then to system-specific gutters/tower/NFT quantities.
        - pH quantities are unified into `ph_down_effective_ml` in the same way.
        - Mixed categorical fields such as `crop_types`, `problem_categories`, and `leak_locations` are tokenized on commas and semicolons.
        - A row-level confidence band is derived from the original quality status plus flags for aggregate, estimated, missing-core, and warning conditions.
        """
    )

with st.expander("Metric definitions", expanded=False):
    st.markdown(
        """
        - **Efficiency score**: composite of water use per active day, nutrient use per active day when measured, manual intervention burden, and stability.
        - **Efficiency confidence**: separate from the efficiency score itself and driven by water coverage, nutrient quantity capture, estimated rows, and aggregate rows.
        - **Stability score**: coefficient of variation, rolling variance ratio, day-to-day change consistency, and clean day-level support after excluding aggregate and estimated rows.
        - **Risk score**: issue-day frequency, leak-day frequency, observed leak severity, and manual intervention days, all normalized by active day.
        - **Workload score**: manual intervention days, manual watering days, nutrient-addition days, and water-addition duration burden.
        - **Confidence score**: `% analysis_ready_water_use_flag`, `% estimated_value_flag`, `% core_measurement_missing`, `% sanity_warning_flag`, and `% imputed values`.
        """
    )

with st.expander("Normalization rules", expanded=False):
    st.markdown(
        """
        - Water, issue, leak, and intervention metrics are normalized by **active days** rather than raw totals.
        - Observation-normalized values are also preserved where useful, but the dashboard avoids ranking systems on raw counts.
        - Leak burden is treated as an observed lower bound when leak reporting is incomplete; missing leak status is not interpreted as no leak.
        """
    )

with st.expander("Scoring methodology", expanded=False):
    st.markdown(
        """
        - Scores are normalized on a 0-100 scale across the currently filtered systems.
        - Missing or non-applicable components are omitted rather than replaced with artificial zeroes.
        - Efficiency does **not** treat missing nutrient quantities as zero. Instead, missing nutrient quantity tracking lowers efficiency confidence and can move the result into estimated or unsupported status.
        - Final conclusions are written with confidence-aware language so the dashboard does not overstate weak comparisons.
        """
    )

with st.expander("Limitations", expanded=False):
    st.markdown(
        """
        - The dataset compares hydroponic and soil systems, which are not directly equivalent in operating model or water-use basis.
        - Soil-system nutrient quantities are not fully tracked, which weakens cross-system efficiency claims.
        - Plant-level metadata is sparse for some systems, especially in plant name and growth stage fields.
        - Leak risk cannot be fully assessed when leak reporting is incomplete.
        - Aggregate weekend rows reduce day-level precision for trend and stability analysis.
        - The dashboard is descriptive and decision-support oriented; it does not claim causal inference.
        """
    )

with st.expander("Interpretation cautions", expanded=False):
    st.markdown(
        """
        - Treat cross-type efficiency rankings as directional unless the systems are measured under harmonized conditions.
        - Avoid per-plant performance claims when plant-count coverage is inconsistent.
        - Use the Data Quality & Confidence page before drawing strong comparative conclusions from any single chart.
        - A system can appear low-risk simply because some risk fields are weakly captured, not because the system is definitively better.
        """
    )

st.markdown("### System evidence snapshot")
st.dataframe(
    scorecard[
        [
            "system",
            "system_type",
            "observations",
            "active_days",
            "efficiency_score",
            "efficiency_confidence",
            "efficiency_measurement_status",
            "stability_score",
            "risk_score",
            "confidence_score",
            "confidence_label",
        ]
    ],
    width="stretch",
    hide_index=True,
)
