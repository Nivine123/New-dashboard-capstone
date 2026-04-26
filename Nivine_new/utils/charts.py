"""Reusable Plotly chart builders."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.constants import (
    ASSESSMENT_COLORS,
    QUALITY_ORDER,
    ROW_CONFIDENCE_COLORS,
    SYSTEM_COLORS,
    WEEKDAY_ORDER,
)


def _base_layout(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        margin=dict(l=18, r=18, t=56, b=24),
        font=dict(family="Inter, Aptos, Segoe UI, sans-serif", color="#0F172A", size=13),
        legend_title_text="",
        title=dict(
            x=0.01,
            xanchor="left",
            font=dict(size=17, family="Inter, Aptos, Segoe UI, sans-serif", color="#0F172A"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor="rgba(255,255,255,0.0)",
        ),
        hoverlabel=dict(
            bgcolor="#ffffff",
            bordercolor="#CBD5E1",
            font=dict(color="#0F172A", size=12),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#E2E8F0",
        tickcolor="#CBD5E1",
        ticks="outside",
        title_font=dict(size=12, color="#64748B"),
    )
    fig.update_yaxes(
        gridcolor="#E2E8F0",
        zeroline=False,
        showline=True,
        linecolor="#E2E8F0",
        tickcolor="#CBD5E1",
        ticks="outside",
        title_font=dict(size=12, color="#64748B"),
    )
    return fig


def score_bar_chart(scorecard: pd.DataFrame) -> go.Figure:
    score_long = scorecard.melt(
        id_vars=["system"],
        value_vars=[
            "efficiency_score",
            "risk_score",
            "stability_score",
            "workload_score",
            "confidence_score",
        ],
        var_name="dimension",
        value_name="score",
    )
    dimension_labels = {
        "efficiency_score": "Efficiency",
        "risk_score": "Risk",
        "stability_score": "Stability",
        "workload_score": "Workload",
        "confidence_score": "Confidence",
    }
    score_long["dimension"] = score_long["dimension"].map(dimension_labels)
    fig = px.bar(
        score_long,
        x="dimension",
        y="score",
        color="system",
        barmode="group",
        color_discrete_map=SYSTEM_COLORS,
        text_auto=".0f",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_title="Score (0-100)")
    return _base_layout(fig, height=420)


def risk_confidence_scatter(scorecard: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        scorecard,
        x="risk_score",
        y="confidence_score",
        size="observations",
        color="system",
        hover_data={
            "efficiency_score": ":.1f",
            "stability_score": ":.1f",
            "workload_score": ":.1f",
            "observations": True,
        },
        color_discrete_map=SYSTEM_COLORS,
    )
    fig.update_layout(
        xaxis_title="Operational risk score",
        yaxis_title="Confidence score",
    )
    return _base_layout(fig, height=420)


def line_trend_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    y_title: str,
    rolling: bool = False,
) -> go.Figure:
    fig = px.line(
        df,
        x=x,
        y=y,
        color="system",
        color_discrete_map=SYSTEM_COLORS,
        markers=not rolling,
    )
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title="")
    return _base_layout(fig, height=400)


def box_distribution_chart(df: pd.DataFrame, x: str, y: str, title: str) -> go.Figure:
    fig = px.box(
        df,
        x=x,
        y=y,
        color=x,
        color_discrete_map=SYSTEM_COLORS,
        points="outliers",
    )
    fig.update_layout(title=title, xaxis_title="", yaxis_title="")
    fig.update_traces(quartilemethod="inclusive")
    return _base_layout(fig, height=400)


def histogram_chart(df: pd.DataFrame, x: str, color: str, title: str, bins: int = 20) -> go.Figure:
    fig = px.histogram(
        df,
        x=x,
        color=color,
        nbins=bins,
        barmode="overlay",
        opacity=0.62,
        color_discrete_map=SYSTEM_COLORS,
    )
    fig.update_layout(title=title, yaxis_title="Count")
    return _base_layout(fig, height=380)


def resource_activity_chart(df: pd.DataFrame, metric: str, title: str, y_title: str) -> go.Figure:
    fig = px.line(
        df,
        x="observation_date",
        y=metric,
        color="system",
        color_discrete_map=SYSTEM_COLORS,
        markers=True,
    )
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title="")
    return _base_layout(fig, height=380)


def grouped_bar_chart(
    df: pd.DataFrame, x: str, y: str, color: str, title: str, y_title: str
) -> go.Figure:
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        barmode="group",
        color_discrete_map=SYSTEM_COLORS,
    )
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title="")
    return _base_layout(fig, height=380)


def leak_coverage_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=summary["system"],
            y=summary["leak_rate_observed"],
            name="Observed leak rate",
            marker_color="#DC2626",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=summary["system"],
            y=summary["leak_reporting_coverage"],
            name="Leak reporting coverage",
            mode="lines+markers",
            marker_color="#2563EB",
            line=dict(width=2),
        )
    )
    fig.update_layout(
        title="Leak incidence versus leak reporting coverage",
        yaxis_title="Rate",
        xaxis_title="",
    )
    return _base_layout(fig, height=400)


def stacked_quality_chart(status_df: pd.DataFrame, x: str = "system") -> go.Figure:
    color_map = {
        "Usable": "#2563EB",
        "Aggregate": "#94A3B8",
        "Estimated": "#D97706",
        "Review Required": "#7C3AED",
        "Event Only": "#DC2626",
    }
    fig = px.bar(
        status_df,
        x=x,
        y="count",
        color="data_quality_status",
        barmode="stack",
        color_discrete_map=color_map,
        category_orders={"data_quality_status": QUALITY_ORDER},
    )
    fig.update_layout(title="Data-quality composition", xaxis_title="", yaxis_title="Rows")
    return _base_layout(fig, height=390)


def heatmap_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    title: str,
    color_scale: str = "YlGnBu",
    text_auto: str = ".2f",
) -> go.Figure:
    pivot = df.pivot(index=y, columns=x, values=z).sort_index()
    if x == "weekday_name":
        pivot = pivot.reindex(columns=WEEKDAY_ORDER)

    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale=color_scale,
        text_auto=text_auto,
    )
    fig.update_layout(title=title, xaxis_title="", yaxis_title="")
    return _base_layout(fig, height=400)


def horizontal_ranking_chart(
    df: pd.DataFrame, category_col: str, value_col: str, title: str, color: str = "#2563EB"
) -> go.Figure:
    trimmed = df.head(12).sort_values(value_col, ascending=True)
    fig = go.Figure(
        go.Bar(
            x=trimmed[value_col],
            y=trimmed[category_col],
            orientation="h",
            marker_color=color,
            text=trimmed[value_col],
            textposition="outside",
        )
    )
    fig.update_layout(title=title, xaxis_title="", yaxis_title="")
    return _base_layout(fig, height=420)


def confidence_band_chart(summary: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        summary,
        x="system",
        y="confidence_score",
        color="comparison_strength",
        color_discrete_map=ASSESSMENT_COLORS,
        text_auto=".0f",
        category_orders={"comparison_strength": list(ASSESSMENT_COLORS.keys())},
    )
    fig.update_layout(title="System confidence profile", yaxis_title="Confidence score")
    return _base_layout(fig, height=380)


def row_confidence_chart(df: pd.DataFrame) -> go.Figure:
    counts = (
        df["row_confidence_band"]
        .value_counts()
        .rename_axis("row_confidence_band")
        .reset_index(name="count")
    )
    fig = px.pie(
        counts,
        names="row_confidence_band",
        values="count",
        color="row_confidence_band",
        color_discrete_map=ROW_CONFIDENCE_COLORS,
        hole=0.45,
    )
    fig.update_layout(title="Evidence quality in the current slice")
    return _base_layout(fig, height=360)


def crop_heatmap(df: pd.DataFrame) -> go.Figure:
    pivot = df.pivot(index="system", columns="crop_type", values="count").fillna(0)
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="Blues",
        text_auto=".0f",
    )
    fig.update_layout(title="Crop mix by system", xaxis_title="", yaxis_title="")
    return _base_layout(fig, height=400)


def issue_timeline_chart(daily: pd.DataFrame) -> go.Figure:
    chart_df = daily.copy()
    chart_df["incident_total"] = chart_df["issue_events"] + chart_df["leak_events"]
    fig = px.line(
        chart_df,
        x="observation_date",
        y="incident_total",
        color="system",
        color_discrete_map=SYSTEM_COLORS,
        markers=True,
    )
    fig.update_layout(title="Incident timeline", yaxis_title="Issue + leak events", xaxis_title="")
    return _base_layout(fig, height=400)


def weekly_multi_metric_chart(weekly: pd.DataFrame, metric: str, title: str, y_title: str) -> go.Figure:
    fig = px.line(
        weekly,
        x="observation_week",
        y=metric,
        color="system",
        color_discrete_map=SYSTEM_COLORS,
        markers=True,
    )
    fig.update_layout(title=title, yaxis_title=y_title, xaxis_title="")
    return _base_layout(fig, height=390)


def completeness_heatmap(completeness: pd.DataFrame) -> go.Figure:
    long_df = completeness.melt(id_vars="system", var_name="metric", value_name="share")
    pivot = long_df.pivot(index="system", columns="metric", values="share")
    fig = px.imshow(
        pivot,
        aspect="auto",
        color_continuous_scale="YlGnBu",
        text_auto=".0%",
        zmin=0,
        zmax=1,
    )
    fig.update_layout(title="Field completeness by system", xaxis_title="", yaxis_title="")
    return _base_layout(fig, height=420)


def pipeline_flow_chart(
    cleaned_rows: int,
    validation_rows: int = 0,
    quality_rows: int = 0,
    review_rows: int = 0,
    dictionary_rows: int = 0,
    has_metadata: bool = False,
) -> go.Figure:
    """Show how cleaning outputs feed the deployed analytics app."""

    labels = [
        "Raw workbook",
        "Cleaning notebook",
        "cleaned_data.csv",
        "validation_report.csv",
        "data_quality_summary.csv",
        "rows_needing_review.csv",
        "data_dictionary.csv",
        "cleaning_metadata.json",
        "Streamlit analytics app",
    ]
    node = {label: index for index, label in enumerate(labels)}
    rows = max(int(cleaned_rows), 1)

    sources = [
        node["Raw workbook"],
        node["Cleaning notebook"],
        node["Cleaning notebook"],
        node["Cleaning notebook"],
        node["Cleaning notebook"],
        node["Cleaning notebook"],
        node["Cleaning notebook"],
        node["cleaned_data.csv"],
        node["validation_report.csv"],
        node["data_quality_summary.csv"],
        node["rows_needing_review.csv"],
        node["data_dictionary.csv"],
        node["cleaning_metadata.json"],
    ]
    targets = [
        node["Cleaning notebook"],
        node["cleaned_data.csv"],
        node["validation_report.csv"],
        node["data_quality_summary.csv"],
        node["rows_needing_review.csv"],
        node["data_dictionary.csv"],
        node["cleaning_metadata.json"],
        node["Streamlit analytics app"],
        node["Streamlit analytics app"],
        node["Streamlit analytics app"],
        node["Streamlit analytics app"],
        node["Streamlit analytics app"],
        node["Streamlit analytics app"],
    ]
    values = [
        rows,
        rows,
        max(int(validation_rows), 1),
        max(int(quality_rows), 1),
        max(int(review_rows), 1),
        max(int(dictionary_rows), 1),
        1 if has_metadata else 0.5,
        rows,
        max(int(validation_rows), 1),
        max(int(quality_rows), 1),
        max(int(review_rows), 1),
        max(int(dictionary_rows), 1),
        1 if has_metadata else 0.5,
    ]

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=18,
                line=dict(color="#CBD5E1", width=0.8),
                label=labels,
                color=[
                    "#DBEAFE",
                    "#E0F2FE",
                    "#DCFCE7",
                    "#FEF3C7",
                    "#FFEDD5",
                    "#FEE2E2",
                    "#EDE9FE",
                    "#F1F5F9",
                    "#DBEAFE",
                ],
            ),
            link=dict(source=sources, target=targets, value=values, color="rgba(37, 99, 235, 0.18)"),
        )
    )
    fig.update_layout(title="Cleaning-to-dashboard data flow")
    return _base_layout(fig, height=430)


def review_readiness_funnel(df: pd.DataFrame) -> go.Figure:
    """Show how many rows remain after key readiness checks."""

    total = len(df)
    water_ready = int(df["water_use_l"].notna().sum()) if "water_use_l" in df.columns else 0
    analysis_ready = int(df["analysis_ready_water_use_flag"].sum()) if "analysis_ready_water_use_flag" in df.columns else 0
    no_warning = int((~df["sanity_warning_flag"]).sum()) if "sanity_warning_flag" in df.columns else total
    no_review = int((~df["needs_review"]).sum()) if "needs_review" in df.columns else no_warning

    fig = go.Figure(
        go.Funnel(
            y=[
                "Rows in current scope",
                "Water quantity present",
                "Analysis-ready water rows",
                "No warning flag",
                "No human-review flag",
            ],
            x=[total, water_ready, analysis_ready, no_warning, no_review],
            marker={"color": ["#2563EB", "#3B82F6", "#059669", "#D97706", "#64748B"]},
        )
    )
    fig.update_layout(title="Data readiness funnel")
    return _base_layout(fig, height=390)


def score_radar_chart(scorecard: pd.DataFrame) -> go.Figure:
    """Compare system score dimensions as a radar chart."""

    dimensions = [
        "efficiency_score",
        "stability_score",
        "risk_score",
        "workload_score",
        "confidence_score",
    ]
    labels = ["Efficiency", "Stability", "Risk", "Workload", "Confidence"]
    fig = go.Figure()
    for _, row in scorecard.iterrows():
        values = [
            float(row[column]) if column in row and pd.notna(row[column]) else 0.0
            for column in dimensions
        ]
        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=labels + [labels[0]],
                fill="toself",
                name=str(row["system"]),
            )
        )
    fig.update_layout(
        title="System score profile radar",
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    )
    return _base_layout(fig, height=440)


def system_score_heatmap(scorecard: pd.DataFrame) -> go.Figure:
    """Render score dimensions as a compact heatmap."""

    matrix = scorecard.set_index("system")[
        [
            "efficiency_score",
            "stability_score",
            "risk_score",
            "workload_score",
            "confidence_score",
        ]
    ].rename(
        columns={
            "efficiency_score": "Efficiency",
            "stability_score": "Stability",
            "risk_score": "Risk",
            "workload_score": "Workload",
            "confidence_score": "Confidence",
        }
    )
    fig = px.imshow(
        matrix,
        aspect="auto",
        color_continuous_scale="Blues",
        text_auto=".0f",
        zmin=0,
        zmax=100,
    )
    fig.update_layout(title="System score heatmap", xaxis_title="", yaxis_title="")
    fig.update_coloraxes(colorbar_title="Score")
    return _base_layout(fig, height=380)


def feature_availability_heatmap(df: pd.DataFrame) -> go.Figure:
    """Show availability of important fields by system."""

    features = {
        "Water use": "water_use_l",
        "Return water": "return_now_l",
        "Water in return": "water_in_return_l",
        "Duration": "water_addition_duration_min",
        "pH-down": "ph_down_effective_ml",
        "Plant count": "plant_count",
        "Plant name": "plant_name_known_flag",
        "Growth stage": "growth_stage_known_flag",
        "Leak status": "leak_reported_flag",
    }
    rows: list[dict[str, float | str]] = []
    for system, group in df.groupby("system"):
        row: dict[str, float | str] = {"system": system}
        for label, column in features.items():
            if column not in group.columns:
                row[label] = np.nan
            elif group[column].dtype == bool:
                row[label] = float(group[column].mean())
            else:
                row[label] = float(group[column].notna().mean())
        rows.append(row)

    matrix = pd.DataFrame(rows).set_index("system")
    fig = px.imshow(
        matrix,
        aspect="auto",
        color_continuous_scale=[[0, "#FEE2E2"], [0.5, "#FEF3C7"], [1, "#DCFCE7"]],
        text_auto=".0%",
        zmin=0,
        zmax=1,
    )
    fig.update_layout(title="Feature availability by system", xaxis_title="", yaxis_title="")
    fig.update_coloraxes(colorbar_tickformat=".0%", colorbar_title="Available")
    return _base_layout(fig, height=420)


def risk_treemap(problem_counts: pd.DataFrame) -> go.Figure:
    """Show issue composition by system and category."""

    fig = px.treemap(
        problem_counts,
        path=["system", "problem_category"],
        values="count",
        color="count",
        color_continuous_scale="OrRd",
    )
    fig.update_layout(title="Operational issue composition")
    return _base_layout(fig, height=430)


def crop_sunburst_chart(crop_counts: pd.DataFrame) -> go.Figure:
    """Show crop hierarchy by system."""

    fig = px.sunburst(
        crop_counts,
        path=["system", "crop_type"],
        values="count",
        color="system",
        color_discrete_map=SYSTEM_COLORS,
    )
    fig.update_layout(title="Crop hierarchy by system")
    return _base_layout(fig, height=430)


def weekday_density_heatmap(df: pd.DataFrame, value_column: str = "dataset_row_id") -> go.Figure:
    """Show observation density by weekday and system."""

    density = (
        df.groupby(["system", "weekday_name"], as_index=False)
        .agg(rows=(value_column, "count"))
        .sort_values(["system", "weekday_name"])
    )
    density["weekday_name"] = pd.Categorical(
        density["weekday_name"], categories=WEEKDAY_ORDER, ordered=True
    )
    return heatmap_chart(
        density,
        x="weekday_name",
        y="system",
        z="rows",
        title="Observation density by weekday",
        color_scale="Blues",
        text_auto=".0f",
    )
