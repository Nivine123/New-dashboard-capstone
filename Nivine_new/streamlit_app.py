"""Deployment-friendly Streamlit router.

Streamlit Community Cloud looks for ``streamlit_app.py`` by default. This file
stays as the deploy entrypoint while the sidebar shows only intentional
dashboard pages instead of a generic "streamlit app" page.
"""

from __future__ import annotations

import streamlit as st


NAVIGATION = {
    "Overview": [
        st.Page("app.py", title="Executive Overview"),
        st.Page("pages/Cleaned_Data_Hub.py", title="Cleaned Data Hub"),
    ],
    "Analytics": [
        st.Page("pages/System_Comparison.py", title="System Comparison"),
        st.Page("pages/Water_Resource_Analytics.py", title="Water Resource Analytics"),
        st.Page("pages/Operational_Risk_Issues.py", title="Operational Risk Issues"),
        st.Page("pages/Crop_Plant_Insights.py", title="Crop Plant Insights"),
        st.Page("pages/Trends_Over_Time.py", title="Trends Over Time"),
    ],
    "Governance": [
        st.Page("pages/Data_Quality_Confidence.py", title="Data Quality Confidence"),
        st.Page(
            "pages/Recommendations_Decision_Support.py",
            title="Recommendations Decision Support",
        ),
        st.Page("pages/Methodology_Capstone_Notes.py", title="Methodology Capstone Notes"),
        st.Page("pages/Cost_Optimization.py", title="Cost Optimization"),
    ],
}


navigation = st.navigation(NAVIGATION, position="sidebar", expanded=True)
navigation.run()
