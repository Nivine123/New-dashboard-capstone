# Deployment Notes

This Streamlit app is ready for Streamlit Community Cloud from the project root. The required cleaned data and supporting report files are bundled in this folder.

## Settings

- Repository root: project root
- Main file: `streamlit_app.py`
- Python runtime: `runtime.txt`
- Theme: `.streamlit/config.toml`

## Required Data

The app uses `outputs/cleaned_data.csv` as the primary data source. The deployment folder includes these supporting cleaning outputs:

- `outputs/validation_report.csv`
- `outputs/data_quality_summary.csv`
- `outputs/rows_needing_review.csv`
- `outputs/data_dictionary.csv`
- `outputs/cleaning_metadata.json`

The raw CSV/workbook is not modified by the dashboard.

## Files To Commit

- `streamlit_app.py`
- `app.py`
- `pages/`
- `utils/`
- `outputs/`
- `.streamlit/config.toml`
- `requirements.txt`
- `runtime.txt`
- `deploy_check.py`
- `README.md`
- `DEPLOYMENT.md`

## Local Check

```bash
python3 deploy_check.py
python3 -m streamlit run streamlit_app.py
```

Use `streamlit_app.py` as the app entry point in Streamlit Community Cloud.
