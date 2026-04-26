"""Water and resource analytics page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.charts import (
    box_distribution_chart,
    histogram_chart,
    line_trend_chart,
    resource_activity_chart,
    stacked_quality_chart,
)
from utils.metrics import compute_daily_metrics, compute_quality_summary, compute_system_summary, format_num, format_pct
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_comparability_note,
    render_hero,
    render_metric_card,
)

context = build_page_context("Water & Resource Analytics")
df = context["df"]

render_hero(
    "Water & Resource Analytics",
    (
        "Investigate water demand, return-water behavior, nutrient activity, and pH adjustments over time. "
        "This page is designed to separate direct measurements from estimated or aggregate rows before drawing conclusions."
    ),
)

if df.empty:
    st.warning("No rows remain after the current filters. Expand the sidebar filters to continue.")
    st.stop()

render_comparability_note(context["comparability_note"])

water_df = df[df["analysis_ready_water_use_flag"] & df["water_use_l"].notna()].copy()
daily = compute_daily_metrics(df)
summary = compute_system_summary(df)
quality = compute_quality_summary(water_df if not water_df.empty else df)

metric_cards = [
    (
        "Analysis-ready water rows",
        f"{len(water_df):,}",
        "Rows suitable for water-use analytics in the current slice.",
    ),
    (
        "Average water use",
        format_num(water_df["water_use_l"].mean(), suffix=" L"),
        "Mean water use across analysis-ready observations.",
    ),
    (
        "Nutrient activity rate",
        format_pct(df["nutrient_addition_flag"].mean()),
        "Share of rows with nutrient additions.",
    ),
    (
        "pH adjustment rate",
        format_pct(df["ph_adjustment_flag"].mean()),
        "Share of rows with a recorded pH-down intervention.",
    ),
]

cols = st.columns(4, gap="medium")
for column, card in zip(cols, metric_cards):
    with column:
        render_metric_card(*card)

st.markdown("### Water use over time")
st.markdown(
    "<div class='section-caption'>Daily totals help show operational demand, while the rolling average smooths short-run noise and aggregate weekends.</div>",
    unsafe_allow_html=True,
)

trend_left, trend_right = st.columns(2, gap="large")
with trend_left:
    st.plotly_chart(
        line_trend_chart(
            daily,
            x="observation_date",
            y="daily_water_use_l",
            title="Daily water use by system",
            y_title="Liters",
        ),
        use_container_width=True,
    )
    render_chart_conclusion(
        "Daily water-use totals by greenhouse system.",
        "The chart reveals demand spikes and operating phases, but aggregate or estimated rows should be checked before treating spikes as physical events.",
    )
with trend_right:
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
    render_chart_conclusion(
        "A 7-day rolling water-use average by system.",
        "The rolling view smooths day-level noise and makes sustained shifts easier to separate from isolated records.",
    )

dist_left, dist_right = st.columns(2, gap="large")
with dist_left:
    st.plotly_chart(
        box_distribution_chart(
            water_df,
            x="system",
            y="water_use_l",
            title="Water-use distribution by system",
        ),
        use_container_width=True,
    )
    render_chart_conclusion(
        "The spread of analysis-ready water-use observations for each system.",
        "Wide boxes or many outliers point to variable operations, data issues, or genuine high-demand periods worth investigating.",
    )
with dist_right:
    st.plotly_chart(
        histogram_chart(
            water_df,
            x="water_use_l",
            color="system",
            title="Water-use density / histogram",
            bins=24,
        ),
        use_container_width=True,
    )
    render_chart_conclusion(
        "The frequency distribution of water-use values by system.",
        "Overlapping distributions suggest similar observed ranges; separated distributions suggest different operating scales or measurement bases.",
    )

st.markdown("### Return-water and addition patterns")
return_long = summary[
    ["system", "water_in_return_mean_l", "return_now_mean_l", "water_addition_duration_median_min"]
].melt(id_vars="system", var_name="metric", value_name="value")

return_labels = {
    "water_in_return_mean_l": "Average water in return (L)",
    "return_now_mean_l": "Average return now (L)",
    "water_addition_duration_median_min": "Median addition duration (min)",
}
return_long["metric"] = return_long["metric"].map(return_labels)

return_fig = px.bar(
    return_long,
    x="system",
    y="value",
    color="metric",
    barmode="group",
    title="Return-water behavior and addition duration",
)
return_fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.88)")
st.plotly_chart(return_fig, use_container_width=True)
render_chart_conclusion(
    "Average return-water levels and median water-addition duration by system.",
    "Return-water and duration patterns indicate how much operational effort and flow balance differ across systems.",
)

resource_left, resource_right = st.columns(2, gap="large")
with resource_left:
    st.plotly_chart(
        resource_activity_chart(
            daily,
            metric="daily_nutrient_ml",
            title="Nutrient additions over time",
            y_title="Total nutrient added (mL)",
        ),
        use_container_width=True,
    )
    render_chart_conclusion(
        "Daily nutrient addition quantities by system.",
        "Concentrated nutrient periods can explain cost, workload, and efficiency differences when quantity tracking is complete.",
    )
with resource_right:
    st.plotly_chart(
        resource_activity_chart(
            daily,
            metric="daily_ph_down_ml",
            title="pH-down activity over time",
            y_title="pH-down added (mL)",
        ),
        use_container_width=True,
    )
    render_chart_conclusion(
        "Daily pH-down activity by system.",
        "Frequent or high pH-down additions point to chemistry-management burden rather than water use alone.",
    )

st.markdown("### Measured vs estimated / aggregate context")
st.markdown(
    "<div class='section-caption'>Use this panel to distinguish direct measurement rows from estimates or bundled weekend observations before interpreting spikes or smoothness.</div>",
    unsafe_allow_html=True,
)
st.plotly_chart(
    stacked_quality_chart(quality["status_by_system"]),
    use_container_width=True,
)
render_chart_conclusion(
    "Data-quality composition for rows used in this resource view.",
    "Water conclusions are strongest when usable rows dominate and review, estimated, or aggregate rows are limited.",
)

with st.expander("Method note for this page", expanded=False):
    st.markdown(
        """
        - Water-use distributions rely on rows marked `analysis_ready_water_use_flag = True`.
        - Estimated and aggregate rows remain in view only if the sidebar toggles keep them included.
        - Hydroponic and soil systems use different water-use bases in the source data, so absolute efficiency comparisons remain directional.
        """
    )
