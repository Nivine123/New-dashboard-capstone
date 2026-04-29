st.markdown("### Plant count and crop mix")

plant_left, plant_right = st.columns(2, gap="large")

with plant_left:
    # Ensure all systems appear, even if plant_count is missing
    all_systems = pd.DataFrame({
        "system": sorted(df["system"].dropna().unique())
    })

    plant_count_summary = (
        df.groupby("system", as_index=False)
        .agg(
            average_plant_count=("plant_count", "mean"),
            plant_count_records=("plant_count", "count"),
        )
    )

    plant_count_view = all_systems.merge(
        plant_count_summary,
        on="system",
        how="left"
    )

    # Display missing plant-count systems as 0, without changing the original data
    plant_count_view["average_plant_count_display"] = (
        plant_count_view["average_plant_count"].fillna(0)
    )

    plant_count_view["plant_count_records"] = (
        plant_count_view["plant_count_records"].fillna(0).astype(int)
    )

    plant_fig = px.bar(
        plant_count_view,
        x="system",
        y="average_plant_count_display",
        text="plant_count_records",
        title="Average plant count by system",
        color="system",
    )

    plant_fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.88)",
        showlegend=False,
    )

    st.plotly_chart(plant_fig, width="stretch")

    render_chart_conclusion(
        "Average recorded plant count by system.",
        "Systems with zero displayed values may reflect missing plant-count data rather than absence of plants. Record counts indicate data coverage.",
    )

with plant_right:
    if crop_counts.empty:
        st.info("No crop tokens remain after the current filters.")
    else:
        st.plotly_chart(crop_heatmap(crop_counts), width="stretch")
        render_chart_conclusion(
            "Crop-token counts across systems.",
            "Crop mix explains why some system comparisons are not perfectly like-for-like.",
        )
