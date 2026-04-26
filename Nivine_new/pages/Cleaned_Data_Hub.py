"""Cleaned data operations page for notebook outputs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.charts import (
    feature_availability_heatmap,
    pipeline_flow_chart,
    review_readiness_funnel,
)
from utils.data_loader import load_cleaning_outputs
from utils.metrics import format_pct
from utils.ui import (
    build_page_context,
    render_chart_conclusion,
    render_hero,
    render_metric_card,
)


KEY_REVIEW_COLUMNS = [
    "raw_record_id",
    "source_row_number",
    "date",
    "time",
    "input_source_sheet",
    "needs_review",
    "review_reasons",
    "water_in_return",
    "mins_added",
    "return_now",
    "how_much_consumed",
    "watered_amount",
    "leak_or_no",
    "plant",
    "problem_notes",
    "planting_notes",
]

KEY_EXPLORER_COLUMNS = [
    "raw_record_id",
    "date",
    "time",
    "input_source_sheet",
    "needs_review",
    "review_reasons",
    "water_in_return_liters",
    "return_now_liters",
    "how_much_consumed_liters",
    "watered_amount_liters",
    "mins_added_minutes",
    "ph_down_milliliters",
    "leak_reported",
    "plant",
    "seed_or_seedling",
    "problem_notes",
]


def _first_existing(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in frame.columns:
            return column
    return None


def _to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def _search_frame(frame: pd.DataFrame, query: str) -> pd.DataFrame:
    if frame.empty or not query.strip():
        return frame

    terms = query.strip().lower().split()
    text_frame = frame.astype(str).apply(lambda column: column.str.lower())
    mask = pd.Series(True, index=frame.index)
    for term in terms:
        mask &= text_frame.apply(lambda column: column.str.contains(term, na=False)).any(axis=1)
    return frame[mask]


def _filter_by_date(
    frame: pd.DataFrame, date_column: str | None, key_prefix: str
) -> pd.DataFrame:
    if frame.empty or date_column is None:
        return frame

    dates = pd.to_datetime(frame[date_column], errors="coerce").dt.date
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return frame

    selected_range = st.slider(
        "Date range",
        min_value=valid_dates.min(),
        max_value=valid_dates.max(),
        value=(valid_dates.min(), valid_dates.max()),
        key=f"{key_prefix}_date_range",
    )
    start_date, end_date = selected_range
    return frame[dates.between(start_date, end_date, inclusive="both")]


def _reason_options(frame: pd.DataFrame) -> list[str]:
    if "review_reasons" not in frame.columns or frame.empty:
        return []

    reasons: set[str] = set()
    for value in frame["review_reasons"].dropna().astype(str):
        for reason in value.replace(",", ";").split(";"):
            cleaned = reason.strip()
            if cleaned and cleaned.lower() not in {"nan", "none"}:
                reasons.add(cleaned)
    return sorted(reasons)


def _filter_by_review_reason(frame: pd.DataFrame, selected: list[str]) -> pd.DataFrame:
    if not selected or "review_reasons" not in frame.columns or frame.empty:
        return frame

    pattern = "|".join(re.escape(reason) for reason in selected)
    return frame[frame["review_reasons"].fillna("").astype(str).str.contains(pattern, regex=True)]


def _safe_count(frame: pd.DataFrame, column: str, value: Any | None = None) -> int:
    if frame.empty or column not in frame.columns:
        return 0
    if value is None:
        return int(frame[column].notna().sum())
    return int(frame[column].eq(value).sum())


def _sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_metadata(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_sanitize_metadata(item) for item in value]
    if isinstance(value, str) and value.startswith("/"):
        return Path(value).name
    return value


def _download_button(label: str, frame: pd.DataFrame, filename: str) -> None:
    if frame.empty:
        st.caption(f"No rows available for {label.lower()}.")
        return
    st.download_button(
        label,
        data=_to_csv_bytes(frame),
        file_name=filename,
        mime="text/csv",
    )


context = build_page_context("Cleaned Data Hub")
prepared_df = context["source_df"]
artifacts = load_cleaning_outputs()
frames: dict[str, pd.DataFrame] = artifacts["frames"]
metadata: dict[str, Any] = artifacts["metadata"]

cleaned_raw = frames.get("cleaned_data", pd.DataFrame())
if cleaned_raw.empty:
    cleaned_raw = prepared_df.copy()

validation = frames.get("validation_report", pd.DataFrame())
quality = frames.get("data_quality_summary", pd.DataFrame())
review_queue = frames.get("rows_needing_review", pd.DataFrame())
dictionary = frames.get("data_dictionary", pd.DataFrame())

if review_queue.empty and "needs_review" in cleaned_raw.columns:
    review_flag = cleaned_raw["needs_review"].astype(str).str.lower().isin(["true", "1", "yes"])
    review_queue = cleaned_raw[review_flag].copy()

render_hero(
    "Cleaned Data Hub",
    (
        "Operational view of the notebook's cleaned data, validation checks, review queue, dictionary, "
        "and pipeline metadata using project-relative cleaning outputs."
    ),
    eyebrow="Data Cleaning Outputs",
)

if artifacts["missing"]:
    missing_names = ", ".join(artifacts["missing"])
    st.info(f"Optional cleaning outputs not found: {missing_names}. Available sections will still render.")

if artifacts["errors"]:
    for name, error in artifacts["errors"].items():
        st.warning(f"{name}: {error}")

validation_counts = (
    validation["severity"].value_counts().to_dict()
    if not validation.empty and "severity" in validation.columns
    else {}
)
review_count = len(review_queue)
review_share = review_count / len(cleaned_raw) if len(cleaned_raw) else None
domain_info = metadata.get("domain", {}) if isinstance(metadata.get("domain"), dict) else {}

cards = [
    ("Cleaned rows", f"{len(cleaned_raw):,}", "Rows loaded from the primary cleaned data output."),
    ("Cleaned columns", f"{cleaned_raw.shape[1]:,}", "Columns available in the cleaned data output."),
    ("Rows needing review", f"{review_count:,}", f"{format_pct(review_share)} of cleaned rows."),
    ("Validation warnings", f"{validation_counts.get('warning', 0):,}", "Warning-level checks reported by the cleaner."),
    ("Validation failures", f"{validation_counts.get('fail', 0):,}", "Fail-level checks reported by the cleaner."),
    (
        "Domain signal",
        str(domain_info.get("domain", "Unknown")),
        f"{domain_info.get('hydroponic_score', 'N/A')} greenhouse/hydroponic column matches.",
    ),
]

for start in range(0, len(cards), 3):
    columns = st.columns(3, gap="medium")
    for column, card in zip(columns, cards[start : start + 3]):
        with column:
            render_metric_card(*card)

st.markdown("### Pipeline and readiness diagrams")
diagram_left, diagram_right = st.columns(2, gap="large")
with diagram_left:
    st.plotly_chart(
        pipeline_flow_chart(
            cleaned_rows=len(cleaned_raw),
            validation_rows=len(validation),
            quality_rows=len(quality),
            review_rows=len(review_queue),
            dictionary_rows=len(dictionary),
            has_metadata=bool(metadata),
        ),
        width="stretch",
    )
    render_chart_conclusion(
        "How the cleaning notebook outputs feed the deployed Streamlit app.",
        "The dashboard is deployment-ready because the primary cleaned data and optional report artifacts are available inside the project.",
    )
with diagram_right:
    st.plotly_chart(review_readiness_funnel(prepared_df), width="stretch")
    render_chart_conclusion(
        "How many rows remain after water-readiness, warning, and review checks.",
        "Rows needing review are not discarded; they are surfaced so decisions can distinguish usable evidence from records requiring human confirmation.",
    )

st.plotly_chart(feature_availability_heatmap(prepared_df), width="stretch")
render_chart_conclusion(
    "The share of rows with key analytical fields populated for each system.",
    "Field coverage explains why some comparisons are strong while others must stay directional.",
)


st.markdown("### Validation and data quality")
validation_left, validation_right = st.columns(2, gap="large")

with validation_left:
    st.markdown("#### Validation report")
    if validation.empty:
        st.info("No validation report rows are available.")
    elif {"check", "severity", "passed", "details"}.issubset(validation.columns):
        validation_summary = (
            validation.groupby(["severity", "passed"], dropna=False)
            .size()
            .reset_index(name="checks")
        )
        fig = px.bar(
            validation_summary,
            x="severity",
            y="checks",
            color="passed",
            text="checks",
            title="Validation checks by severity",
            color_discrete_map={True: "#2A9D8F", False: "#E76F51", "True": "#2A9D8F", "False": "#E76F51"},
        )
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        render_chart_conclusion(
            "Validation checks grouped by severity and pass/fail status.",
            "The app can separate checks that passed from warnings or failures before promoting any analytical conclusion.",
        )
        st.dataframe(validation, width="stretch", hide_index=True)
    else:
        st.warning("Validation report is present but does not have the expected columns.")
        st.dataframe(validation, width="stretch", hide_index=True)

with validation_right:
    st.markdown("#### Quality summary")
    if quality.empty:
        st.info("No data quality summary rows are available.")
    elif {"area", "finding", "count", "severity"}.issubset(quality.columns):
        quality_view = quality.copy()
        quality_view["count_numeric"] = pd.to_numeric(quality_view["count"], errors="coerce")
        severity_counts = (
            quality_view.groupby("severity", dropna=False)
            .size()
            .reset_index(name="findings")
        )
        fig = px.bar(
            severity_counts,
            x="severity",
            y="findings",
            color="severity",
            text="findings",
            title="Quality findings by severity",
            color_discrete_map={"info": "#2A9D8F", "warning": "#E9C46A", "fail": "#E76F51"},
        )
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig, width="stretch")
        render_chart_conclusion(
            "Quality findings grouped by severity.",
            "Warning-heavy areas should guide review priorities, while info-level findings provide context without blocking analysis.",
        )

        warning_rows = quality_view[quality_view["severity"].astype(str).str.lower().eq("warning")]
        warning_rows = warning_rows.sort_values("count_numeric", ascending=False, na_position="last")
        st.dataframe(warning_rows.head(20), width="stretch", hide_index=True)
    else:
        st.warning("Data quality summary is present but does not have the expected columns.")
        st.dataframe(quality, width="stretch", hide_index=True)


st.markdown("### Review queue")
if review_queue.empty:
    st.success("No rows are currently flagged for human review.")
else:
    queue = review_queue.copy()
    queue_system_col = _first_existing(queue, ["input_source_sheet", "system"])
    queue_date_col = _first_existing(queue, ["date", "observed_at", "input_observed_at"])

    q1, q2, q3 = st.columns([1, 1, 1.2], gap="medium")
    with q1:
        if queue_system_col:
            system_values = sorted(queue[queue_system_col].dropna().astype(str).unique().tolist())
            selected_systems = st.multiselect(
                "System / sheet",
                options=system_values,
                default=system_values,
                key="review_system_filter",
            )
            queue = queue[queue[queue_system_col].astype(str).isin(selected_systems)]
    with q2:
        selected_reasons = st.multiselect(
            "Review reason",
            options=_reason_options(queue),
            default=[],
            key="review_reason_filter",
        )
        queue = _filter_by_review_reason(queue, selected_reasons)
    with q3:
        queue_search = st.text_input("Search review rows", key="review_search")
        queue = _search_frame(queue, queue_search)

    queue = _filter_by_date(queue, queue_date_col, "review")
    display_columns = [column for column in KEY_REVIEW_COLUMNS if column in queue.columns]
    if not display_columns:
        display_columns = queue.columns[: min(12, len(queue.columns))].tolist()

    st.caption(f"{len(queue):,} review rows shown.")
    st.dataframe(queue[display_columns], width="stretch", hide_index=True)
    _download_button("Download filtered review queue", queue, "filtered_review_queue.csv")


st.markdown("### Cleaned data explorer")
explorer = cleaned_raw.copy()
explorer_system_col = _first_existing(explorer, ["input_source_sheet", "system"])
explorer_date_col = _first_existing(explorer, ["date", "observed_at", "input_observed_at"])

e1, e2, e3 = st.columns([1, 1, 1.2], gap="medium")
with e1:
    if explorer_system_col:
        systems = sorted(explorer[explorer_system_col].dropna().astype(str).unique().tolist())
        selected_systems = st.multiselect(
            "Explorer system / sheet",
            options=systems,
            default=systems,
            key="explorer_system_filter",
        )
        explorer = explorer[explorer[explorer_system_col].astype(str).isin(selected_systems)]
with e2:
    if "needs_review" in explorer.columns:
        review_mode = st.selectbox(
            "Review status",
            options=["All rows", "Needs review", "No review flag"],
            key="explorer_review_filter",
        )
        review_bool = explorer["needs_review"].astype(str).str.lower().isin(["true", "1", "yes"])
        if review_mode == "Needs review":
            explorer = explorer[review_bool]
        elif review_mode == "No review flag":
            explorer = explorer[~review_bool]
with e3:
    explorer_search = st.text_input("Search cleaned data", key="explorer_search")
    explorer = _search_frame(explorer, explorer_search)

explorer = _filter_by_date(explorer, explorer_date_col, "explorer")
default_explorer_columns = [column for column in KEY_EXPLORER_COLUMNS if column in explorer.columns]
if not default_explorer_columns:
    default_explorer_columns = explorer.columns[: min(16, len(explorer.columns))].tolist()

selected_columns = st.multiselect(
    "Columns to display",
    options=explorer.columns.tolist(),
    default=default_explorer_columns,
    key="explorer_columns",
)
if not selected_columns:
    selected_columns = default_explorer_columns

st.caption(f"{len(explorer):,} cleaned rows shown.")
st.dataframe(explorer[selected_columns], width="stretch", hide_index=True)
d1, d2 = st.columns(2, gap="medium")
with d1:
    _download_button("Download filtered cleaned data", explorer, "filtered_cleaned_data.csv")
with d2:
    _download_button("Download full cleaned data", cleaned_raw, "cleaned_data.csv")


st.markdown("### Greenhouse operating signals")
chart_source = prepared_df.copy()
water_chart = chart_source[
    chart_source["observation_date"].notna() & chart_source["water_use_l"].notna()
]
ph_chart = chart_source[
    chart_source["observation_date"].notna() & chart_source["ph_down_ml"].notna()
]
duration_chart = chart_source[chart_source["water_addition_duration_min"].notna()]

domain_left, domain_right = st.columns(2, gap="large")
with domain_left:
    if water_chart.empty:
        st.info("No water quantity columns are available for a time-series chart.")
    else:
        water_daily = (
            water_chart.groupby(["observation_date", "system", "water_use_basis"], as_index=False)
            .agg(water_use_l=("water_use_l", "sum"))
        )
        fig = px.line(
            water_daily,
            x="observation_date",
            y="water_use_l",
            color="system",
            line_dash="water_use_basis",
            markers=True,
            title="Water use over time",
        )
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        render_chart_conclusion(
            "Water-use movement over time by system and water-use basis.",
            "Spikes and drops should be interpreted together with the quality and review flags because some rows represent estimates or aggregate periods.",
        )

with domain_right:
    if ph_chart.empty:
        st.info("No pH-down quantity columns are available for a time-series chart.")
    else:
        ph_daily = (
            ph_chart.groupby(["observation_date", "system"], as_index=False)
            .agg(ph_down_ml=("ph_down_ml", "sum"))
        )
        fig = px.bar(
            ph_daily,
            x="observation_date",
            y="ph_down_ml",
            color="system",
            title="pH-down activity over time",
        )
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        render_chart_conclusion(
            "Daily pH-down additions by system.",
            "pH activity highlights intervention intensity and helps identify periods where chemistry adjustments were concentrated.",
        )

domain_bottom_left, domain_bottom_right = st.columns(2, gap="large")
with domain_bottom_left:
    if "leak_flag" not in chart_source.columns:
        st.info("No leak-status field is available.")
    else:
        leak_counts = (
            chart_source.groupby(["system", "leak_flag"], as_index=False)
            .size()
            .rename(columns={"size": "rows"})
        )
        fig = px.bar(
            leak_counts,
            x="system",
            y="rows",
            color="leak_flag",
            barmode="stack",
            title="Leak reporting by system",
        )
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, width="stretch")
        render_chart_conclusion(
            "Leak-status reporting counts across systems.",
            "A system with fewer reported leaks is only reassuring when leak-status coverage is also strong.",
        )

with domain_bottom_right:
    if duration_chart.empty:
        st.info("No water-addition duration column is available.")
    else:
        fig = px.box(
            duration_chart,
            x="system",
            y="water_addition_duration_min",
            color="system",
            points="outliers",
            title="Water-addition duration distribution",
        )
        fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig, width="stretch")
        render_chart_conclusion(
            "Distribution of recorded water-addition duration by system.",
            "Wide duration ranges point to variable operating workload or inconsistent recording that deserves follow-up.",
        )


st.markdown("### Data dictionary")
if dictionary.empty:
    st.info("No data dictionary output is available.")
else:
    dictionary_view = dictionary.copy()
    dict_left, dict_right = st.columns([1, 1.2], gap="medium")
    with dict_left:
        if "role" in dictionary_view.columns:
            roles = sorted(dictionary_view["role"].dropna().astype(str).unique().tolist())
            selected_roles = st.multiselect("Dictionary role", roles, default=roles)
            dictionary_view = dictionary_view[dictionary_view["role"].astype(str).isin(selected_roles)]
    with dict_right:
        dictionary_query = st.text_input("Search data dictionary", key="dictionary_search")
        dictionary_view = _search_frame(dictionary_view, dictionary_query)

    if "missing_pct" in dictionary_view.columns:
        dictionary_view["missing_pct"] = pd.to_numeric(dictionary_view["missing_pct"], errors="coerce")
        max_missing = st.slider(
            "Maximum missing percentage",
            min_value=0.0,
            max_value=100.0,
            value=100.0,
            step=1.0,
        )
        dictionary_view = dictionary_view[
            dictionary_view["missing_pct"].fillna(0).le(max_missing)
        ]

    st.dataframe(dictionary_view, width="stretch", hide_index=True)
    _download_button("Download filtered data dictionary", dictionary_view, "filtered_data_dictionary.csv")


st.markdown("### Metadata and pipeline summary")
if not metadata:
    st.info("No cleaning metadata output is available, or the metadata file could not be parsed.")
else:
    meta_cards = [
        ("Run date", str(metadata.get("run_date", "N/A")), "Notebook cleaning run date."),
        ("Generated UTC", str(metadata.get("generated_at_utc", "N/A")), "Timestamp recorded by the cleaning pipeline."),
        ("Original rows", f"{metadata.get('original_rows', 'N/A')}", "Rows observed before cleaning."),
        ("Cleaned rows", f"{metadata.get('cleaned_rows', 'N/A')}", "Rows written to the cleaned output."),
        ("Duplicates removed", f"{metadata.get('exact_duplicates_removed', 'N/A')}", "Exact duplicate rows removed."),
        ("Review rows", f"{metadata.get('rows_needing_review', 'N/A')}", "Rows flagged for human review."),
    ]
    for start in range(0, len(meta_cards), 3):
        columns = st.columns(3, gap="medium")
        for column, card in zip(columns, meta_cards[start : start + 3]):
            with column:
                render_metric_card(*card)

    validation_meta = metadata.get("validation_counts")
    if isinstance(validation_meta, dict):
        st.markdown("#### Validation counts from metadata")
        st.dataframe(
            pd.DataFrame(
                [{"severity": key, "checks": value} for key, value in validation_meta.items()]
            ),
            width="stretch",
            hide_index=True,
        )

    with st.expander("Sanitized metadata JSON", expanded=False):
        st.json(_sanitize_metadata(metadata))
