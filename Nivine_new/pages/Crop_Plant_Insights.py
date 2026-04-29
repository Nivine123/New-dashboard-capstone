from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown("## Plant Scale and Crop Context")

st.markdown(
    "This section summarizes crop presence, average recorded plant counts "
    "across systems, and tower planting activity for the Towers system only."
)

# ---------------------------------------------------------
# Ensure required columns exist
# ---------------------------------------------------------
required_cols = {"system", "plant_count", "observation_date"}
missing = required_cols - set(df.columns)

if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

# ---------------------------------------------------------
# Prepare data safely
# ---------------------------------------------------------
df = df.copy()

df["plant_count_clean"] = (
    pd.to_numeric(df["plant_count"], errors="coerce")
    .fillna(0)
)

mask_towers = df["system"].astype(str).str.lower().str.contains("tower", na=False)

# ---------------------------------------------------------
# KPI Row
# ---------------------------------------------------------
k1, k2, k3 = st.columns(3)

k1.metric(
    "Avg Recorded Plants (All Systems)",
    f"{df['plant_count_clean'].mean():.1f}",
)

if mask_towers.any():
    k2.metric(
        "Avg Towers Planted (Towers System)",
        f"{df.loc[mask_towers, 'plant_count_clean'].mean():.1f}",
    )
else:
    k2.metric(
        "Avg Towers Planted (Towers System)",
        "N/A",
    )

k3.metric(
    "Towers Capacity (Reference)",
    "24 towers",
)

# ---------------------------------------------------------
# Crop types
# ---------------------------------------------------------
st.markdown("### Crop Types Across Systems")

if "crop_tokens" in df.columns and df["crop_tokens"].notna().any():
    crop_df = (
        df.explode("crop_tokens")
        .loc[lambda x: x["crop_tokens"].notna() & (x["crop_tokens"] != "")]
    )

    crop_counts = (
        crop_df.groupby(["system", "crop_tokens"])
        .size()
        .reset_index(name="count")
    )

    fig_crop = px.bar(
        crop_counts,
        x="system",
        y="count",
        color="crop_tokens",
        title="Observed Crop Tokens by System",
    )

    st.plotly_chart(fig_crop, use_container_width=True)
else:
    st.info("No crop data available.")

# ---------------------------------------------------------
# Average plants per system
# ---------------------------------------------------------
st.markdown("### Average Recorded Plants per System")

avg_plants_system = (
    df.groupby("system", as_index=False)["plant_count_clean"]
    .mean()
)

fig_avg = px.bar(
    avg_plants_system,
    x="system",
    y="plant_count_clean",
    title="Average Recorded Plant Count by System",
)

st.plotly_chart(fig_avg, use_container_width=True)

# ---------------------------------------------------------
# Towers planted over time (Towers ONLY)
# ---------------------------------------------------------
st.markdown("### Towers Planted Over Time (Towers System Only)")

if mask_towers.any():
    towers_trend = (
        df.loc[mask_towers]
        .groupby("observation_date", as_index=False)["plant_count_clean"]
        .mean()
    )

    fig_towers = px.line(
        towers_trend,
        x="observation_date",
        y="plant_count_clean",
        markers=True,
        title="Towers Planted Over Time",
    )

    fig_towers.add_hline(
        y=24,
        line_dash="dash",
        annotation_text="Max Capacity (24 towers)",
    )

    st.plotly_chart(fig_towers, use_container_width=True)
else:
    st.info("No Towers system data available under current filters.")

# ---------------------------------------------------------
# Methodology note
# ---------------------------------------------------------
with st.expander("Methodology Note"):
    st.markdown(
        "- Plant count values are descriptive and system-specific.\n"
        "- For the Towers system, plant_count represents the number of towers planted.\n"
        "- Tower capacity (24 towers) is used as a reference limit only.\n"
    )
