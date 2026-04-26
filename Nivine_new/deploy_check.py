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
    "outputs/cleaned_data.csv",
]
OPTIONAL_OUTPUTS = [
    "outputs/validation_report.csv",
    "outputs/data_quality_summary.csv",
    "outputs/rows_needing_review.csv",
    "outputs/data_dictionary.csv",
    "outputs/cleaning_metadata.json",
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
    missing = [file for file in REQUIRED_FILES if not (PROJECT_ROOT / file).exists()]
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
    print("Optional deployment data files:")
    for file in OPTIONAL_OUTPUTS:
        status = "available" if (PROJECT_ROOT / file).exists() else "missing"
        print(f"- {file}: {status}")


def main() -> None:
    check_files()
    check_syntax()
    check_data()
    print("Deployment readiness passed.")


if __name__ == "__main__":
    main()
