# Deployment Notes

This Streamlit app is ready for Streamlit Community Cloud from the project root.

## Settings

- Repository root: project root
- Main file: `streamlit_app.py`
- Python runtime: `runtime.txt`
- Theme: `.streamlit/config.toml`

## Required Data

The app uses `outputs/cleaned_data.csv` as the primary data source. These optional cleaning outputs are integrated automatically when present:

- `outputs/validation_report.csv`
- `outputs/data_quality_summary.csv`
- `outputs/rows_needing_review.csv`
- `outputs/data_dictionary.csv`
- `outputs/cleaning_metadata.json`

The raw CSV/workbook is not modified by the dashboard.

## Local Check

```bash
python3 deploy_check.py
python3 -m streamlit run streamlit_app.py
```
