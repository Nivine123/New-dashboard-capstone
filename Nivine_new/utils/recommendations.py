"""Narratives, key findings, and action-oriented recommendation builders."""

from __future__ import annotations

from typing import Any

import pandas as pd

from utils.metrics import format_num, format_pct


def _system_name(scorecard: pd.DataFrame, column: str, ascending: bool) -> str | None:
    usable = scorecard.dropna(subset=[column])
    if usable.empty:
        return None
    row = usable.sort_values(column, ascending=ascending).iloc[0]
    return str(row["system"])


def _system_row(scorecard: pd.DataFrame, system_name: str | None) -> pd.Series | None:
    if system_name is None or scorecard.empty:
        return None
    matches = scorecard[scorecard["system"] == system_name]
    if matches.empty:
        return None
    return matches.iloc[0]


def _assessment_lookup(
    trust_matrix: pd.DataFrame, comparison_area: str, default: str = "Directional only"
) -> str:
    if trust_matrix.empty:
        return default
    matches = trust_matrix.loc[
        trust_matrix["Dimension"].eq(comparison_area), "Reliability"
    ]
    return str(matches.iloc[0]) if not matches.empty else default


def build_dimension_confidence_summary(trust_matrix: pd.DataFrame) -> dict[str, str]:
    """Keep confidence dimension-specific so Page 1 does not overstate certainty."""

    efficiency = _assessment_lookup(trust_matrix, "Efficiency")
    stability = _assessment_lookup(trust_matrix, "Stability")
    risk = _assessment_lookup(trust_matrix, "Operational Risk")

    assessments = {efficiency, stability, risk}
    if len(assessments) == 1:
        overall = "Moderate" if efficiency == "Directional only" else efficiency
    elif "Not reliable enough" in assessments:
        overall = "Dimension-dependent"
    else:
        overall = "Mixed"

    return {
        "efficiency": efficiency,
        "stability": stability,
        "risk": risk,
        "overall": overall,
    }


def _stability_detail(row: pd.Series | None) -> str:
    if row is None:
        return "No stability comparison is available."
    full = _stability_statement(row)
    prefix = f"{row['system']} has the strongest current stability score. "
    return full[len(prefix) :] if full.startswith(prefix) else full


def _sentence_case(text: str) -> str:
    if not text:
        return text
    parts = [part.strip() for part in text.split(". ") if part.strip()]
    normalized = []
    for part in parts:
        cleaned = part[:-1] if part.endswith(".") else part
        normalized.append(cleaned[:1].upper() + cleaned[1:])
    return ". ".join(normalized) + ("." if normalized else "")


def _efficiency_statement(row: pd.Series | None) -> str:
    if row is None:
        return "No efficiency comparison is available."

    base = (
        f"{row['system']} shows the strongest apparent efficiency score in the current slice."
    )
    if row["efficiency_measurement_status"] == "Measured efficiency":
        return (
            base
            + f" The efficiency signal is {row['efficiency_label'].lower()} because water, nutrient, intervention, and stability inputs are sufficiently observed."
        )
    if row["efficiency_measurement_status"] == "Estimated efficiency":
        return (
            base
            + " Interpret this as directional only because nutrient quantities are captured inconsistently."
        )
    return (
        base
        + " Interpret this as directional only because nutrient quantities are not fully measured, so the apparent lead is unsupported."
    )


def _stability_statement(row: pd.Series | None) -> str:
    """Translate the raw stability drivers into a non-contradictory executive narrative."""

    if row is None:
        return "No stability comparison is available."

    explanation = str(row.get("stability_explanation", "")).lower()
    contained = "comparatively contained" in explanation
    wide = "comparatively wide" in explanation
    steady = "rolling variance stays relatively steady" in explanation
    elevated = "rolling variance remains elevated" in explanation
    consistent = "day-to-day changes are comparatively consistent" in explanation
    abrupt = "day-to-day changes are comparatively abrupt" in explanation
    smoothed = "aggregate days may still smooth" in explanation

    clauses: list[str] = [f"{row['system']} has the strongest current stability score."]

    if contained and steady and abrupt:
        clauses.append(
            "Longer-run water variability appears comparatively controlled, although short-term day-to-day shifts are still present."
        )
    elif contained and steady:
        clauses.append(
            "Both overall water variability and rolling variance appear comparatively controlled."
        )
    elif wide and steady:
        clauses.append(
            "Variance is fairly steady through time, although the overall spread of water use remains wider than the most stable pattern."
        )
    elif contained:
        clauses.append("Overall water variability appears comparatively contained.")
    elif steady:
        clauses.append("Rolling variance is comparatively steady through time.")
    elif elevated:
        clauses.append("Variance remains elevated, which weakens the stability signal.")

    if consistent and not abrupt:
        clauses.append("Day-to-day changes are comparatively consistent.")
    elif abrupt and not (contained and steady):
        clauses.append("Short-term day-to-day shifts remain comparatively abrupt.")

    if smoothed:
        clauses.append("Aggregate days may smooth part of the observed pattern.")

    return " ".join(clauses)


def build_key_findings(
    scorecard: pd.DataFrame,
    summary: pd.DataFrame,
    comparability_note: str | None,
    include_caution: bool = True,
) -> list[dict[str, str]]:
    if scorecard.empty or summary.empty:
        return []

    efficiency_row = _system_row(
        scorecard, _system_name(scorecard, "efficiency_score", ascending=False)
    )
    stability_row = _system_row(
        scorecard, _system_name(scorecard, "stability_score", ascending=False)
    )
    risk_row = _system_row(scorecard, _system_name(scorecard, "risk_score", ascending=False))

    findings: list[dict[str, str]] = []

    if efficiency_row is not None:
        findings.append(
            {
                "title": f"Apparent efficiency leader: {efficiency_row['system']}",
                "body": _efficiency_statement(efficiency_row),
            }
        )

    if stability_row is not None:
        findings.append(
            {
                "title": f"Most stable operating pattern: {stability_row['system']}",
                "body": _stability_statement(stability_row),
            }
        )

    if risk_row is not None:
        findings.append(
            {
                "title": f"Highest operational risk: {risk_row['system']}",
                "body": (
                    f"{risk_row['system']} carries the highest composite risk score in the current slice. "
                    f"{_sentence_case(str(risk_row['risk_breakdown']))}"
                ),
            }
        )

    if comparability_note and include_caution:
        findings.append(
            {
                "title": "Critical interpretation caution",
                "body": comparability_note,
            }
        )

    return findings[:4]


def build_executive_summary(
    overview: dict[str, Any],
    scorecard: pd.DataFrame,
    summary: pd.DataFrame,
    trust_matrix: pd.DataFrame,
    comparability_note: str | None,
) -> str:
    if scorecard.empty:
        return "No observations remain after the selected filters."

    efficiency_row = _system_row(
        scorecard, _system_name(scorecard, "efficiency_score", ascending=False)
    )
    stability_row = _system_row(
        scorecard, _system_name(scorecard, "stability_score", ascending=False)
    )
    risk_row = _system_row(scorecard, _system_name(scorecard, "risk_score", ascending=False))
    confidence = build_dimension_confidence_summary(trust_matrix)

    sentences = [
        (
            f"The current selection covers {overview['total_observations']} observations across "
            f"{overview['system_count']} greenhouse systems from {overview['active_date_range']}."
        ),
        (
            f"Confidence is dimension-dependent: efficiency is {confidence['efficiency'].lower()}, "
            f"stability is {confidence['stability'].lower()}, and operational risk is {confidence['risk'].lower()}."
        ),
        "No single system has equally strong evidence across all dimensions; evidence strength varies by metric.",
    ]
    if efficiency_row is not None:
        sentences.append(_efficiency_statement(efficiency_row))
    if stability_row is not None:
        sentences.append(
            f"{stability_row['system']} currently provides the strongest stability benchmark. {_stability_detail(stability_row)}"
        )
    if risk_row is not None:
        sentences.append(
            f"Operational risk is currently highest in {risk_row['system']}, driven by frequent issue days, heavier manual intervention, and observed leak burden."
        )
    if comparability_note:
        sentences.append(
            "As noted in the comparability caution, efficiency should be interpreted directionally across system types."
        )
    return " ".join(sentences)


def build_dashboard_tells_us(
    scorecard: pd.DataFrame,
    summary: pd.DataFrame,
    trust_matrix: pd.DataFrame,
    comparability_note: str | None,
) -> list[str]:
    if scorecard.empty:
        return ["The selected filters leave no rows to analyze."]

    efficiency_row = scorecard.sort_values("efficiency_score", ascending=False).iloc[0]
    stability_row = scorecard.sort_values("stability_score", ascending=False).iloc[0]
    risk_row = scorecard.sort_values("risk_score", ascending=False).iloc[0]
    confidence = build_dimension_confidence_summary(trust_matrix)

    items = [
        (
            f"Confidence is dimension-dependent: efficiency is {confidence['efficiency'].lower()}, stability is {confidence['stability'].lower()}, and risk is {confidence['risk'].lower()}."
        ),
        (
            "No single system has equally strong evidence across all dimensions; evidence strength varies by metric."
        ),
        (
            f"{stability_row['system']} currently provides the strongest stability benchmark, while {risk_row['system']} carries the heaviest day-normalized operational burden."
        ),
        (
            f"{efficiency_row['system']} shows the strongest apparent efficiency score, but interpret that result directionally as noted in the comparability caution."
            if comparability_note
            else f"{efficiency_row['system']} shows the strongest apparent efficiency score, but the result remains directional rather than definitive."
        ),
    ]
    return items


def build_key_cautions(summary: pd.DataFrame, trust_matrix: pd.DataFrame) -> list[str]:
    cautions: list[str] = []

    unsupported_efficiency = trust_matrix[
        trust_matrix["Dimension"].eq("Efficiency")
        & trust_matrix["Reliability"].eq("Not reliable enough")
    ]
    if not unsupported_efficiency.empty:
        cautions.append(
            "As noted in the comparability caution, efficiency is not yet defensible as a cross-system ranking because nutrient measurement remains incomplete."
        )

    low_leak = summary.loc[
        summary["leak_reported_day_share"].fillna(0) < 0.5, "system"
    ].astype(str).tolist()
    if low_leak:
        cautions.append(
            f"Leak comparisons are partial for {', '.join(low_leak)} because leak status is not recorded on enough active days."
        )

    sparse_crop = summary.loc[
        summary[["crop_known_share", "plant_known_share", "growth_known_share"]]
        .fillna(0)
        .mean(axis=1)
        < 0.35,
        "system",
    ].astype(str).tolist()
    if sparse_crop:
        cautions.append(
            f"Plant and growth-stage analysis is weak for {', '.join(sparse_crop)} due to sparse metadata."
        )

    if not cautions:
        cautions.append(
            "Comparisons remain observational and should be treated as evidence for prioritization, not causal proof."
        )

    return cautions[:4]


def generate_recommendation_table(
    scorecard: pd.DataFrame, summary: pd.DataFrame, trust_matrix: pd.DataFrame
) -> pd.DataFrame:
    if scorecard.empty or summary.empty:
        return pd.DataFrame(
            columns=[
                "Finding",
                "Why it matters",
                "Recommended action",
                "Expected benefit",
                "Confidence level",
            ]
        )

    recommendations: list[dict[str, str]] = []

    efficiency_row = scorecard.sort_values("efficiency_score", ascending=False).iloc[0]
    if efficiency_row["efficiency_measurement_status"] != "Measured efficiency":
        recommendations.append(
            {
                "Finding": "Efficiency is not yet decision-grade across all systems.",
                "Why it matters": efficiency_row["efficiency_warning"],
                "Recommended action": (
                    "Standardize nutrient quantity logging across systems before making a scale-up decision based on apparent efficiency."
                ),
                "Expected benefit": "Efficiency conclusions become academically defensible and operationally comparable.",
                "Confidence level": "High",
            }
        )

    highest_risk_system = _system_name(scorecard, "risk_score", ascending=False)
    if highest_risk_system:
        risk_row = summary[summary["system"] == highest_risk_system].iloc[0]
        recommendations.append(
            {
                "Finding": f"{highest_risk_system} shows the highest operational risk per active day.",
                "Why it matters": (
                    f"Issue days occur on {format_pct(risk_row['issue_days_per_active_day'])} of active days, "
                    f"and manual intervention days occur on {format_pct(risk_row['manual_days_per_active_day'])}."
                ),
                "Recommended action": (
                    f"Prioritize a root-cause review for {highest_risk_system}, starting with recurring issue categories, leak points, and manual overrides."
                ),
                "Expected benefit": "Lower downtime risk and lower intervention burden.",
                "Confidence level": "High",
            }
        )

    most_stable = _system_name(scorecard, "stability_score", ascending=False)
    if most_stable:
        stable_row = _system_row(scorecard, most_stable)
        recommendations.append(
            {
                "Finding": f"{most_stable} provides the strongest stability benchmark.",
                "Why it matters": stable_row["stability_explanation"],
                "Recommended action": (
                    f"Use {most_stable} as the benchmark operating pattern when defining acceptable process variance and monitoring thresholds."
                ),
                "Expected benefit": "Better forecasting, planning, and control.",
                "Confidence level": "Moderate",
            }
        )

    low_leak = summary.loc[
        summary["leak_reported_day_share"].fillna(0) < 0.5, "system"
    ].astype(str).tolist()
    if low_leak:
        recommendations.append(
            {
                "Finding": "Leak monitoring remains incomplete in some systems.",
                "Why it matters": (
                    f"{', '.join(low_leak)} cannot be treated as low-leak systems when leak status is absent on many active days."
                ),
                "Recommended action": (
                    "Make leak status mandatory on every observation, including severity and location when a leak occurs."
                ),
                "Expected benefit": "Risk comparisons become much more trustworthy.",
                "Confidence level": "High",
            }
        )

    directional = trust_matrix[trust_matrix["Reliability"] == "Directional only"]
    if not directional.empty:
        recommendations.append(
            {
                "Finding": "Some comparisons remain directional rather than definitive.",
                "Why it matters": directional.iloc[0]["Why"],
                "Recommended action": (
                    "Validate the apparent leaders in a controlled follow-up period with harmonized measurement rules before making a capital or procurement decision."
                ),
                "Expected benefit": "Lower decision risk and stronger thesis defensibility.",
                "Confidence level": "Moderate",
            }
        )

    return pd.DataFrame(recommendations)


def build_decision_summary(
    scorecard: pd.DataFrame, summary: pd.DataFrame, comparability_note: str | None
) -> dict[str, str]:
    if scorecard.empty:
        return {
            "best_efficiency": "No result",
            "best_stability": "No result",
            "highest_operational_risk": "No result",
            "most_reliable_conclusion": "No result",
            "what_not_to_conclude": "No result",
            "validate_before_decision": "No result",
            "efficiency_takeaway": "No result",
            "stability_takeaway": "No result",
            "risk_takeaway": "No result",
            "most_reliable_insight": "No result",
            "not_yet_defensible": "No result",
        }

    efficiency_row = scorecard.sort_values("efficiency_score", ascending=False).iloc[0]
    stability_row = scorecard.sort_values("stability_score", ascending=False).iloc[0]
    risk_row = scorecard.sort_values("risk_score", ascending=False).iloc[0]
    confidence_row = scorecard.sort_values("confidence_score", ascending=False).iloc[0]

    best_efficiency = f"{efficiency_row['system']} ({efficiency_row['efficiency_label']}; {efficiency_row['efficiency_measurement_status']})"
    best_stability = f"{stability_row['system']} (stability score {stability_row['stability_score']:.0f})"
    highest_risk = f"{risk_row['system']} (risk score {risk_row['risk_score']:.0f})"

    most_reliable = (
        f"The most reliable conclusion is the comparative stability signal, where {stability_row['system']} currently leads "
        f"and the evidence base is stronger than the efficiency comparison."
    )

    if efficiency_row["efficiency_measurement_status"] != "Measured efficiency":
        not_to_conclude = (
            f"Do not conclude that {efficiency_row['system']} is definitively the most efficient system yet; "
            "the current efficiency ranking is weakened by incomplete nutrient measurement."
        )
    else:
        not_to_conclude = (
            "Do not treat any observed efficiency difference as causal without a harmonized follow-up design."
        )

    validation_text = (
        "Validate the leading systems under a harmonized measurement protocol, especially when the decision compares soil and hydroponic setups."
        if comparability_note
        else "Validate the leading systems over an additional observation window before making a real business decision."
    )

    efficiency_takeaway = (
        f"{efficiency_row['system']} shows the strongest apparent efficiency score, but this remains directional only because nutrient measurement is incomplete and the efficiency signal is unsupported."
        if efficiency_row["efficiency_measurement_status"] == "Unsupported efficiency"
        else f"{efficiency_row['system']} shows the strongest apparent efficiency score, but this remains directional only because nutrient quantities are captured inconsistently."
    )
    stability_takeaway = (
        f"{stability_row['system']} provides the strongest current stability signal. {_stability_detail(stability_row)}"
    )
    risk_takeaway = (
        f"{risk_row['system']} has the highest operational risk, driven by frequent issue days, heavier manual intervention, and observed leak burden."
    )
    most_reliable_insight = (
        f"Stability is the strongest current comparative insight, and {stability_row['system']} leads that dimension."
    )
    not_yet_defensible = (
        "No system can yet be declared definitively most efficient. The current efficiency ranking remains weakened by incomplete nutrient measurement and cross-system comparability limits."
    )

    return {
        "best_efficiency": best_efficiency,
        "best_stability": best_stability,
        "highest_operational_risk": highest_risk,
        "most_reliable_conclusion": most_reliable,
        "what_not_to_conclude": not_to_conclude,
        "validate_before_decision": validation_text,
        "efficiency_takeaway": efficiency_takeaway,
        "stability_takeaway": stability_takeaway,
        "risk_takeaway": risk_takeaway,
        "most_reliable_insight": most_reliable_insight,
        "not_yet_defensible": not_yet_defensible,
    }
