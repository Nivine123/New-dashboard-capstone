# Greenhouse Systems Capstone Dashboard

A multi-page Streamlit application for a Masters in Data Analytics thesis focused on greenhouse system evaluation. The dashboard combines business intelligence, operational analytics, and data-quality-aware interpretation using the greenhouse observation dataset in this workspace.

## Project structure

- `app.py`: Executive Overview page
- `streamlit_app.py`: deployment-friendly entrypoint for Streamlit Community Cloud
- `pages/`: dedicated thesis pages for comparison, resources, risk, crops, confidence, trends, recommendations, and methodology
- `utils/`: reusable logic for loading, preprocessing, metrics, scoring, charts, recommendations, and shared UI
- `outputs/cleaned_data.csv`: primary cleaned dataset used by the app
- `outputs/`: optional validation, quality, review-queue, data-dictionary, and metadata reports
- `.streamlit/config.toml`: deployment theme and Streamlit runtime settings
- `deploy_check.py`: local readiness check for syntax, required files, and data availability
- `requirements.txt`: Python dependencies
- `runtime.txt`: pinned Python runtime for cloud deployment

## Run instructions

1. Create or activate a Python environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
streamlit run streamlit_app.py
```

4. Open the local Streamlit URL shown in the terminal.

## Streamlit deployment

This project is prepared for Streamlit Community Cloud.

### Recommended deployment settings

- Repository root: this project folder
- Main file path: `streamlit_app.py`
- Python version: `3.11` via `runtime.txt`

### Deployment checklist

1. Push the full project to GitHub, including:
   - `streamlit_app.py`
   - `app.py`
   - `pages/`
   - `utils/`
   - `outputs/cleaned_data.csv`
   - optional `outputs/` report files
   - `.streamlit/config.toml`
   - `requirements.txt`
   - `runtime.txt`
2. In Streamlit Community Cloud, create a new app from the repository.
3. Set the app entry file to `streamlit_app.py` if Streamlit does not auto-detect it.
4. Redeploy whenever you update the code or dataset.

### Notes for cloud deployment

- The app loads `outputs/cleaned_data.csv` first and falls back to older greenhouse cleaned CSV filenames only for local compatibility.
- No local secrets are required for deployment.
- The app uses only file-based local data, so there is no database or API setup step.
- The dashboard is multi-page and Streamlit will automatically detect the `pages/` directory in deployment.

## Analytical logic used

- The app loads the cleaned CSV from `outputs/cleaned_data.csv` and integrates optional cleaning reports when present.
- Dates, timestamps, numeric measures, and boolean flags are standardized during preprocessing.
- Nutrient and pH quantities are unified into derived fields so the app can use generic and system-specific measurement columns without double counting.
- The app creates row-level evidence bands:
  - `Strong evidence`: usable, analysis-ready, non-estimated, non-aggregate, and non-warning rows
  - `Directional evidence`: usable / aggregate / estimated rows without core-measurement failure
  - `Limited evidence`: event-only or weak-confidence rows
- System comparison uses transparent 0-100 component scoring:
  - `Efficiency`: composite of water use per active day, nutrient use per active day when measured, intervention burden, and stability
  - `Efficiency confidence`: separate from the efficiency score itself; missing nutrient quantities lower confidence instead of being treated as zero
  - `Risk`: issue-day frequency, leak-day frequency, observed leak severity, and manual intervention days
  - `Stability`: coefficient of variation, rolling variance ratio, day-to-day change consistency, and clean daily support
  - `Workload`: manual intervention days, manual watering days, nutrient-addition days, and water-addition duration burden
  - `Confidence`: analysis-ready coverage, estimated values, missing core measures, warning flags, and imputed values
- System burden metrics are normalized by active days, with observation-normalized context shown where useful.
- Recommendations are generated from those metrics and always framed with confidence-aware language.
- The dashboard includes pipeline Sankey diagrams, readiness funnels, score radar charts, score heatmaps, availability heatmaps, issue treemaps, crop sunbursts, weekday density heatmaps, recommendation confidence charts, and cost waterfall/treemap views.
- Every major chart includes a short conclusion underneath so the visual can be interpreted in a capstone or executive-review setting.

## Assumptions and limitations

- Cross-system efficiency comparisons are directional when the filter scope mixes hydroponic and soil systems.
- Water-use basis differs across the dataset:
  - Hydroponic systems rely on recorded consumption.
  - Conventional uses applied watering.
- Nutrient quantity tracking is incomplete for some systems, so apparent efficiency leadership may remain estimated or unsupported.
- Leak absence is not treated as proof of low risk when leak reporting coverage is incomplete.
- Plant-level fields are sparse for some systems, so crop insights are intentionally cautious.
- The app avoids misleading per-plant efficiency claims because plant-count coverage is uneven.
- Findings are descriptive and operational, not causal.

## Future enhancements

- Add predictive forecasting for water use, issue probability, and intervention burden.
- Add anomaly detection for sudden water spikes, repeated leak clusters, and out-of-pattern nutrient activity.
- Add controlled scenario analysis for comparing system upgrades or maintenance interventions.
- Add automated narrative export for thesis appendices or executive PDF summaries.
- Add statistical testing modules for stronger follow-up validation once measurement rules are harmonized.
