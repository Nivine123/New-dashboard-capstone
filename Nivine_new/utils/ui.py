"""Shared Streamlit layout, styling, and sidebar controls."""

from __future__ import annotations

from typing import Any

import streamlit as st

from utils.data_loader import (
    available_filter_options,
    build_comparability_note,
    default_filters,
    filter_dataset,
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
                --bg: #f3f6f4;
                --bg-soft: #eef3f0;
                --surface: rgba(255, 255, 255, 0.94);
                --surface-strong: #ffffff;
                --surface-muted: #f7faf8;
                --stroke: #d9e2db;
                --stroke-strong: #cfd9d1;
                --text: #18324a;
                --muted: #5a7181;
                --accent: #2c7a70;
                --accent-soft: #e6f2ee;
                --warning: #c38b19;
                --warning-soft: #fbf2da;
                --risk: #b6523e;
                --risk-soft: #f9e7e2;
                --shadow-lg: 0 18px 36px rgba(18, 44, 67, 0.08);
                --shadow-md: 0 10px 24px rgba(18, 44, 67, 0.06);
                --shadow-sm: 0 4px 14px rgba(18, 44, 67, 0.05);
            }
            html, body, [data-testid="stAppViewContainer"] {
                background: var(--bg-soft);
                color: var(--text);
                font-family: "Aptos", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            }
            .stApp {
                background:
                    radial-gradient(circle at top right, rgba(44, 122, 112, 0.08), transparent 26%),
                    linear-gradient(180deg, #f8faf8 0%, var(--bg-soft) 100%);
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
                background: rgba(248, 250, 248, 0.82);
                border-bottom: 1px solid rgba(217, 226, 219, 0.7);
                backdrop-filter: blur(12px);
            }
            [data-testid="stToolbar"] {
                color: var(--text);
            }
            [data-testid="stSidebar"] {
                background:
                    linear-gradient(180deg, rgba(248, 251, 249, 0.98), rgba(242, 247, 244, 0.98));
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
                background: rgba(44, 122, 112, 0.08);
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
                border-color: #bdd0c5;
            }
            [data-baseweb="tag"] {
                background: var(--accent-soft) !important;
                border-radius: 999px !important;
                border: 1px solid #c7ded6 !important;
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
                background:
                    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(244, 249, 246, 0.96));
                border: 1px solid var(--stroke);
                border-radius: 26px;
                padding: 1.55rem 1.7rem 1.45rem;
                box-shadow: var(--shadow-lg);
                margin-bottom: 1.1rem;
                position: relative;
                overflow: hidden;
            }
            .hero-card::after {
                content: "";
                position: absolute;
                inset: auto -40px -52px auto;
                width: 220px;
                height: 220px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(44, 122, 112, 0.12) 0%, rgba(44, 122, 112, 0) 68%);
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
                border-radius: 20px;
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
                border-radius: 18px;
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
            .sidebar-card {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid var(--stroke);
                border-radius: 18px;
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
                background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(251, 246, 232, 0.98));
                border: 1px solid #ead8a8;
                border-left: 5px solid var(--warning);
                border-radius: 18px;
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
                background: var(--accent-soft);
                color: #225e57;
                border-color: #c4ddd5;
            }
            .status-badge.warn {
                background: var(--warning-soft);
                color: #886514;
                border-color: #efd79a;
            }
            .status-badge.risk {
                background: var(--risk-soft);
                color: #9b4535;
                border-color: #efc0b5;
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


def render_sidebar(df, dataset_path) -> dict[str, Any]:
    options = available_filter_options(df)
    defaults = default_filters(df)

    with st.sidebar:
        st.markdown(
            f"""
            <div class="sidebar-card">
                <div class="sidebar-title">Analysis Controls</div>
                <div class="sidebar-subtitle">Dataset: <strong>{dataset_path.name}</strong><br>Refine scope, crop context, and evidence quality before interpreting system differences.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Core scope")
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

        st.markdown("### Crop context")
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

        st.markdown("### Evidence filters")
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

        st.markdown("### Include / Exclude")
        include_estimated = st.checkbox(
            "Include estimated rows",
            value=defaults["include_estimated"],
        )
        include_aggregate = st.checkbox(
            "Include weekend / aggregate rows",
            value=defaults["include_aggregate"],
        )

        st.markdown(
            "<div class='small-note'>Use the controls above to tighten the evidence base before interpreting system differences.</div>",
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
