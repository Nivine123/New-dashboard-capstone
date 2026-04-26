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
        margin=dict(l=18, r=18, t=58, b=18),
        font=dict(family="Aptos, Segoe UI, sans-serif", color="#17324d", size=13),
        legend_title_text="",
        title=dict(
            x=0.01,
            xanchor="left",
            font=dict(size=18, family="Aptos, Segoe UI, sans-serif", color="#17324d"),
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
            bordercolor="#d7e0d9",
            font=dict(color="#17324d", size=12),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#d4ddd6",
        tickcolor="#b9c7bc",
        ticks="outside",
        title_font=dict(size=12, color="#5c7081"),
    )
    fig.update_yaxes(
        gridcolor="#e4ebe5",
        zeroline=False,
        showline=True,
        linecolor="#d4ddd6",
        tickcolor="#b9c7bc",
        ticks="outside",
        title_font=dict(size=12, color="#5c7081"),
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
            marker_color="#E76F51",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=summary["system"],
            y=summary["leak_reporting_coverage"],
            name="Leak reporting coverage",
            mode="lines+markers",
            marker_color="#264653",
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
        "Usable": "#2A9D8F",
        "Aggregate": "#E9C46A",
        "Estimated": "#F4A261",
        "Review Required": "#B66DFF",
        "Event Only": "#E76F51",
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
    df: pd.DataFrame, category_col: str, value_col: str, title: str, color: str = "#2A9D8F"
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
        color_continuous_scale="YlGn",
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
