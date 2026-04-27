"""Dataset loading, preprocessing, and filter utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from utils.constants import QUALITY_ORDER, ROW_CONFIDENCE_ORDER

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIRNAME = "outputs"

DATASET_CANDIDATES = (
    "outputs/cleaned_data.csv",
    "cleaned_data.csv",
    "greenhouse_systems_cleaned(8).csv",
    "greenhouse_systems_cleaned.csv",
)

CLEANING_OUTPUT_FILES = {
    "cleaned_data": "cleaned_data.csv",
    "validation_report": "validation_report.csv",
    "data_quality_summary": "data_quality_summary.csv",
    "rows_needing_review": "rows_needing_review.csv",
    "data_dictionary": "data_dictionary.csv",
    "cleaning_metadata": "cleaning_metadata.json",
}

BOOLEAN_COLUMNS = [
    "manual_water_addition",
    "ph_adjustment_flag",
    "issue_flag",
    "nutrient_addition_flag",
    "manual_intervention_flag",
    "weekend_or_aggregate_flag",
    "estimated_value_flag",
    "harvest_related_flag",
    "end_of_cycle_flag",
    "core_measurement_missing",
    "drop_irrelevant_sparse_row",
    "analysis_ready_water_use_flag",
    "sanity_warning_flag",
    "age_days_imputed",
]

NUMERIC_COLUMNS = [
    "water_in_return_l",
    "water_addition_duration_min",
    "return_now_l",
    "nutrient_a_ml",
    "nutrient_b_ml",
    "nutrient_total_ml",
    "nutrient_a_nft_ml",
    "nutrient_b_nft_ml",
    "nutrient_a_gutters_ml",
    "nutrient_b_gutters_ml",
    "nutrient_a_towers_ml",
    "nutrient_b_towers_ml",
    "ph_down_ml",
    "ph_down_nft_ml",
    "ph_down_gutters_ml",
    "ph_down_towers_ml",
    "water_consumed_l",
    "watered_amount_l",
    "water_use_l",
    "age_days",
    "plant_count",
    "source_row_number",
]

TEXT_COLUMNS = [
    "system",
    "system_type",
    "water_use_basis",
    "leak_flag",
    "leak_severity",
    "leak_locations",
    "plant_name",
    "growth_stage",
    "crop_types",
    "problem_notes",
    "problem_categories",
    "data_quality_status",
]

UNKNOWN_TOKENS = {
    "",
    "-",
    "unknown",
    "nan",
    "none",
    "na",
    "n/a",
    "not reported",
    "no issue recorded",
    "unspecified",
}

PREPARED_DATA_VERSION = 3

SYSTEM_NAME_ALIASES = {
    "A shape and Gutters": "A-shape + Gutters",
    "A-shape and Gutters": "A-shape + Gutters",
    "Towers": "Tower",
}


def find_dataset_path(base_dir: Path | None = None) -> Path:
    """Locate the greenhouse CSV, preferring the notebook's cleaned output."""

    search_dir = base_dir or PROJECT_ROOT

    for filename in DATASET_CANDIDATES:
        candidate = search_dir / filename
        if candidate.exists():
            return candidate

    matches = sorted(search_dir.glob("greenhouse_systems_cleaned*.csv"))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        "Could not find outputs/cleaned_data.csv, cleaned_data.csv, or a greenhouse_systems_cleaned*.csv fallback."
    )


def get_cleaning_outputs_dir(base_dir: Path | None = None) -> Path:
    """Return the project-relative directory used for data-cleaning artifacts."""

    return (base_dir or PROJECT_ROOT) / OUTPUTS_DIRNAME


def get_cleaning_output_paths(base_dir: Path | None = None) -> dict[str, Path]:
    """Build project-relative paths for the optional cleaning-output files."""

    outputs_dir = get_cleaning_outputs_dir(base_dir)
    return {
        name: outputs_dir / filename
        for name, filename in CLEANING_OUTPUT_FILES.items()
    }


@st.cache_data(show_spinner=False)
def _load_optional_csv(path_str: str, modified_time: float) -> tuple[pd.DataFrame, str | None]:
    """Read an optional CSV without letting malformed files crash the app."""

    _ = modified_time
    try:
        return pd.read_csv(path_str), None
    except pd.errors.EmptyDataError:
        return pd.DataFrame(), "File exists but contains no rows."
    except Exception as exc:  # pragma: no cover - defensive UI guard
        return pd.DataFrame(), f"{type(exc).__name__}: {exc}"


@st.cache_data(show_spinner=False)
def _load_optional_json(path_str: str, modified_time: float) -> tuple[dict[str, Any], str | None]:
    """Read an optional JSON metadata file without surfacing stack traces."""

    _ = modified_time
    try:
        with Path(path_str).open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return {}, "Metadata JSON is valid but does not contain an object."
        return payload, None
    except json.JSONDecodeError as exc:
        return {}, f"Malformed JSON: {exc}"
    except Exception as exc:  # pragma: no cover - defensive UI guard
        return {}, f"{type(exc).__name__}: {exc}"


def load_cleaning_outputs(base_dir: Path | None = None) -> dict[str, Any]:
    """Load all cleaning artifacts that exist, with per-file errors and missing-file info."""

    paths = get_cleaning_output_paths(base_dir)
    frames: dict[str, pd.DataFrame] = {}
    metadata: dict[str, Any] = {}
    errors: dict[str, str] = {}
    missing: list[str] = []

    for name, path in paths.items():
        if not path.exists():
            missing.append(name)
            if name != "cleaning_metadata":
                frames[name] = pd.DataFrame()
            continue

        if name == "cleaning_metadata":
            metadata, error = _load_optional_json(str(path), path.stat().st_mtime)
        else:
            frame, error = _load_optional_csv(str(path), path.stat().st_mtime)
            frames[name] = frame

        if error:
            errors[name] = error

    return {
        "paths": paths,
        "frames": frames,
        "metadata": metadata,
        "errors": errors,
        "missing": missing,
    }


def _normalize_boolean(series: pd.Series) -> pd.Series:
    """Safely convert mixed-type truthy columns into booleans."""

    mapping = {
        True: True,
        False: False,
        "true": True,
        "false": False,
        "yes": True,
        "no": False,
        "1": True,
        "0": False,
    }
    if series.dtype == bool:
        return series.fillna(False)

    cleaned = (
        series.astype(str)
        .str.strip()
        .str.lower()
        .replace({"nan": "", "none": ""})
        .map(mapping)
    )
    return cleaned.fillna(False).astype(bool)


def _optional_series(
    frame: pd.DataFrame, column: str, default: Any = np.nan
) -> pd.Series:
    """Return a column or a default-filled series aligned to the frame."""

    if column in frame.columns:
        return frame[column]
    return pd.Series(default, index=frame.index)


def _first_available(frame: pd.DataFrame, columns: list[str], default: Any = np.nan) -> pd.Series:
    """Return the first non-null value across candidate columns."""

    result = pd.Series(np.nan, index=frame.index)
    for column in columns:
        if column in frame.columns:
            result = result.combine_first(frame[column])
    if not (isinstance(default, float) and pd.isna(default)):
        result = result.fillna(default)
    return result


def _clean_text(series: pd.Series, default: str = "Unknown") -> pd.Series:
    """Normalize text fields while preserving useful source values."""

    cleaned = series.fillna("").astype(str).str.strip()
    missing = cleaned.str.lower().isin(UNKNOWN_TOKENS)
    return cleaned.mask(missing, default)


def _has_text(series: pd.Series) -> pd.Series:
    """Return True where a text-like source value carries useful information."""

    return ~_clean_text(series, default="").eq("")


def _extract_first_quantity(series: pd.Series, skip_pattern: str | None = None) -> pd.Series:
    """Extract a conservative first numeric quantity from messy source text."""

    text = series.fillna("").astype(str)
    extracted = pd.to_numeric(
        text.str.extract(r"(-?\d+(?:\.\d+)?)", expand=False),
        errors="coerce",
    )
    if skip_pattern:
        extracted = extracted.mask(text.str.contains(skip_pattern, case=False, na=False))
    return extracted


def _extract_age_days(series: pd.Series) -> pd.Series:
    """Convert simple age strings such as '10 days' or '3-4 weeks' to days."""

    text = series.fillna("").astype(str).str.lower()
    ranges = text.str.extract(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
    first = pd.to_numeric(ranges[0], errors="coerce")
    second = pd.to_numeric(ranges[1], errors="coerce")
    single = pd.to_numeric(
        text.str.extract(r"(\d+(?:\.\d+)?)", expand=False), errors="coerce"
    )
    value = ((first + second) / 2).combine_first(single)
    value = value.mask(text.str.contains("week", na=False), value * 7)
    return value


def _categorize_problem_notes(value: Any) -> str:
    """Create lightweight issue categories from greenhouse free text."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "No issue recorded"

    text = str(value).strip().lower()
    if not text or text in UNKNOWN_TOKENS:
        return "No issue recorded"

    categories: list[str] = []
    patterns = {
        "Leak / water loss": r"leak|spill|lost|missing water",
        "Pump / return issue": r"pump|return",
        "Power / lighting": r"electric|light|power",
        "Water stress": r"stress|dry|evaporation|water room",
        "Crop / plant health": r"weed|harvest|basil|lettuce|pepper|kale|plant",
        "Manual operation": r"manual|manually|door",
    }
    for label, pattern in patterns.items():
        if re.search(pattern, text):
            categories.append(label)

    return "; ".join(categories) if categories else "Other issue"


def _classify_leak_severity(raw_leak: pd.Series, leak_reported: pd.Series) -> pd.Series:
    """Classify leak severity from the cleaned boolean and source phrase."""

    text = raw_leak.fillna("").astype(str).str.lower()
    severity = pd.Series("Unknown", index=raw_leak.index)
    severity = severity.mask(leak_reported.eq(False), "No Leak")
    severity = severity.mask(
        leak_reported.eq(True)
        & text.str.contains(r"major|alot|a lot|cylinder|lost|spill", na=False),
        "Major",
    )
    severity = severity.mask(leak_reported.eq(True) & severity.eq("Unknown"), "Minor")
    return severity


def _derive_cleaning_output_aliases(frame: pd.DataFrame) -> pd.DataFrame:
    """Adapt the notebook's cleaned output to the dashboard's analysis schema."""

    if "input_source_sheet" not in frame.columns:
        return frame

    result = frame.copy()
    sheet = _clean_text(_optional_series(result, "input_source_sheet"), "Unknown")
    result["system"] = sheet.replace(SYSTEM_NAME_ALIASES)
    result["system_type"] = np.where(result["system"].eq("Conventional"), "Soil", "Hydroponic")

    result["observation_date"] = pd.to_datetime(
        _first_available(result, ["date", "date_raw_source", "observed_at"]),
        errors="coerce",
    ).dt.normalize()
    result["observation_time"] = _clean_text(_optional_series(result, "time"), "")
    result["observation_timestamp"] = pd.to_datetime(
        _first_available(result, ["observed_at", "input_observed_at"]),
        errors="coerce",
    )

    consumed = pd.to_numeric(
        _optional_series(result, "how_much_consumed_liters"), errors="coerce"
    )
    watered = pd.to_numeric(_optional_series(result, "watered_amount_liters"), errors="coerce")
    result["water_consumed_l"] = consumed
    result["watered_amount_l"] = watered
    result["water_use_l"] = consumed.combine_first(watered)
    result["water_use_basis"] = np.select(
        [consumed.notna(), watered.notna()],
        ["Recorded consumption", "Applied watering"],
        default="No water quantity",
    )

    result["water_in_return_l"] = pd.to_numeric(
        _optional_series(result, "water_in_return_liters"), errors="coerce"
    )
    result["return_now_l"] = pd.to_numeric(
        _optional_series(result, "return_now_liters"), errors="coerce"
    )
    result["water_addition_duration_min"] = pd.to_numeric(
        _optional_series(result, "mins_added_minutes"), errors="coerce"
    )
    result["ph_down_ml"] = pd.to_numeric(
        _optional_series(result, "ph_down_milliliters"), errors="coerce"
    )

    raw_plant_count = _first_available(
        result, ["how_many_plants_planted", "how_many_planted"], default=""
    )
    result["plant_count"] = _extract_first_quantity(
        raw_plant_count, skip_pattern=r"all except|empty|tower|unit"
    )
    result["age_days"] = _extract_age_days(_optional_series(result, "age", ""))
    result["age_days_imputed"] = False

    result["plant_name"] = _clean_text(_optional_series(result, "plant"), "Unknown")
    result["growth_stage"] = _clean_text(
        _optional_series(result, "seed_or_seedling"), "Unknown"
    )
    result["crop_types"] = result["plant_name"]
    result["leak_locations"] = _clean_text(
        _optional_series(result, "leak_or_no"), "Unknown"
    )

    problem_text = _first_available(
        result, ["problem_notes", "problems", "problems_faced"], default=""
    )
    result["problem_notes"] = _clean_text(problem_text, "No issue recorded")
    result["problem_categories"] = result["problem_notes"].apply(_categorize_problem_notes)
    problem_present = _has_text(problem_text)

    review_flag = _normalize_boolean(_optional_series(result, "needs_review", False))
    result["needs_review"] = review_flag
    review_reasons = _clean_text(_optional_series(result, "review_reasons"), "")
    outlier_columns = [column for column in result.columns if column.endswith("_possible_outlier")]
    outlier_flag = (
        result[outlier_columns].apply(_normalize_boolean).any(axis=1)
        if outlier_columns
        else pd.Series(False, index=result.index)
    )

    weekend_text = (
        _clean_text(_optional_series(result, "how_much_consumed"), "")
        + " "
        + _clean_text(_optional_series(result, "watered_amount"), "")
        + " "
        + review_reasons
    ).str.lower()
    result["weekend_or_aggregate_flag"] = weekend_text.str.contains(
        r"weekend|\b\d+\s*days?\b|aggregate", na=False
    )
    result["estimated_value_flag"] = review_reasons.str.contains(
        r"context|uncertainty|ambiguous|requires_review", case=False, na=False
    )
    result["core_measurement_missing"] = result["observation_date"].isna() | result["water_use_l"].isna()
    result["sanity_warning_flag"] = review_flag | outlier_flag
    result["analysis_ready_water_use_flag"] = (
        result["water_use_l"].notna()
        & ~review_flag
        & ~outlier_flag
        & result["observation_date"].notna()
    )

    result["manual_water_addition"] = (
        _clean_text(_optional_series(result, "mins_added"), "")
        .str.contains("manual", case=False, na=False)
        | _clean_text(_optional_series(result, "mins_added_parse_status"), "")
        .str.contains("manual", case=False, na=False)
    )
    result["ph_adjustment_flag"] = result["ph_down_ml"].notna() | _has_text(
        _optional_series(result, "ph_down")
    )
    result["nutrient_addition_flag"] = _has_text(
        _optional_series(result, "nutrient_solution")
    )
    result["issue_flag"] = problem_present
    result["manual_intervention_flag"] = (
        result["manual_water_addition"]
        | result["ph_adjustment_flag"]
        | result["nutrient_addition_flag"]
        | result["issue_flag"]
    )

    leak_source = _optional_series(result, "leak_reported")
    leak_text = leak_source.fillna("").astype(str).str.strip().str.lower()
    leak_yes = leak_source.eq(True) | leak_text.isin(["true", "yes", "y", "1"])
    leak_no = leak_source.eq(False) | leak_text.isin(["false", "no", "n", "0"])
    leak_bool = pd.Series(np.nan, index=result.index, dtype="object")
    leak_bool = leak_bool.mask(leak_yes, True).mask(leak_no, False)
    result["leak_flag"] = np.select(
        [leak_bool.eq(True), leak_bool.eq(False)],
        ["Yes", "No"],
        default="Unknown",
    )
    result["leak_severity"] = _classify_leak_severity(
        _optional_series(result, "leak_or_no"), leak_bool
    )

    result["nutrient_total_ml"] = pd.to_numeric(
    _optional_series(result, "nutrient_solution_milliliters"), errors="coerce"
)
    result["harvest_related_flag"] = problem_text.fillna("").astype(str).str.contains(
        "harvest", case=False, na=False
    )
    result["end_of_cycle_flag"] = problem_text.fillna("").astype(str).str.contains(
        "end of cycle", case=False, na=False
    )
    result["drop_irrelevant_sparse_row"] = False

    status = pd.Series("Usable", index=result.index)
    status = status.mask(result["weekend_or_aggregate_flag"], "Aggregate")
    status = status.mask(result["estimated_value_flag"], "Estimated")
    status = status.mask(result["core_measurement_missing"], "Event Only")
    status = status.mask(review_flag, "Review Required")
    result["data_quality_status"] = status

    if "dataset_row_id" not in result.columns:
        result["dataset_row_id"] = np.arange(1, len(result) + 1)

    return result


def split_tokens(value: Any, preserve_unknown: bool = False) -> list[str]:
    """Split comma or semicolon separated categorical fields into clean tokens."""

    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    text = str(value).replace("/", ";").replace(",", ";")
    tokens = [part.strip() for part in text.split(";") if part.strip()]
    if preserve_unknown:
        return tokens

    cleaned = [token for token in tokens if token.strip().lower() not in UNKNOWN_TOKENS]
    return cleaned


def _is_known_text(series: pd.Series) -> pd.Series:
    values = series.fillna("").astype(str).str.strip().str.lower()
    return ~values.isin(UNKNOWN_TOKENS)


def _classify_row_confidence(frame: pd.DataFrame) -> pd.Series:
    strong_mask = (
        frame["data_quality_status"].eq("Usable")
        & frame["analysis_ready_water_use_flag"]
        & ~frame["estimated_value_flag"]
        & ~frame["weekend_or_aggregate_flag"]
        & ~frame["core_measurement_missing"]
        & ~frame["sanity_warning_flag"]
    )

    directional_mask = (
        frame["data_quality_status"].isin(["Usable", "Aggregate", "Estimated"])
        & ~frame["core_measurement_missing"]
    )

    return np.select(
        [strong_mask, directional_mask],
        ["Strong evidence", "Directional evidence"],
        default="Limited evidence",
    )


def _first_non_null(*series_list: pd.Series) -> pd.Series:
    result = series_list[0].copy()
    for series in series_list[1:]:
        result = result.combine_first(series)
    return result


def _sum_if_any(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    subset = frame.reindex(columns=columns)
    summed = subset.fillna(0).sum(axis=1)
    return summed.where(subset.notna().any(axis=1), np.nan)


def ensure_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill derived fields when an older cached prepared dataset is loaded."""

    frame = df.copy()

    text_defaults = {
        "system": "Unknown",
        "system_type": "Unknown",
        "water_use_basis": "Unknown",
        "leak_flag": "Unknown",
        "leak_severity": "Unknown",
        "plant_name": "Unknown",
        "growth_stage": "Unknown",
        "crop_types": "Unknown",
        "problem_categories": "Unknown",
        "leak_locations": "Unknown",
        "data_quality_status": "Unknown",
    }
    for column, default in text_defaults.items():
        if column not in frame.columns:
            frame[column] = default

    boolean_defaults = {
        "manual_water_addition": False,
        "ph_adjustment_flag": False,
        "issue_flag": False,
        "nutrient_addition_flag": False,
        "manual_intervention_flag": False,
        "weekend_or_aggregate_flag": False,
        "estimated_value_flag": False,
        "core_measurement_missing": False,
        "analysis_ready_water_use_flag": False,
        "sanity_warning_flag": False,
        "age_days_imputed": False,
        "harvest_related_flag": False,
        "end_of_cycle_flag": False,
        "drop_irrelevant_sparse_row": False,
    }
    for column, default in boolean_defaults.items():
        if column not in frame.columns:
            frame[column] = default
        frame[column] = _normalize_boolean(frame[column])

    numeric_defaults = {
        "water_use_l": np.nan,
        "water_in_return_l": np.nan,
        "return_now_l": np.nan,
        "water_addition_duration_min": np.nan,
        "plant_count": np.nan,
        "nutrient_total_ml": np.nan,
        "ph_down_ml": np.nan,
    }
    for column, default in numeric_defaults.items():
        if column not in frame.columns:
            frame[column] = default

    if "observation_date" in frame.columns:
        frame["observation_date"] = pd.to_datetime(
            frame["observation_date"], errors="coerce"
        ).dt.normalize()
    else:
        frame["observation_date"] = pd.NaT

    if "observation_timestamp" not in frame.columns:
        frame["observation_timestamp"] = pd.NaT
    timestamp = pd.to_datetime(frame["observation_timestamp"], errors="coerce")
    if "observation_time" not in frame.columns:
        frame["observation_time"] = ""
    combined = pd.to_datetime(
        frame["observation_date"].dt.strftime("%Y-%m-%d").fillna("")
        + " "
        + frame["observation_time"].fillna("").astype(str),
        errors="coerce",
    )
    frame["observation_timestamp"] = timestamp.fillna(combined)

    frame["leak_reported_flag"] = frame["leak_flag"].isin(["Yes", "No"])
    frame["leak_incident_flag"] = frame["leak_flag"].eq("Yes")
    frame["issue_incident_flag"] = _normalize_boolean(frame["issue_flag"])
    frame["water_measurement_available"] = frame["water_use_l"].notna()
    frame["manual_water_activity_flag"] = (
        frame["manual_water_addition"] | frame["water_addition_duration_min"].notna()
    )

    generic_nutrient_pair = _sum_if_any(frame, ["nutrient_a_ml", "nutrient_b_ml"])
    nft_nutrient_pair = _sum_if_any(frame, ["nutrient_a_nft_ml", "nutrient_b_nft_ml"])
    gutters_nutrient_pair = _sum_if_any(
        frame, ["nutrient_a_gutters_ml", "nutrient_b_gutters_ml"]
    )
    towers_nutrient_pair = _sum_if_any(
        frame, ["nutrient_a_towers_ml", "nutrient_b_towers_ml"]
    )
    specific_nutrient_pair = _first_non_null(
        nft_nutrient_pair, gutters_nutrient_pair, towers_nutrient_pair
    )
    frame["nutrient_effective_ml"] = _first_non_null(
        frame.get("nutrient_total_ml", pd.Series(np.nan, index=frame.index)),
        generic_nutrient_pair,
        specific_nutrient_pair,
    )
    frame["nutrient_measurement_available"] = frame["nutrient_effective_ml"].notna()

    specific_ph_down = _first_non_null(
        frame.get("ph_down_nft_ml", pd.Series(np.nan, index=frame.index)),
        frame.get("ph_down_gutters_ml", pd.Series(np.nan, index=frame.index)),
        frame.get("ph_down_towers_ml", pd.Series(np.nan, index=frame.index)),
    )
    frame["ph_down_effective_ml"] = _first_non_null(
        frame.get("ph_down_ml", pd.Series(np.nan, index=frame.index)),
        specific_ph_down,
    )
    frame["ph_measurement_available"] = frame["ph_down_effective_ml"].notna()

    frame["usable_row_flag"] = frame["data_quality_status"].eq("Usable")
    frame["clean_measurement_flag"] = (
        frame["analysis_ready_water_use_flag"]
        & ~frame["estimated_value_flag"]
        & ~frame["weekend_or_aggregate_flag"]
        & ~frame["core_measurement_missing"]
    )
    frame["row_confidence_band"] = _classify_row_confidence(frame)

    frame["crop_tokens"] = frame["crop_types"].apply(split_tokens)
    frame["problem_category_tokens"] = frame["problem_categories"].apply(split_tokens)
    frame["leak_location_tokens"] = frame["leak_locations"].apply(split_tokens)

    frame["plant_name_known_flag"] = _is_known_text(frame["plant_name"])
    frame["growth_stage_known_flag"] = _is_known_text(frame["growth_stage"])
    frame["crop_known_flag"] = _is_known_text(frame["crop_types"])
    frame["plant_count_known_flag"] = frame["plant_count"].notna()

    frame["observation_week"] = frame["observation_date"].dt.to_period("W-SUN").apply(
        lambda period: period.start_time if pd.notna(period) else pd.NaT
    )
    frame["observation_month"] = frame["observation_date"].dt.to_period("M").apply(
        lambda period: period.start_time if pd.notna(period) else pd.NaT
    )
    frame["weekday_name"] = frame["observation_date"].dt.day_name()
    frame["is_weekend"] = frame["observation_date"].dt.dayofweek.ge(5)

    if "dataset_row_id" not in frame.columns:
        frame["dataset_row_id"] = np.arange(1, len(frame) + 1)

    return frame


def preprocess_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize types and create analysis-ready derived fields."""

    frame = _derive_cleaning_output_aliases(df)

    for column in NUMERIC_COLUMNS:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    for column in BOOLEAN_COLUMNS:
        if column in frame.columns:
            frame[column] = _normalize_boolean(frame[column])

    for column in TEXT_COLUMNS:
        if column in frame.columns:
            frame[column] = (
                frame[column]
                .fillna("Unknown")
                .astype(str)
                .str.strip()
                .replace({"": "Unknown"})
            )

    if "observation_date" not in frame.columns:
        frame["observation_date"] = pd.NaT
    frame["observation_date"] = pd.to_datetime(
        frame["observation_date"], errors="coerce"
    ).dt.normalize()

    if "observation_timestamp" not in frame.columns:
        frame["observation_timestamp"] = pd.NaT
    timestamp = pd.to_datetime(frame["observation_timestamp"], errors="coerce")
    if "observation_time" not in frame.columns:
        frame["observation_time"] = ""
    combined = pd.to_datetime(
        frame["observation_date"].dt.strftime("%Y-%m-%d").fillna("")
        + " "
        + frame["observation_time"].fillna("").astype(str),
        errors="coerce",
    )
    frame["observation_timestamp"] = timestamp.fillna(combined)

    return ensure_derived_columns(frame)


@st.cache_data(show_spinner=False)
def load_prepared_dataset(
    path_str: str, modified_time: float, prepared_data_version: int
) -> pd.DataFrame:
    """Load the CSV with caching tied to the file modification timestamp."""

    _ = modified_time
    _ = prepared_data_version
    raw = pd.read_csv(path_str)
    return preprocess_dataset(raw)


def load_greenhouse_dataset() -> tuple[pd.DataFrame, Path]:
    path = find_dataset_path()
    prepared = load_prepared_dataset(
        str(path), path.stat().st_mtime, PREPARED_DATA_VERSION
    )
    prepared = ensure_derived_columns(prepared)
    return prepared, path


def available_filter_options(df: pd.DataFrame) -> dict[str, list[Any]]:
    crop_options = sorted({token for tokens in df["crop_tokens"] for token in tokens})

    plant_options = sorted(
        {
            value
            for value in df["plant_name"].dropna().unique().tolist()
            if str(value).strip().lower() not in UNKNOWN_TOKENS
        }
    )

    return {
        "systems": sorted(df["system"].dropna().unique().tolist()),
        "system_types": sorted(df["system_type"].dropna().unique().tolist()),
        "crops": crop_options,
        "plant_names": plant_options,
        "quality_status": [
            status for status in QUALITY_ORDER if status in df["data_quality_status"].unique()
        ],
        "row_confidence_bands": [
            band for band in ROW_CONFIDENCE_ORDER if band in df["row_confidence_band"].unique()
        ],
    }


def default_filters(df: pd.DataFrame) -> dict[str, Any]:
    options = available_filter_options(df)
    valid_dates = df["observation_date"].dropna()
    if valid_dates.empty:
        today = pd.Timestamp.today().date()
        date_range = (today, today)
    else:
        date_range = (valid_dates.min().date(), valid_dates.max().date())

    return {
        "systems": options["systems"],
        "system_types": options["system_types"],
        "date_range": date_range,
        "crop_types": [],
        "plant_names": [],
        "quality_status": options["quality_status"],
        "row_confidence_bands": options["row_confidence_bands"],
        "include_estimated": True,
        "include_aggregate": True,
    }


def _contains_selected_tokens(series: pd.Series, selected_tokens: list[str]) -> pd.Series:
    selected = set(selected_tokens)
    return series.apply(lambda tokens: bool(set(tokens) & selected))


def filter_dataset(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Apply sidebar filters without mutating the cached source data."""

    filtered = df.copy()

    if filters.get("systems"):
        filtered = filtered[filtered["system"].isin(filters["systems"])]

    if filters.get("system_types"):
        filtered = filtered[filtered["system_type"].isin(filters["system_types"])]

    if filtered["observation_date"].notna().any():
        start_date, end_date = filters["date_range"]
        start_ts = pd.to_datetime(start_date)
        end_ts = pd.to_datetime(end_date)
        filtered = filtered[
            filtered["observation_date"].between(start_ts, end_ts, inclusive="both")
        ]

    if filters.get("crop_types"):
        filtered = filtered[
            _contains_selected_tokens(filtered["crop_tokens"], filters["crop_types"])
        ]

    if filters.get("plant_names"):
        filtered = filtered[filtered["plant_name"].isin(filters["plant_names"])]

    if filters.get("quality_status"):
        filtered = filtered[filtered["data_quality_status"].isin(filters["quality_status"])]

    if filters.get("row_confidence_bands"):
        filtered = filtered[
            filtered["row_confidence_band"].isin(filters["row_confidence_bands"])
        ]

    if not filters.get("include_estimated", True):
        filtered = filtered[~filtered["estimated_value_flag"]]

    if not filters.get("include_aggregate", True):
        filtered = filtered[~filtered["weekend_or_aggregate_flag"]]

    return filtered.sort_values(["observation_date", "observation_timestamp", "system"])


def build_comparability_note(df: pd.DataFrame) -> str | None:
    """Highlight when comparisons should be read cautiously."""

    if df.empty:
        return None

    notes: list[str] = []
    if df["system_type"].nunique() > 1:
        notes.append(
            "Cross-system efficiency comparisons mix hydroponic and soil systems, so treat them as directional rather than directly equivalent."
        )

    if df["water_use_basis"].nunique() > 1:
        notes.append(
            "Water use is measured on different bases in the dataset: hydroponic systems rely on recorded consumption, while the Conventional system uses applied watering."
        )

    if notes:
        return " ".join(notes)

    return None
