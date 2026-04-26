"""Shared constants for the greenhouse analytics app."""

from __future__ import annotations

SYSTEM_ORDER = ["A-shape + Gutters", "Conventional", "Tower"]

SYSTEM_COLORS = {
    "A-shape + Gutters": "#2563EB",
    "Conventional": "#0F172A",
    "Tower": "#F59E0B",
}

SYSTEM_TYPE_COLORS = {
    "Hydroponic": "#2563EB",
    "Soil": "#059669",
}

QUALITY_ORDER = ["Usable", "Aggregate", "Estimated", "Review Required", "Event Only"]

ROW_CONFIDENCE_ORDER = [
    "Strong evidence",
    "Directional evidence",
    "Limited evidence",
]

ROW_CONFIDENCE_COLORS = {
    "Strong evidence": "#2563EB",
    "Directional evidence": "#D97706",
    "Limited evidence": "#DC2626",
}

ASSESSMENT_ORDER = ["Reliable", "Directional only", "Not reliable enough"]

ASSESSMENT_COLORS = {
    "Reliable": "#2563EB",
    "Directional only": "#D97706",
    "Not reliable enough": "#DC2626",
}

WEEKDAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
