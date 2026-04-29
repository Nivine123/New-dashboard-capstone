# =========================================================
# Plant Scale & Crop Context
# =========================================================

st.markdown("## 🌱 Plant Scale & Crop Context")

st.markdown(
    """
This section describes **what is planted** and **at what scale**.
Plant count metrics are descriptive and reflect how each system records planting activity.
"""
)

# ---------------------------------------------------------
# Prepare columns safely
# ---------------------------------------------------------
df = df.copy()

# Make plant_count numeric and safe
df["plant_count_clean"] = (
    pd.to_numeric(df["plant_count"], errors="coerce")
    .fillna(0)
)

# Identify Towers system robustly
mask_towers = df["system"].astype(str).str.lower().str.contains("tower", na=False)

# ---------------------------------------------------------
# ===== KPI ROW =====
# ---------------------------------------------------------
k1, k2, k3 = st.columns(3)

# KPI 1 — Average plants per system (ALL systems)
avg_plants_all = df["plant_count_clean"].mean()

k1.metric(
    "Avg Recorded Plants (All Systems)",
    f"{avg_plants_all:,.1f}",
    help="Average recorded plant count across all systems (descriptive only).",
)

# KPI 2 — Avg towers planted (TOWERS only)
if mask_towers.any():
    avg_towers = df.loc[mask_towers, "plant_count_clean"].mean()
    k2.metric(
        "Avg Towers Planted (Towers System)",
        f"{avg_towers:,.1f}",
        help="Average number of towers planted. Applies only to the Towers system.",
    )
else:
    k2.metric(
        "Avg Towers Planted (Towers System)",
        "N/A",
        help="No Towers system data available under current filters.",
    )

# KPI 3 — Max capacity reference
k3.metric(
    "Towers Capacity (Reference)",
    "24 towers",
    help="Maximum possible number of towers (reference only).",
)

# ---------------------------------------------------------
# ===== Crop / Plant Types =====
# ---------------------------------------------------------
st.markdown("### 🌿 Crop Types Across Systems")

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
        labels={
            "count": "Observations",
            "crop_tokens": "Crop Type",
            "system": "System",
        },
    )

    st.plotly_chart(fig_crop, use_container_width=True)

    render_chart_conclusion(
        "Observed crop types by system.",
        "This view shows which crops appear in each system. Counts reflect observation frequency, not yield.",
    )
else:
    st.info("No crop type data available under current filters.")

# ---------------------------------------------------------
# ===== Avg Plants per System =====
# ---------------------------------------------------------
st.markdown("### 📊 Average Recorded Plants per System")

avg_plants_system = (
    df.groupby("system", as_index=False)["plant_count_clean"]
    .mean()
)

fig_avg_plants = px.bar(
    avg_plants_system,
    x="system",
    y="plant_count_clean",
    title="Average Recorded Plant Count by System",
    labels={
        "plant_count_clean": "Avg Recorded Plants",
        "system": "System",
    },
)

st.plotly_chart(fig_avg_plants, use_container_width=True)

render_chart_conclusion(
    "Average recorded plant count by system.",
    "Values are descriptive indicators of planting scale. Recording methods differ across systems.",
)

# ---------------------------------------------------------
# ===== Towers Planted Over Time (TOWERS ONLY) =====
# ---------------------------------------------------------
st.markdown("### 🏗 Towers Planted Over Time (Towers System Only)")

if mask_towers.any():
    towers_trend = (
