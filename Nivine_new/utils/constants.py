"""Shared constants for the greenhouse analytics app."""

from __future__ import annotations

SYSTEM_ORDER = ["A-shape + Gutters", "Conventional", "Tower"]

SYSTEM_COLORS = {
    "A-shape + Gutters": "#2A9D8F",
    "Conventional": "#264653",
    "Tower": "#E9C46A",
}

SYSTEM_TYPE_COLORS = {
    "Hydroponic": "#2A9D8F",
    "Soil": "#8D6E63",
}

QUALITY_ORDER = ["Usable", "Aggregate", "Estimated", "Review Required", "Event Only"]

ROW_CONFIDENCE_ORDER = [
    "Strong evidence",
    "Directional evidence",
    "Limited evidence",
]

ROW_CONFIDENCE_COLORS = {
    "Strong evidence": "#2A9D8F",
    "Directional evidence": "#E9C46A",
    "Limited evidence": "#E76F51",
}

ASSESSMENT_ORDER = ["Reliable", "Directional only", "Not reliable enough"]

ASSESSMENT_COLORS = {
    "Reliable": "#2A9D8F",
    "Directional only": "#E9C46A",
    "Not reliable enough": "#E76F51",
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
