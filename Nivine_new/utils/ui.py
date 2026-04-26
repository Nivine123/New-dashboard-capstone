"""Shared Streamlit layout, styling, and sidebar controls."""

from __future__ import annotations

from typing import Any

import streamlit as st

from utils.data_loader import (
    available_filter_options,
    build_comparability_note,
    default_filters,
    filter_dataset,
    load_cleaning_outputs,
    load_greenhouse_dataset,
)


def configure_page(page_title: str) -> None:
    st.set_page_config(
        page_title=f"{page_title} | Greenhouse Systems Thesis Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()


def inject_theme() -> None:
    st.markdown(
        """
        <style>
            :root {
                color-scheme: light;
                --bg: #F8FAFC;
                --bg-soft: #F8FAFC;
                --surface: rgba(255, 255, 255, 0.94);
                --surface-strong: #ffffff;
                --surface-muted: #F8FAFC;
                --stroke: #E2E8F0;
                --stroke-strong: #CBD5E1;
                --text: #0F172A;
                --muted: #64748B;
                --accent: #2563EB;
                --accent-soft: #DBEAFE;
                --warning: #D97706;
                --warning-soft: #FEF3C7;
                --risk: #DC2626;
                --risk-soft: #FEE2E2;
                --shadow-lg: 0 18px 36px rgba(15, 23, 42, 0.08);
                --shadow-md: 0 10px 24px rgba(15, 23, 42, 0.06);
                --shadow-sm: 0 4px 14px rgba(15, 23, 42, 0.05);
            }
            html, body, [data-testid="stAppViewContainer"] {
                background: var(--bg-soft);
                color: var(--text);
                font-family: "Aptos", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            }
            .stApp {
                background: linear-gradient(180deg, #FFFFFF 0%, var(--bg-soft) 100%);
                color: var(--text);
            }
            .block-container {
                padding-top: 1.35rem;
                padding-bottom: 2.4rem;
                padding-left: 2rem;
                padding-right: 2rem;
                max-width: 1500px;
            }
            [data-testid="stHeader"] {
                background: rgba(248, 250, 252, 0.9);
                border-bottom: 1px solid rgba(226, 232, 240, 0.9);
                backdrop-filter: blur(12px);
            }
            [data-testid="stToolbar"] {
                color: var(--text);
            }
            [data-testid="stSidebar"] {
                background: #FFFFFF;
                border-right: 1px solid var(--stroke);
            }
            [data-testid="stSidebarNav"] {
                padding-top: 0.6rem;
            }
            [data-testid="stSidebarNav"] * {
                color: var(--text);
            }
            [data-testid="stSidebarNav"] a {
                border-radius: 14px;
                margin-bottom: 0.18rem;
            }
            [data-testid="stSidebarNav"] a:hover {
                background: rgba(37, 99, 235, 0.08);
            }
            [data-baseweb="select"] > div,
            [data-baseweb="input"] > div,
            [data-baseweb="textarea"] > div {
                background: var(--surface-strong);
                border-color: var(--stroke);
                border-radius: 14px;
                box-shadow: none;
            }
            [data-testid="stDateInputField"],
            [data-testid="stNumberInputField"],
            [data-testid="stTextInputRootElement"] {
                background: var(--surface-strong);
                border-radius: 14px;
            }
            [data-baseweb="select"] > div:hover,
            [data-baseweb="input"] > div:hover,
            [data-baseweb="textarea"] > div:hover {
                border-color: #BFDBFE;
            }
            [data-baseweb="tag"] {
                background: var(--accent-soft) !important;
                border-radius: 999px !important;
                border: 1px solid #BFDBFE !important;
                color: var(--accent) !important;
            }
            [data-baseweb="tag"] span {
                color: var(--accent) !important;
            }
            div[data-testid="stSelectbox"] label,
            div[data-testid="stMultiSelect"] label,
            div[data-testid="stSlider"] label,
            div[data-testid="stDateInput"] label,
            div[data-testid="stCheckbox"] label,
            div[data-testid="stRadio"] label {
                color: var(--text);
                font-weight: 600;
            }
            [data-testid="stMarkdownContainer"],
            [data-testid="stCaptionContainer"] {
                color: var(--text);
            }
            div[data-testid="stAlert"] {
                background: var(--surface);
                color: var(--text);
                border-radius: 18px;
                border: 1px solid var(--stroke);
                box-shadow: var(--shadow-sm);
            }
            div[data-testid="stPlotlyChart"],
            [data-testid="stDataFrame"] {
                background: var(--surface);
                border-radius: 22px;
                border: 1px solid var(--stroke);
                box-shadow: var(--shadow-sm);
                padding: 0.45rem 0.55rem;
            }
            [data-testid="stDataFrame"] {
                overflow: hidden;
            }
            [data-testid="stExpander"] {
                border: 1px solid var(--stroke);
                border-radius: 18px;
                background: var(--surface);
                box-shadow: var(--shadow-sm);
            }
            details summary {
                font-weight: 700;
                color: var(--text);
            }
            h1, h2, h3 {
                color: var(--text);
                letter-spacing: -0.02em;
            }
            h2 {
                font-size: 1.45rem;
                margin-top: 0.5rem;
                margin-bottom: 0.3rem;
            }
            h3 {
                font-size: 1.12rem;
                margin-top: 0.35rem;
                margin-bottom: 0.35rem;
            }
            p, li {
                color: var(--muted);
                line-height: 1.55;
            }
            .hero-card {
                background: #FFFFFF;
                border: 1px solid var(--stroke);
                border-radius: 16px;
                padding: 1.55rem 1.7rem 1.45rem;
                box-shadow: var(--shadow-lg);
                margin-bottom: 1.1rem;
                position: relative;
                overflow: hidden;
            }
            .hero-eyebrow {
                color: var(--accent);
                font-size: 0.76rem;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                font-weight: 700;
                margin-bottom: 0.45rem;
            }
            .hero-title {
                font-size: 2rem;
                font-weight: 760;
                color: var(--text);
                margin-bottom: 0.48rem;
                line-height: 1.1;
                position: relative;
                z-index: 1;
            }
            .hero-subtitle {
                font-size: 0.99rem;
                color: var(--muted);
                max-width: 980px;
                line-height: 1.55;
                position: relative;
                z-index: 1;
            }
            .metric-card {
                background: var(--surface);
                border: 1px solid var(--stroke);
                border-radius: 12px;
                padding: 1rem 1rem 0.95rem;
                box-shadow: var(--shadow-sm);
                min-height: 126px;
                transition: transform 140ms ease, box-shadow 140ms ease;
            }
            .metric-card:hover {
                transform: translateY(-1px);
                box-shadow: var(--shadow-md);
            }
            .metric-label {
                color: var(--muted);
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                margin-bottom: 0.48rem;
                font-weight: 700;
            }
            .metric-value {
                color: var(--text);
                font-size: 1.58rem;
                font-weight: 760;
                line-height: 1.1;
                margin-bottom: 0.42rem;
            }
            .metric-note {
                color: var(--muted);
                font-size: 0.87rem;
                line-height: 1.45;
            }
            .callout-card {
                background: var(--surface);
                border: 1px solid var(--stroke);
                border-left: 5px solid var(--accent);
                border-radius: 12px;
                padding: 0.95rem 1rem 0.92rem;
                box-shadow: var(--shadow-sm);
                min-height: 140px;
            }
            .callout-card.warning {
                border-left-color: var(--warning);
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(251, 246, 232, 0.96));
            }
            .callout-card.risk {
                border-left-color: var(--risk);
                background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(251, 239, 235, 0.96));
            }
            .callout-title {
                font-weight: 760;
                color: var(--text);
                margin-bottom: 0.38rem;
            }
            .callout-body {
                color: var(--muted);
                line-height: 1.5;
                font-size: 0.93rem;
            }
            .section-caption {
                color: var(--muted);
                margin-top: -0.12rem;
                margin-bottom: 0.9rem;
                max-width: 980px;
            }
            div[data-testid="stMetric"] {
                background: var(--surface);
                border-radius: 18px;
                border: 1px solid var(--stroke);
                padding: 0.8rem 1rem;
                box-shadow: var(--shadow-sm);
            }
            .small-note {
                color: var(--muted);
                font-size: 0.85rem;
                line-height: 1.45;
            }
            .chart-conclusion {
                background: #FFFFFF;
                border: 1px solid var(--stroke);
                border-left: 4px solid var(--accent);
                border-radius: 10px;
                color: var(--muted);
                font-size: 0.9rem;
                line-height: 1.45;
                margin: -0.15rem 0 1rem 0;
                padding: 0.72rem 0.82rem;
                box-shadow: var(--shadow-sm);
            }
            .chart-conclusion strong {
                color: var(--text);
            }
            .sidebar-card {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid var(--stroke);
                border-radius: 12px;
                padding: 0.9rem 0.95rem;
                box-shadow: var(--shadow-sm);
                margin-bottom: 0.85rem;
            }
            .sidebar-title {
                color: var(--text);
                font-size: 0.98rem;
                font-weight: 760;
                margin-bottom: 0.18rem;
            }
            .sidebar-subtitle {
                color: var(--muted);
                font-size: 0.84rem;
                line-height: 1.4;
            }
            .comparability-card {
                background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255, 251, 235, 0.98));
                border: 1px solid #FDE68A;
                border-left: 5px solid var(--warning);
                border-radius: 12px;
                padding: 0.95rem 1rem 0.92rem;
                box-shadow: var(--shadow-sm);
                margin: 0.2rem 0 1rem 0;
            }
            .comparability-label {
                color: #8a6510;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-weight: 760;
                margin-bottom: 0.28rem;
            }
            .comparability-body {
                color: #6d5930;
                font-size: 0.93rem;
                line-height: 1.5;
            }
            .status-badge {
                display: inline-block;
                padding: 0.34rem 0.68rem;
                border-radius: 999px;
                font-size: 0.76rem;
                font-weight: 760;
                letter-spacing: 0.02em;
                margin: 0 0.35rem 0.35rem 0;
                border: 1px solid transparent;
                box-shadow: 0 2px 8px rgba(18, 44, 67, 0.04);
            }
            .status-badge.good {
                background: #ECFDF5;
                color: #047857;
                border-color: #A7F3D0;
            }
            .status-badge.warn {
                background: #FFFBEB;
                color: #92400E;
                border-color: #FDE68A;
            }
            .status-badge.risk {
                background: #FEF2F2;
                color: #B91C1C;
                border-color: #FECACA;
            }
            /* Nivo-style professional polish */
            .block-container {
                max-width: 1540px;
                padding-top: 1.15rem;
            }
            [data-testid="stSidebar"] {
                box-shadow: 8px 0 28px rgba(15, 23, 42, 0.04);
            }
            [data-testid="stSidebarNav"] a {
                border: 1px solid transparent;
                border-radius: 10px;
                color: var(--text);
                font-weight: 650;
                padding-top: 0.52rem;
                padding-bottom: 0.52rem;
            }
            [data-testid="stSidebarNav"] a[aria-current="page"],
            [data-testid="stSidebarNav"] a:focus {
                background: #EFF6FF;
                border-color: #BFDBFE;
                color: #1D4ED8;
            }
            h1, h2, h3 {
                letter-spacing: 0;
            }
            h2 {
                border-bottom: 1px solid var(--stroke);
                padding-bottom: 0.28rem;
            }
            div[data-testid="stPlotlyChart"],
            [data-testid="stDataFrame"],
            [data-testid="stExpander"] {
                border-radius: 12px;
                border-color: var(--stroke);
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
            }
            div[data-testid="stAlert"] {
                border-radius: 12px;
                box-shadow: none;
            }
            .hero-card {
                border-radius: 12px;
                padding: 1.18rem 1.3rem;
                margin-bottom: 1.05rem;
                box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
            }
            .hero-title {
                font-size: 1.88rem;
                letter-spacing: 0;
            }
            .hero-subtitle {
                max-width: 1080px;
            }
            .hero-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 0.45rem;
                margin-top: 0.85rem;
            }
            .hero-pill {
                background: #EFF6FF;
                border: 1px solid #BFDBFE;
                border-radius: 999px;
                color: #1D4ED8;
                font-size: 0.78rem;
                font-weight: 700;
                padding: 0.34rem 0.68rem;
            }
            .metric-card {
                border-radius: 10px;
                box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
                min-height: 118px;
            }
            .metric-label {
                letter-spacing: 0.08em;
            }
            .metric-value {
                font-size: 1.5rem;
            }
            .callout-card,
            .comparability-card,
            .chart-conclusion,
            .sidebar-card {
                border-radius: 10px;
            }
            .chart-conclusion {
                background: #F8FAFC;
                border-left-color: #2563EB;
                box-shadow: none;
            }
            .freshness-card {
                background: #F8FAFC;
                border: 1px solid var(--stroke);
                border-radius: 10px;
                padding: 0.8rem 0.85rem;
                margin-bottom: 0.9rem;
            }
            .freshness-title {
                color: var(--text);
                font-size: 0.88rem;
                font-weight: 760;
                margin-bottom: 0.45rem;
            }
            .freshness-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.45rem;
            }
            .freshness-item {
                background: #FFFFFF;
                border: 1px solid var(--stroke);
                border-radius: 8px;
                padding: 0.5rem 0.55rem;
            }
            .freshness-label {
                color: var(--muted);
                font-size: 0.67rem;
                font-weight: 720;
                letter-spacing: 0.06em;
                text-transform: uppercase;
            }
            .freshness-value {
                color: var(--text);
                font-size: 0.88rem;
                font-weight: 760;
                margin-top: 0.1rem;
            }
            [data-testid="stDownloadButton"] button,
            [data-testid="stButton"] button {
                border-radius: 10px;
                border: 1px solid #BFDBFE;
                background: #FFFFFF;
                color: #1D4ED8;
                font-weight: 700;
            }
            [data-testid="stDownloadButton"] button:hover,
            [data-testid="stButton"] button:hover {
                border-color: #2563EB;
                background: #EFF6FF;
                color: #1D4ED8;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(title: str, subtitle: str, eyebrow: str = "Masters in Data Analytics") -> None:
    st.markdown(
        f"""
        <div class="hero-card">
            <div class="hero-eyebrow">{eyebrow}</div>
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
            <div class="hero-meta">
                <span class="hero-pill">Cleaned outputs bundled</span>
                <span class="hero-pill">Confidence-aware analytics</span>
                <span class="hero-pill">Deployment-ready</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_callout(title: str, body: str, tone: str = "default") -> None:
    css_class = "callout-card" if tone == "default" else f"callout-card {tone}"
    st.markdown(
        f"""
        <div class="{css_class}">
            <div class="callout-title">{title}</div>
            <div class="callout-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badge(label: str, tone: str = "good") -> None:
    st.markdown(
        f"<span class='status-badge {tone}'>{label}</span>",
        unsafe_allow_html=True,
    )


def render_chart_conclusion(what: str, conclusion: str) -> None:
    """Add a short, consistent explanation under a chart."""

    st.markdown(
        f"""
        <div class="chart-conclusion">
            <strong>What it shows:</strong> {what}<br>
            <strong>Conclusion:</strong> {conclusion}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(df, dataset_path) -> dict[str, Any]:
    options = available_filter_options(df)
    defaults = default_filters(df)
    cleaning_outputs = load_cleaning_outputs()
    metadata = cleaning_outputs["metadata"]
    bundled_reports = 6 - len(cleaning_outputs["missing"])
    try:
        cleaned_rows = int(metadata.get("cleaned_rows", len(df)))
    except (TypeError, ValueError):
        cleaned_rows = len(df)
    run_date = str(metadata.get("run_date") or metadata.get("generated_at_utc") or "Available")
    run_date = run_date.split("T")[0] if "T" in run_date else run_date

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-card">
                <div class="sidebar-title">Analysis Controls</div>
                <div class="sidebar-subtitle">Refine scope, crop context, and evidence quality before interpreting system differences.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="freshness-card">
                <div class="freshness-title">Data Freshness</div>
                <div class="freshness-grid">
                    <div class="freshness-item">
                        <div class="freshness-label">Clean run</div>
                        <div class="freshness-value">{run_date}</div>
                    </div>
                    <div class="freshness-item">
                        <div class="freshness-label">Rows</div>
                        <div class="freshness-value">{cleaned_rows:,}</div>
                    </div>
                    <div class="freshness-item">
                        <div class="freshness-label">Reports</div>
                        <div class="freshness-value">{bundled_reports}/6</div>
                    </div>
                    <div class="freshness-item">
                        <div class="freshness-label">Raw data</div>
                        <div class="freshness-value">Untouched</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander("Core Scope", expanded=True):
            systems = st.multiselect(
                "System",
                options=options["systems"],
                default=defaults["systems"],
                help="Select one or more greenhouse systems for the current analysis view.",
            )
            system_types = st.multiselect(
                "System type",
                options=options["system_types"],
                default=defaults["system_types"],
            )
            date_range = st.slider(
                "Observation date range",
                min_value=defaults["date_range"][0],
                max_value=defaults["date_range"][1],
                value=defaults["date_range"],
            )

        with st.expander("Crop Context", expanded=False):
            crop_types = st.multiselect(
                "Crop types",
                options=options["crops"],
                default=[],
                help="Optional crop filter. Leaving this empty keeps every crop in scope.",
            )
            plant_names = st.multiselect(
                "Plant name",
                options=options["plant_names"],
                default=[],
            )

        with st.expander("Evidence Quality", expanded=True):
            quality_status = st.multiselect(
                "Data quality status",
                options=options["quality_status"],
                default=defaults["quality_status"],
            )
            row_confidence_bands = st.multiselect(
                "Evidence strength",
                options=options["row_confidence_bands"],
                default=defaults["row_confidence_bands"],
                help="Filter rows by the app's confidence-aware classification.",
            )
            include_estimated = st.checkbox(
                "Include estimated rows",
                value=defaults["include_estimated"],
            )
            include_aggregate = st.checkbox(
                "Include weekend / aggregate rows",
                value=defaults["include_aggregate"],
            )

        st.markdown(
            "<div class='small-note'>Filters apply across every page and keep the dashboard's conclusions tied to the active evidence slice.</div>",
            unsafe_allow_html=True,
        )

    return {
        "systems": systems,
        "system_types": system_types,
        "date_range": date_range,
        "crop_types": crop_types,
        "plant_names": plant_names,
        "quality_status": quality_status,
        "row_confidence_bands": row_confidence_bands,
        "include_estimated": include_estimated,
        "include_aggregate": include_aggregate,
    }


def build_page_context(page_title: str) -> dict[str, Any]:
    configure_page(page_title)
    try:
        df, dataset_path = load_greenhouse_dataset()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Could not load the cleaned dataset: {type(exc).__name__}: {exc}")
        st.stop()

    filters = render_sidebar(df, dataset_path)
    filtered_df = filter_dataset(df, filters)
    comparability_note = build_comparability_note(filtered_df)

    return {
        "page_title": page_title,
        "source_df": df,
        "df": filtered_df,
        "filters": filters,
        "dataset_path": dataset_path,
        "comparability_note": comparability_note,
    }


def render_comparability_note(note: str | None) -> None:
    if note:
        st.markdown(
            f"""
            <div class="comparability-card">
                <div class="comparability-label">Comparability Caution</div>
                <div class="comparability-body">{note}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
