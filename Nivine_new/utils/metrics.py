"""Metric builders used across dashboard pages."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from utils.constants import QUALITY_ORDER, SYSTEM_ORDER, WEEKDAY_ORDER
from utils.data_loader import ensure_derived_columns


def _known_share(series: pd.Series) -> float:
    values = series.fillna("").astype(str).str.strip().str.lower()
    unknown_tokens = {
        "",
        "unknown",
        "nan",
        "none",
        "not reported",
        "no issue recorded",
        "unspecified",
    }
    return float((~values.isin(unknown_tokens)).mean()) if len(values) else np.nan


def safe_cv(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty or clean.mean() == 0 or len(clean) < 2:
        return np.nan
    return float(clean.std(ddof=1) / clean.mean())


def safe_rate(mask: pd.Series) -> float:
    clean = mask.dropna()
    return float(clean.mean()) if not clean.empty else np.nan


def sum_or_nan(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return np.nan
    return float(clean.sum())


def _safe_divide(numerator: float | int, denominator: float | int) -> float:
    if denominator in (0, None) or pd.isna(denominator):
        return np.nan
    return float(numerator) / float(denominator)


def _rolling_variance_ratio(series: pd.Series, window: int = 7) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.mean() == 0 or len(clean) < 3:
        return np.nan
    rolling_var = clean.rolling(window=window, min_periods=3).var()
    if rolling_var.dropna().empty:
        return np.nan
    return float(rolling_var.mean() / (clean.mean() ** 2))


def _day_change_ratio(series: pd.Series) -> float:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 2:
        return np.nan

    diffs = clean.diff().abs().dropna()
    if diffs.empty:
        return np.nan

    base = clean.shift(1).abs().replace(0, np.nan)
    pct_change = (clean.diff().abs() / base).dropna()
    if not pct_change.empty:
        return float(pct_change.median())

    if clean.mean() == 0:
        return np.nan
    return float(diffs.median() / clean.mean())


def format_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.1%}"


def format_num(value: float | None, decimals: int = 1, suffix: str = "") -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}{suffix}"


def order_systems(values: list[str]) -> list[str]:
    ordered = [system for system in SYSTEM_ORDER if system in values]
    ordered.extend(sorted([system for system in values if system not in ordered]))
    return ordered


def compute_overview_metrics(df: pd.DataFrame) -> dict[str, Any]:
    df = ensure_derived_columns(df)
    leak_observed = df[df["leak_reported_flag"]]
    warning_or_estimated = df["sanity_warning_flag"] | df["estimated_value_flag"]

    return {
        "total_observations": int(len(df)),
        "active_date_range": (
            f"{df['observation_date'].min():%Y-%m-%d} to {df['observation_date'].max():%Y-%m-%d}"
            if not df.empty
            else "No data"
        ),
        "system_count": int(df["system"].nunique()),
        "average_water_use_l": df.loc[df["water_use_l"].notna(), "water_use_l"].mean(),
        "leak_incidence_rate": safe_rate(leak_observed["leak_incident_flag"]),
        "leak_reporting_coverage": safe_rate(df["leak_reported_flag"]),
        "issue_incidence_rate": safe_rate(df["issue_incident_flag"]),
        "average_plant_count": df["plant_count"].mean(),
        "rows_marked_usable": int(df["data_quality_status"].eq("Usable").sum()),
        "analysis_ready_share": safe_rate(df["analysis_ready_water_use_flag"]),
        "warning_or_estimated_share": safe_rate(warning_or_estimated),
        "aggregate_share": safe_rate(df["weekend_or_aggregate_flag"]),
    }


def compute_daily_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_derived_columns(df)
    if df.empty:
        return pd.DataFrame()

    daily = (
        df.groupby(["system", "system_type", "observation_date"], as_index=False)
        .agg(
            observations=("dataset_row_id", "count"),
            water_rows=("water_use_l", lambda s: int(s.notna().sum())),
            daily_water_use_l=("water_use_l", sum_or_nan),
            daily_water_mean_l=("water_use_l", "mean"),
            daily_nutrient_ml=("nutrient_effective_ml", sum_or_nan),
            daily_ph_down_ml=("ph_down_effective_ml", sum_or_nan),
            mean_return_now_l=("return_now_l", "mean"),
            mean_water_in_return_l=("water_in_return_l", "mean"),
            issue_events=("issue_incident_flag", "sum"),
            leak_events=("leak_incident_flag", "sum"),
            manual_events=("manual_intervention_flag", "sum"),
            nutrient_events=("nutrient_addition_flag", "sum"),
            aggregate_rows=("weekend_or_aggregate_flag", "sum"),
            estimated_rows=("estimated_value_flag", "sum"),
            analysis_ready_rows=("analysis_ready_water_use_flag", "sum"),
        )
        .sort_values(["observation_date", "system"])
    )

    daily["rolling_7d_water_use_l"] = (
        daily.sort_values("observation_date")
        .groupby("system")["daily_water_use_l"]
        .transform(lambda s: s.rolling(window=7, min_periods=2).mean())
    )
    daily["rolling_14d_issue_rate"] = (
        daily.sort_values("observation_date")
        .groupby("system")["issue_events"]
        .transform(lambda s: s.rolling(window=14, min_periods=3).mean())
    )
    return daily


def compute_weekly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_derived_columns(df)
    if df.empty:
        return pd.DataFrame()

    weekly = (
        df.groupby(["system", "system_type", "observation_week"], as_index=False)
        .agg(
            observations=("dataset_row_id", "count"),
            weekly_water_use_l=("water_use_l", sum_or_nan),
            weekly_nutrient_ml=("nutrient_effective_ml", sum_or_nan),
            weekly_ph_down_ml=("ph_down_effective_ml", sum_or_nan),
            issue_events=("issue_incident_flag", "sum"),
            leak_events=("leak_incident_flag", "sum"),
            manual_events=("manual_intervention_flag", "sum"),
        )
        .sort_values(["observation_week", "system"])
    )

    weekly["rolling_4w_water_use_l"] = (
        weekly.groupby("system")["weekly_water_use_l"]
        .transform(lambda s: s.rolling(window=4, min_periods=2).mean())
    )
    return weekly


def compute_system_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build a normalized system summary for risk, stability, efficiency, and trust."""

    df = ensure_derived_columns(df)
    if df.empty:
        return pd.DataFrame()

    selected_span = (
        int((df["observation_date"].max() - df["observation_date"].min()).days) + 1
        if df["observation_date"].notna().any()
        else 0
    )

    severity_map = {
        "No Leak": 0.0,
        "Minor": 0.45,
        "Major": 1.0,
        "Unspecified": 0.6,
        "Unknown": np.nan,
    }
    frame = df.copy()
    frame["leak_severity_weight"] = frame["leak_severity"].map(severity_map)

    base = (
        frame.groupby(["system", "system_type"], as_index=False)
        .agg(
            observations=("dataset_row_id", "count"),
            active_days=("observation_date", "nunique"),
            analysis_ready_share=("analysis_ready_water_use_flag", "mean"),
            usable_share=("usable_row_flag", "mean"),
            aggregate_share=("weekend_or_aggregate_flag", "mean"),
            estimated_share=("estimated_value_flag", "mean"),
            core_missing_share=("core_measurement_missing", "mean"),
            warning_share=("sanity_warning_flag", "mean"),
            imputed_share=("age_days_imputed", "mean"),
            leak_reporting_coverage=("leak_reported_flag", "mean"),
            water_measurement_share=("water_measurement_available", "mean"),
            nutrient_measurement_share=("nutrient_measurement_available", "mean"),
            plant_count_mean=("plant_count", "mean"),
            plant_count_median=("plant_count", "median"),
            crop_known_share=("crop_types", _known_share),
            plant_known_share=("plant_name", _known_share),
            growth_known_share=("growth_stage", _known_share),
        )
        .sort_values("system")
    )

    row_metrics = (
        frame.groupby("system", as_index=False)
        .agg(
            water_obs=("water_use_l", lambda s: int(s.notna().sum())),
            water_total_l=("water_use_l", sum_or_nan),
            nutrient_quantity_obs=("nutrient_effective_ml", lambda s: int(s.notna().sum())),
            nutrient_total_effective_ml=("nutrient_effective_ml", sum_or_nan),
            ph_total_effective_ml=("ph_down_effective_ml", sum_or_nan),
            water_in_return_mean_l=("water_in_return_l", "mean"),
            return_now_mean_l=("return_now_l", "mean"),
            water_addition_duration_median_min=("water_addition_duration_min", "median"),
            water_addition_duration_total_min=("water_addition_duration_min", sum_or_nan),
        )
        .sort_values("system")
    )

    daily_ops = (
        frame.groupby(["system", "observation_date"], as_index=False)
        .agg(
            day_observations=("dataset_row_id", "count"),
            issue_day=("issue_incident_flag", "max"),
            issue_events=("issue_incident_flag", "sum"),
            manual_day=("manual_intervention_flag", "max"),
            manual_events=("manual_intervention_flag", "sum"),
            leak_day=("leak_incident_flag", "max"),
            leak_events=("leak_incident_flag", "sum"),
            leak_reported_day=("leak_reported_flag", "max"),
            leak_severity_day=("leak_severity_weight", "max"),
            major_leak_day=("leak_severity", lambda s: int(s.eq("Major").any())),
            nutrient_addition_day=("nutrient_addition_flag", "max"),
            nutrient_quantity_day=("nutrient_measurement_available", "max"),
            water_measurement_day=("water_measurement_available", "max"),
            manual_water_day=("manual_water_activity_flag", "max"),
            aggregate_day=("weekend_or_aggregate_flag", "max"),
            estimated_day=("estimated_value_flag", "max"),
        )
        .sort_values(["system", "observation_date"])
    )

    operational = (
        daily_ops.groupby("system", as_index=False)
        .agg(
            observations_per_active_day=("day_observations", "mean"),
            issue_days=("issue_day", "sum"),
            issue_days_per_active_day=("issue_day", "mean"),
            issue_events_per_day=("issue_events", "mean"),
            manual_days=("manual_day", "sum"),
            manual_days_per_active_day=("manual_day", "mean"),
            manual_events_per_day=("manual_events", "mean"),
            leak_days=("leak_day", "sum"),
            leak_days_per_active_day=("leak_day", "mean"),
            leak_events_per_day=("leak_events", "mean"),
            leak_reported_days=("leak_reported_day", "sum"),
            leak_reported_day_share=("leak_reported_day", "mean"),
            observed_leak_severity=("leak_severity_day", "mean"),
            major_leak_day_share=("major_leak_day", "mean"),
            water_days=("water_measurement_day", "sum"),
            water_day_coverage=("water_measurement_day", "mean"),
            nutrient_addition_days=("nutrient_addition_day", "sum"),
            nutrient_addition_days_per_active_day=("nutrient_addition_day", "mean"),
            nutrient_quantity_days=("nutrient_quantity_day", "sum"),
            nutrient_day_coverage=("nutrient_quantity_day", "mean"),
            manual_water_days_per_active_day=("manual_water_day", "mean"),
            aggregate_day_share=("aggregate_day", "mean"),
            estimated_day_share=("estimated_day", "mean"),
        )
        .sort_values("system")
    )

    stability_source = frame[
        frame["analysis_ready_water_use_flag"]
        & frame["water_use_l"].notna()
        & ~frame["weekend_or_aggregate_flag"]
        & ~frame["estimated_value_flag"]
    ]

    stability_daily = (
        stability_source.groupby(["system", "observation_date"], as_index=False)
        .agg(daily_water_use_l=("water_use_l", sum_or_nan))
        .sort_values(["system", "observation_date"])
    )

    stability_rows: list[dict[str, Any]] = []
    for system, group in stability_daily.groupby("system"):
        ordered = group.sort_values("observation_date")
        series = ordered["daily_water_use_l"]
        stability_rows.append(
            {
                "system": system,
                "stability_input_days": int(len(ordered)),
                "daily_water_mean_l": float(series.mean()) if not series.dropna().empty else np.nan,
                "daily_water_cv": safe_cv(series),
                "rolling_variance_ratio": _rolling_variance_ratio(series),
                "day_change_ratio": _day_change_ratio(series),
                "median_abs_day_change_l": (
                    float(series.diff().abs().median())
                    if len(series.dropna()) > 1
                    else np.nan
                ),
            }
        )
    stability = pd.DataFrame(stability_rows)

    if stability.empty:
        stability = pd.DataFrame(
            columns=[
                "system",
                "stability_input_days",
                "daily_water_mean_l",
                "daily_water_cv",
                "rolling_variance_ratio",
                "day_change_ratio",
                "median_abs_day_change_l",
            ]
        )

    summary = (
        base.merge(row_metrics, on="system", how="left")
        .merge(operational, on="system", how="left")
        .merge(stability, on="system", how="left")
    )

    summary["coverage_density"] = (
        summary["active_days"] / selected_span if selected_span else np.nan
    )
    summary["clean_row_share"] = (
        1
        - summary["aggregate_share"].fillna(0)
        - summary["estimated_share"].fillna(0)
        - summary["core_missing_share"].fillna(0)
    ).clip(lower=0, upper=1)

    summary["water_use_per_active_day_l"] = summary.apply(
        lambda row: _safe_divide(row["water_total_l"], row["active_days"]), axis=1
    )
    summary["water_use_per_observation_l"] = summary.apply(
        lambda row: _safe_divide(row["water_total_l"], row["water_obs"]), axis=1
    )
    summary["nutrient_use_per_active_day_ml"] = summary.apply(
        lambda row: _safe_divide(row["nutrient_total_effective_ml"], row["active_days"]),
        axis=1,
    )
    summary["nutrient_use_per_observation_ml"] = summary.apply(
        lambda row: _safe_divide(
            row["nutrient_total_effective_ml"], row["nutrient_quantity_obs"]
        ),
        axis=1,
    )
    summary["ph_use_per_active_day_ml"] = summary.apply(
        lambda row: _safe_divide(row["ph_total_effective_ml"], row["active_days"]), axis=1
    )
    summary["issue_events_per_observation"] = summary.apply(
        lambda row: _safe_divide(row["issue_days"], row["observations"]), axis=1
    )
    summary["manual_events_per_observation"] = summary.apply(
        lambda row: _safe_divide(row["manual_days"], row["observations"]), axis=1
    )
    summary["leak_days_per_reported_day"] = summary.apply(
        lambda row: _safe_divide(row["leak_days"], row["leak_reported_days"]), axis=1
    )
    summary["nutrient_quantity_capture_rate"] = summary.apply(
        lambda row: (
            _safe_divide(row["nutrient_quantity_days"], row["nutrient_addition_days"])
            if row["nutrient_addition_days"] > 0
            else (1.0 if row["nutrient_quantity_days"] > 0 else 0.0)
        ),
        axis=1,
    )
    summary["stability_support_ratio"] = summary.apply(
        lambda row: _safe_divide(row["stability_input_days"], row["active_days"]), axis=1
    )

    summary["risk_signal_text"] = np.select(
        [
            summary["issue_days_per_active_day"].ge(0.5),
            summary["issue_days_per_active_day"].ge(0.2),
        ],
        [
            "Frequent issue days are recorded across the active period",
            "Issues recur, but not on most active days",
        ],
        default="Recorded issue pressure is comparatively lower",
    )

    summary["system"] = pd.Categorical(
        summary["system"],
        categories=order_systems(summary["system"].astype(str).tolist()),
        ordered=True,
    )
    summary = summary.sort_values("system").reset_index(drop=True)
    return summary


def explode_token_counts(
    df: pd.DataFrame, token_column: str, label_name: str
) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for _, row in df[["system", token_column]].iterrows():
        for token in row[token_column]:
            records.append({"system": row["system"], label_name: token})

    if not records:
        return pd.DataFrame(columns=["system", label_name, "count"])

    exploded = pd.DataFrame(records)
    counts = (
        exploded.groupby(["system", label_name], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["count", label_name], ascending=[False, True])
    )
    return counts


def compute_problem_category_counts(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_derived_columns(df)
    return explode_token_counts(df, "problem_category_tokens", "problem_category")


def compute_leak_location_counts(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_derived_columns(df)
    leaks = df[df["leak_incident_flag"]]
    return explode_token_counts(leaks, "leak_location_tokens", "leak_location")


def compute_crop_counts(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_derived_columns(df)
    return explode_token_counts(df, "crop_tokens", "crop_type")


def compute_quality_summary(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = ensure_derived_columns(df)
    status_overall = (
        df["data_quality_status"]
        .value_counts(dropna=False)
        .rename_axis("data_quality_status")
        .reset_index(name="count")
    )
    status_overall["data_quality_status"] = pd.Categorical(
        status_overall["data_quality_status"],
        categories=QUALITY_ORDER,
        ordered=True,
    )
    status_overall = status_overall.sort_values("data_quality_status")

    status_by_system = (
        df.groupby(["system", "data_quality_status"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    status_by_system["data_quality_status"] = pd.Categorical(
        status_by_system["data_quality_status"],
        categories=QUALITY_ORDER,
        ordered=True,
    )

    completeness = (
        df.groupby("system", as_index=False)
        .agg(
            water_use_recorded=("water_use_l", lambda s: float(s.notna().mean())),
            nutrient_quantity_recorded=(
                "nutrient_effective_ml",
                lambda s: float(s.notna().mean()),
            ),
            leak_status_recorded=("leak_reported_flag", "mean"),
            issue_flag_recorded=("issue_flag", lambda s: float(s.notna().mean())),
            crop_type_known=("crop_known_flag", "mean"),
            plant_name_known=("plant_name_known_flag", "mean"),
            growth_stage_known=("growth_stage_known_flag", "mean"),
            plant_count_known=("plant_count_known_flag", "mean"),
            analysis_ready_share=("analysis_ready_water_use_flag", "mean"),
            estimated_share=("estimated_value_flag", "mean"),
            aggregate_share=("weekend_or_aggregate_flag", "mean"),
            warning_share=("sanity_warning_flag", "mean"),
            imputed_share=("age_days_imputed", "mean"),
        )
        .sort_values("system")
    )

    return {
        "status_overall": status_overall,
        "status_by_system": status_by_system,
        "completeness": completeness,
    }


def build_trust_matrix(
    df: pd.DataFrame, summary: pd.DataFrame, scorecard: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Summarize where the comparison is reliable, directional, or too weak."""

    df = ensure_derived_columns(df)
    if summary.empty:
        return pd.DataFrame(columns=["Dimension", "Reliability", "Why"])

    mixed_system_types = df["system_type"].nunique() > 1
    mixed_water_basis = df["water_use_basis"].nunique() > 1

    if scorecard is None or scorecard.empty:
        efficiency_confidence_floor = 0.0
        unsupported_efficiency = len(summary)
    else:
        efficiency_confidence_floor = float(
            scorecard["efficiency_confidence"].fillna(0).min()
        )
        unsupported_efficiency = int(
            scorecard["efficiency_measurement_status"].eq("Unsupported efficiency").sum()
        )

    efficiency_why: list[str] = []
    if unsupported_efficiency > 0:
        efficiency_why.append(
            "at least one system lacks complete nutrient measurement, so efficiency is not fully measured"
        )
    if mixed_system_types or mixed_water_basis:
        efficiency_why.append(
            "system types and water-use bases are not directly equivalent"
        )
    if efficiency_confidence_floor < 40:
        efficiency_assessment = "Not reliable enough"
        efficiency_why = (
            "At least one system lacks complete nutrient measurement; efficiency is not fully measured and not directly comparable across system types."
        )
    elif efficiency_confidence_floor < 70 or mixed_system_types or mixed_water_basis:
        efficiency_assessment = "Directional only"
        efficiency_why = (
            "Efficiency can be interpreted directionally, but incomplete nutrient measurement or cross-system comparability limits prevent a fully defensible ranking."
        )
    else:
        efficiency_assessment = "Reliable"
        efficiency_why = (
            "Efficiency inputs are sufficiently measured and comparable across the selected systems."
        )

    if summary["stability_support_ratio"].fillna(0).min() >= 0.6:
        stability_assessment = "Reliable"
        stability_why = (
            "Based on consistent non-aggregate daily water series with sufficient coverage across systems."
        )
    elif summary["stability_input_days"].fillna(0).min() >= 10:
        stability_assessment = "Directional only"
        stability_why = (
            "Daily stability can be compared, but at least one system has a shorter clean time series."
        )
    else:
        stability_assessment = "Not reliable enough"
        stability_why = (
            "At least one system lacks enough clean day-level water observations for a defensible stability comparison."
        )

    leak_cov = summary["leak_reported_day_share"].fillna(0)
    if leak_cov.min() >= 0.75:
        risk_assessment = "Reliable"
        risk_why = (
            "Issue and manual-intervention fields are broadly populated, and leak reporting is strong enough to support a risk comparison."
        )
    elif leak_cov.max() >= 0.4:
        risk_assessment = "Directional only"
        risk_why = (
            "Issue and intervention signals are usable, but incomplete leak reporting limits full reliability."
        )
    else:
        risk_assessment = "Not reliable enough"
        risk_why = (
            "Leak coverage is too weak to support a full operational-risk comparison."
        )

    confidence_floor = summary[
        [
            "analysis_ready_share",
            "estimated_share",
            "core_missing_share",
            "warning_share",
            "imputed_share",
        ]
    ]
    if confidence_floor["analysis_ready_share"].min() >= 0.8 and (
        confidence_floor[["estimated_share", "core_missing_share", "warning_share"]]
        .max()
        .max()
        <= 0.1
    ):
        confidence_assessment = "Reliable"
        confidence_why = (
            "System-level quality flags provide a solid basis for confidence-weighted interpretation."
        )
    elif confidence_floor["analysis_ready_share"].min() >= 0.6:
        confidence_assessment = "Directional only"
        confidence_why = (
            "Confidence indicators are informative but should guide interpretation rather than act as primary decision drivers."
        )
    else:
        confidence_assessment = "Not reliable enough"
        confidence_why = (
            "At least one system has too little analysis-ready support for a strong confidence comparison."
        )

    records = [
        {
            "Dimension": "Efficiency",
            "Reliability": efficiency_assessment,
            "Why": efficiency_why,
        },
        {
            "Dimension": "Stability",
            "Reliability": stability_assessment,
            "Why": stability_why,
        },
        {
            "Dimension": "Operational Risk",
            "Reliability": risk_assessment,
            "Why": risk_why,
        },
        {
            "Dimension": "Evidence Strength",
            "Reliability": confidence_assessment,
            "Why": confidence_why,
        },
    ]
    return pd.DataFrame(records)


def compute_incident_heatmap(df: pd.DataFrame, incident_column: str) -> pd.DataFrame:
    df = ensure_derived_columns(df)
    heatmap = (
        df.groupby(["system", "weekday_name"], as_index=False)[incident_column]
        .mean()
        .rename(columns={incident_column: "rate"})
    )
    heatmap["weekday_name"] = pd.Categorical(
        heatmap["weekday_name"], categories=WEEKDAY_ORDER, ordered=True
    )
    return heatmap.sort_values(["system", "weekday_name"])
