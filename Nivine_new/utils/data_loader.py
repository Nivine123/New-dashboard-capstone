"""Dataset loading, preprocessing, and filter utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from utils.constants import QUALITY_ORDER, ROW_CONFIDENCE_ORDER

DATASET_CANDIDATES = (
    "greenhouse_systems_cleaned(8).csv",
    "greenhouse_systems_cleaned.csv",
)

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
    "unknown",
    "nan",
    "none",
    "not reported",
    "no issue recorded",
    "unspecified",
}

PREPARED_DATA_VERSION = 2


def find_dataset_path(base_dir: Path | None = None) -> Path:
    """Locate the greenhouse CSV using the requested filename first."""

    search_dir = base_dir or Path(__file__).resolve().parents[1]

    for filename in DATASET_CANDIDATES:
        candidate = search_dir / filename
        if candidate.exists():
            return candidate

    matches = sorted(search_dir.glob("greenhouse_systems_cleaned*.csv"))
    if matches:
        return matches[0]

    raise FileNotFoundError(
        "Could not find greenhouse_systems_cleaned(8).csv or a matching greenhouse_systems_cleaned*.csv file."
    )


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
        "issue_flag": False,
        "nutrient_addition_flag": False,
        "manual_intervention_flag": False,
        "weekend_or_aggregate_flag": False,
        "estimated_value_flag": False,
        "core_measurement_missing": False,
        "analysis_ready_water_use_flag": False,
        "sanity_warning_flag": False,
        "age_days_imputed": False,
    }
    for column, default in boolean_defaults.items():
        if column not in frame.columns:
            frame[column] = default
        frame[column] = _normalize_boolean(frame[column])

    numeric_defaults = {
        "water_use_l": np.nan,
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

    frame = df.copy()

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

    frame["observation_date"] = pd.to_datetime(
        frame["observation_date"], errors="coerce"
    ).dt.normalize()

    timestamp = pd.to_datetime(frame["observation_timestamp"], errors="coerce")
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
    return {
        "systems": options["systems"],
        "system_types": options["system_types"],
        "date_range": (
            df["observation_date"].min().date(),
            df["observation_date"].max().date(),
        ),
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
