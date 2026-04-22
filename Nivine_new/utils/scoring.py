"""Confidence-aware scoring logic for the greenhouse system comparison views."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _minmax_score(series: pd.Series, higher_is_better: bool) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    if valid.empty:
        return pd.Series(np.nan, index=series.index)
    if valid.max() == valid.min():
        return pd.Series(50.0, index=series.index)
    if higher_is_better:
        scored = (numeric - valid.min()) / (valid.max() - valid.min()) * 100
    else:
        scored = (valid.max() - numeric) / (valid.max() - valid.min()) * 100
    return scored.clip(lower=0, upper=100)


def _weighted_average(row: pd.Series, weights: dict[str, float]) -> float:
    total_weight = 0.0
    total_value = 0.0
    for column, weight in weights.items():
        value = row.get(column)
        if pd.notna(value):
            total_weight += weight
            total_value += float(value) * weight
    if total_weight == 0:
        return np.nan
    return total_value / total_weight


def _performance_band(value: float) -> str:
    if pd.isna(value):
        return "Insufficient evidence"
    if value >= 67:
        return "High"
    if value >= 40:
        return "Medium"
    return "Low"


def _risk_band(value: float) -> str:
    if pd.isna(value):
        return "Insufficient evidence"
    if value >= 67:
        return "High"
    if value >= 40:
        return "Moderate"
    return "Low"


def _confidence_label(value: float) -> str:
    if pd.isna(value):
        return "Weak"
    if value >= 75:
        return "Strong"
    if value >= 55:
        return "Moderate"
    return "Weak"


def _efficiency_reliability_label(value: float) -> str:
    if pd.isna(value):
        return "Low reliability"
    if value >= 75:
        return "High reliability"
    if value >= 50:
        return "Medium reliability"
    return "Low reliability"


def _comparison_strength(confidence_label: str) -> str:
    mapping = {
        "Strong": "Reliable",
        "Moderate": "Directional only",
        "Weak": "Not reliable enough",
    }
    return mapping.get(confidence_label, "Not reliable enough")


def compute_confidence(summary: pd.DataFrame) -> pd.DataFrame:
    """Compute system-level confidence from quality flags only."""

    if summary.empty:
        return pd.DataFrame()

    result = summary[["system"]].copy()

    result["confidence_score"] = (
        100
        * (
            0.35 * summary["analysis_ready_share"].fillna(0)
            + 0.20 * (1 - summary["estimated_share"].fillna(1))
            + 0.20 * (1 - summary["core_missing_share"].fillna(1))
            + 0.15 * (1 - summary["warning_share"].fillna(1))
            + 0.10 * (1 - summary["imputed_share"].fillna(1))
        )
    ).clip(lower=0, upper=100)
    result["confidence_label"] = result["confidence_score"].apply(_confidence_label)

    explanations: list[str] = []
    for _, row in summary.iterrows():
        weak_points: list[str] = []
        if row["analysis_ready_share"] < 0.7:
            weak_points.append("analysis-ready coverage is limited")
        if row["estimated_share"] > 0.1:
            weak_points.append("estimated values are material")
        if row["core_missing_share"] > 0:
            weak_points.append("some core measurements are missing")
        if row["warning_share"] > 0.05:
            weak_points.append("warning flags are present")
        if row["imputed_share"] > 0.05:
            weak_points.append("imputed values are present")

        if not weak_points:
            explanations.append("Quality flags support a comparatively strong system-level evidence base.")
        else:
            explanations.append("Confidence is reduced because " + "; ".join(weak_points) + ".")

    result["confidence_explanation"] = explanations
    return result


def compute_stability(summary: pd.DataFrame) -> pd.DataFrame:
    """Score stability using coefficient of variation, rolling variance, and day-change consistency."""

    if summary.empty:
        return pd.DataFrame()

    result = summary[
        [
            "system",
            "daily_water_cv",
            "rolling_variance_ratio",
            "day_change_ratio",
            "stability_support_ratio",
            "stability_input_days",
            "aggregate_share",
        ]
    ].copy()

    result["stability_cv_component"] = _minmax_score(
        result["daily_water_cv"], higher_is_better=False
    )
    result["stability_rolling_component"] = _minmax_score(
        result["rolling_variance_ratio"], higher_is_better=False
    )
    result["stability_change_component"] = _minmax_score(
        result["day_change_ratio"], higher_is_better=False
    )
    result["stability_support_component"] = _minmax_score(
        result["stability_support_ratio"], higher_is_better=True
    )

    weights = {
        "stability_cv_component": 0.40,
        "stability_rolling_component": 0.30,
        "stability_change_component": 0.20,
        "stability_support_component": 0.10,
    }
    result["stability_score"] = result.apply(
        lambda row: _weighted_average(row, weights), axis=1
    )
    result["stability"] = result["stability_score"].apply(_performance_band)

    explanations: list[str] = []
    for _, row in result.iterrows():
        if row["stability_support_ratio"] < 0.4:
            explanations.append(
                "Stability is difficult to assess because too few non-aggregate daily water observations remain after filtering."
            )
            continue

        drivers: list[str] = []
        if pd.notna(row["daily_water_cv"]) and row["daily_water_cv"] <= result["daily_water_cv"].median(skipna=True):
            drivers.append("day-to-day water variability is comparatively contained")
        elif pd.notna(row["daily_water_cv"]):
            drivers.append("water variability is comparatively wide")

        if pd.notna(row["rolling_variance_ratio"]) and row["rolling_variance_ratio"] <= result["rolling_variance_ratio"].median(skipna=True):
            drivers.append("rolling variance stays relatively steady")
        elif pd.notna(row["rolling_variance_ratio"]):
            drivers.append("rolling variance remains elevated")

        if pd.notna(row["day_change_ratio"]) and row["day_change_ratio"] <= result["day_change_ratio"].median(skipna=True):
            drivers.append("day-to-day changes are comparatively consistent")
        elif pd.notna(row["day_change_ratio"]):
            drivers.append("day-to-day changes are comparatively abrupt")

        if row["aggregate_share"] > 0.12:
            drivers.append("aggregate days may still smooth some underlying volatility")

        explanations.append(". ".join(drivers).strip(". ") + ".")

    result["stability_explanation"] = explanations
    return result[
        ["system", "stability_score", "stability", "stability_explanation"]
    ]


def compute_risk(summary: pd.DataFrame) -> pd.DataFrame:
    """Score operational risk using issue days, leak days, severity, and manual intervention days."""

    if summary.empty:
        return pd.DataFrame()

    result = summary[
        [
            "system",
            "issue_days_per_active_day",
            "leak_days_per_active_day",
            "observed_leak_severity",
            "manual_days_per_active_day",
            "leak_reported_day_share",
        ]
    ].copy()

    result["risk_issue_component"] = _minmax_score(
        result["issue_days_per_active_day"], higher_is_better=True
    )
    result["risk_leak_component"] = _minmax_score(
        result["leak_days_per_active_day"], higher_is_better=True
    )
    result["risk_severity_component"] = _minmax_score(
        result["observed_leak_severity"], higher_is_better=True
    )
    result["risk_manual_component"] = _minmax_score(
        result["manual_days_per_active_day"], higher_is_better=True
    )

    weights = {
        "risk_issue_component": 0.35,
        "risk_leak_component": 0.25,
        "risk_severity_component": 0.20,
        "risk_manual_component": 0.20,
    }
    result["risk_score"] = result.apply(lambda row: _weighted_average(row, weights), axis=1)
    result["risk"] = result["risk_score"].apply(_risk_band)

    breakdowns: list[str] = []
    for _, row in result.iterrows():
        parts: list[str] = []
        if row["issue_days_per_active_day"] >= result["issue_days_per_active_day"].median(skipna=True):
            parts.append("issue-day frequency is a major risk driver")
        if row["manual_days_per_active_day"] >= result["manual_days_per_active_day"].median(skipna=True):
            parts.append("manual intervention burden is elevated")
        if pd.notna(row["leak_days_per_active_day"]) and row["leak_days_per_active_day"] > 0:
            parts.append("observed leak days contribute to risk")
        if pd.notna(row["observed_leak_severity"]) and row["observed_leak_severity"] >= 0.6:
            parts.append("observed leaks skew toward higher severity")
        if row["leak_reported_day_share"] < 0.5:
            parts.append("leak evidence is partial, so leak risk is a lower-bound estimate")
        breakdowns.append(". ".join(parts).strip(". ") + ".")

    result["risk_breakdown"] = breakdowns
    return result[["system", "risk_score", "risk", "risk_breakdown"]]


def compute_efficiency(
    summary: pd.DataFrame,
    stability: pd.DataFrame,
    confidence: pd.DataFrame,
) -> pd.DataFrame:
    """Score apparent efficiency while separating measurement strength from the score itself."""

    if summary.empty:
        return pd.DataFrame()

    base = summary.merge(
        stability[["system", "stability_score"]], on="system", how="left"
    ).merge(confidence[["system", "confidence_score"]], on="system", how="left")

    result = base[
        [
            "system",
            "water_use_per_active_day_l",
            "nutrient_use_per_active_day_ml",
            "manual_days_per_active_day",
            "stability_score",
            "water_day_coverage",
            "nutrient_quantity_capture_rate",
            "estimated_share",
            "aggregate_share",
            "nutrient_quantity_obs",
            "confidence_score",
        ]
    ].copy()

    result["efficiency_water_component"] = _minmax_score(
        result["water_use_per_active_day_l"], higher_is_better=False
    )
    result["efficiency_nutrient_component"] = _minmax_score(
        result["nutrient_use_per_active_day_ml"], higher_is_better=False
    )
    result["efficiency_intervention_component"] = _minmax_score(
        result["manual_days_per_active_day"], higher_is_better=False
    )
    result["efficiency_stability_component"] = _minmax_score(
        result["stability_score"], higher_is_better=True
    )

    weights = {
        "efficiency_water_component": 0.35,
        "efficiency_nutrient_component": 0.25,
        "efficiency_intervention_component": 0.20,
        "efficiency_stability_component": 0.20,
    }
    result["efficiency_score"] = result.apply(
        lambda row: _weighted_average(row, weights), axis=1
    )

    measurement_confidence = (
        100
        * (
            0.35 * result["water_day_coverage"].fillna(0)
            + 0.35 * result["nutrient_quantity_capture_rate"].fillna(0)
            + 0.15 * (1 - result["estimated_share"].fillna(1))
            + 0.15 * (1 - result["aggregate_share"].fillna(1))
        )
    ).clip(lower=0, upper=100)

    result["efficiency_confidence"] = (
        0.70 * measurement_confidence + 0.30 * result["confidence_score"].fillna(0)
    )
    result.loc[result["nutrient_quantity_obs"].fillna(0).eq(0), "efficiency_confidence"] = (
        result.loc[result["nutrient_quantity_obs"].fillna(0).eq(0), "efficiency_confidence"]
        .clip(upper=35)
    )
    result.loc[
        (result["nutrient_quantity_obs"].fillna(0).gt(0))
        & (result["nutrient_quantity_capture_rate"].fillna(0) < 0.35),
        "efficiency_confidence",
    ] = result.loc[
        (result["nutrient_quantity_obs"].fillna(0).gt(0))
        & (result["nutrient_quantity_capture_rate"].fillna(0) < 0.35),
        "efficiency_confidence",
    ].clip(upper=59)

    status_conditions = [
        (result["water_day_coverage"].fillna(0) >= 0.5)
        & (result["nutrient_quantity_obs"].fillna(0) > 0)
        & (result["nutrient_quantity_capture_rate"].fillna(0) >= 0.7),
        (result["water_day_coverage"].fillna(0) >= 0.5)
        & (result["nutrient_quantity_obs"].fillna(0) > 0),
    ]
    result["efficiency_measurement_status"] = np.select(
        status_conditions,
        ["Measured efficiency", "Estimated efficiency"],
        default="Unsupported efficiency",
    )
    result["efficiency_label"] = result["efficiency_confidence"].apply(
        _efficiency_reliability_label
    )

    warnings: list[str] = []
    for _, row in result.iterrows():
        if row["efficiency_measurement_status"] == "Unsupported efficiency":
            warnings.append(
                "⚠️ Efficiency comparison not fully reliable due to missing nutrient quantity tracking."
            )
        elif row["efficiency_measurement_status"] == "Estimated efficiency":
            warnings.append(
                "⚠️ Efficiency is only partially measured because nutrient quantities are captured inconsistently."
            )
        else:
            warnings.append("Efficiency is directly measured in the current slice.")
    result["efficiency_warning"] = warnings

    return result[
        [
            "system",
            "efficiency_score",
            "efficiency_confidence",
            "efficiency_label",
            "efficiency_measurement_status",
            "efficiency_warning",
        ]
    ]


def build_system_scorecard(
    summary: pd.DataFrame, mixed_types: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create the comparison scorecard plus component-level detail."""

    if summary.empty:
        empty = pd.DataFrame()
        return empty, empty

    confidence = compute_confidence(summary)
    stability = compute_stability(summary)
    risk = compute_risk(summary)
    efficiency = compute_efficiency(summary, stability, confidence)

    components = (
        summary.merge(confidence, on="system", how="left")
        .merge(stability, on="system", how="left")
        .merge(risk, on="system", how="left")
        .merge(efficiency, on="system", how="left")
    )

    components["workload_manual_component"] = _minmax_score(
        components["manual_days_per_active_day"], higher_is_better=True
    )
    components["workload_water_component"] = _minmax_score(
        components["manual_water_days_per_active_day"], higher_is_better=True
    )
    components["workload_nutrient_component"] = _minmax_score(
        components["nutrient_addition_days_per_active_day"], higher_is_better=True
    )
    components["workload_duration_component"] = _minmax_score(
        components["water_addition_duration_total_min"]
        / components["active_days"].replace(0, np.nan),
        higher_is_better=True,
    )

    workload_weights = {
        "workload_manual_component": 0.40,
        "workload_water_component": 0.20,
        "workload_nutrient_component": 0.20,
        "workload_duration_component": 0.20,
    }
    components["workload_score"] = components.apply(
        lambda row: _weighted_average(row, workload_weights), axis=1
    )
    components["workload"] = components["workload_score"].apply(_risk_band)

    components["confidence"] = components["confidence_label"]
    components["efficiency"] = components["efficiency_label"]
    components["comparison_strength"] = np.select(
        [
            components["efficiency_measurement_status"].eq("Unsupported efficiency")
            | components["confidence_label"].eq("Weak"),
            components["efficiency_measurement_status"].eq("Estimated efficiency")
            | components["confidence_label"].eq("Moderate"),
        ],
        ["Not reliable enough", "Directional only"],
        default="Reliable",
    )
    components["warning_badge"] = np.where(
        components["confidence_label"].eq("Weak"),
        "⚠️ Low confidence",
        np.where(
            components["efficiency_measurement_status"].ne("Measured efficiency"),
            "⚠️ Efficiency caution",
            "Evidence usable",
        ),
    )

    readouts: list[str] = []
    for _, row in components.iterrows():
        parts: list[str] = []

        if pd.notna(row["efficiency_score"]):
            if row["efficiency_score"] >= 67:
                parts.append("Apparent efficiency is comparatively strong")
            elif row["efficiency_score"] < 40:
                parts.append("Apparent efficiency is comparatively weak")

        if pd.notna(row["stability_score"]):
            if row["stability_score"] >= 67:
                parts.append("stability is a relative strength")
            elif row["stability_score"] < 40:
                parts.append("stability is comparatively weaker")

        if pd.notna(row["risk_score"]) and row["risk_score"] >= 67:
            parts.append("operational risk is elevated")
        elif pd.notna(row["risk_score"]) and row["risk_score"] < 40:
            parts.append("observed operational risk is lighter")

        if row["efficiency_measurement_status"] != "Measured efficiency":
            parts.append(row["efficiency_warning"])
        elif mixed_types:
            parts.append(
                "Cross-type efficiency comparisons should still be treated as directional."
            )

        if row["confidence_label"] == "Weak":
            parts.append("Overall conclusions should be treated cautiously.")

        readouts.append(" ".join(parts).strip())

    scorecard = components[
        [
            "system",
            "system_type",
            "observations",
            "active_days",
            "observations_per_active_day",
            "water_use_per_active_day_l",
            "water_use_per_observation_l",
            "issue_days_per_active_day",
            "manual_days_per_active_day",
            "leak_days_per_active_day",
            "leak_reported_day_share",
            "efficiency_score",
            "efficiency_confidence",
            "efficiency_label",
            "efficiency_measurement_status",
            "efficiency_warning",
            "risk_score",
            "risk",
            "risk_breakdown",
            "stability_score",
            "stability",
            "stability_explanation",
            "workload_score",
            "workload",
            "confidence_score",
            "confidence_label",
            "confidence_explanation",
            "comparison_strength",
            "warning_badge",
        ]
    ].copy()
    scorecard["confidence"] = scorecard["confidence_label"]
    scorecard["analytical_readout"] = readouts
    return scorecard, components
