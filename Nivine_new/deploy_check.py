"""Small deployment readiness check for the Streamlit dashboard."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = [
    "streamlit_app.py",
    "app.py",
    "requirements.txt",
    "runtime.txt",
    ".streamlit/config.toml",
]
REQUIRED_DATA_FILES = [
    "outputs/cleaned_data.csv",
    "outputs/validation_report.csv",
    "outputs/data_quality_summary.csv",
    "outputs/rows_needing_review.csv",
    "outputs/data_dictionary.csv",
    "outputs/cleaning_metadata.json",
]
EXPECTED_PAGES = [
    "pages/Cleaned_Data_Hub.py",
    "pages/System_Comparison.py",
    "pages/Water_Resource_Analytics.py",
    "pages/Operational_Risk_Issues.py",
    "pages/Crop_Plant_Insights.py",
    "pages/Data_Quality_Confidence.py",
    "pages/Trends_Over_Time.py",
    "pages/Recommendations_Decision_Support.py",
    "pages/Methodology_Capstone_Notes.py",
    "pages/Cost_Optimization.py",
]
BANNED_PATH_SNIPPETS = [
    "/" "Users/",
    "Desktop/" "nivo",
    "Desktop/" "New-dashboard-capstone",
]


def check_syntax() -> None:
    python_files = [
        PROJECT_ROOT / "streamlit_app.py",
        PROJECT_ROOT / "app.py",
        *sorted((PROJECT_ROOT / "pages").glob("*.py")),
        *sorted((PROJECT_ROOT / "utils").glob("*.py")),
    ]
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def check_files() -> None:
    expected = REQUIRED_FILES + REQUIRED_DATA_FILES + EXPECTED_PAGES
    missing = [file for file in expected if not (PROJECT_ROOT / file).exists()]
    if missing:
        raise FileNotFoundError("Missing required deploy files: " + ", ".join(missing))


def check_data() -> None:
    cleaned_path = PROJECT_ROOT / "outputs" / "cleaned_data.csv"
    cleaned = pd.read_csv(cleaned_path)
    if cleaned.empty:
        raise ValueError("outputs/cleaned_data.csv exists but contains no rows.")

    metadata_path = PROJECT_ROOT / "outputs" / "cleaning_metadata.json"
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError("outputs/cleaning_metadata.json must contain a JSON object.")

    print(f"cleaned rows: {len(cleaned):,}")
    print(f"cleaned columns: {cleaned.shape[1]:,}")
    print("Bundled deployment data files:")
    for file in REQUIRED_DATA_FILES:
        status = "available" if (PROJECT_ROOT / file).exists() else "missing"
        print(f"- {file}: {status}")


def check_no_local_paths() -> None:
    """Keep deploy-facing code/docs/metadata free of machine-local paths."""

    paths = [
        PROJECT_ROOT / "streamlit_app.py",
        PROJECT_ROOT / "app.py",
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "DEPLOYMENT.md",
        PROJECT_ROOT / "deploy_check.py",
        PROJECT_ROOT / ".streamlit" / "config.toml",
        PROJECT_ROOT / "outputs" / "cleaning_metadata.json",
        *sorted((PROJECT_ROOT / "pages").glob("*.py")),
        *sorted((PROJECT_ROOT / "utils").glob("*.py")),
    ]
    leaks: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if any(snippet in text for snippet in BANNED_PATH_SNIPPETS):
            leaks.append(str(path.relative_to(PROJECT_ROOT)))
    if leaks:
        raise ValueError("Local absolute path references found in: " + ", ".join(leaks))


def main() -> None:
    check_files()
    check_syntax()
    check_data()
    check_no_local_paths()
    print("Deployment readiness passed.")


if __name__ == "__main__":
    main()
