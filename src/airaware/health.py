"""Health impact mapping and public health guidance module based on official CPCB definitions."""

from typing import Any, Dict, Optional
from airaware.aqi import load_categories


def get_health_details(category_name: str, categories_cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Retrieve detailed health impact and advisory information for a given AQI category.

    Args:
        category_name: Name of category (e.g. 'Good', 'Moderate', 'Poor').
        categories_cfg: Optional preloaded categories configuration.

    Returns:
        Dictionary containing category name, health impact, advisory, alert level, and hex color.
    """
    if categories_cfg is None:
        categories_cfg = load_categories()

    for cat in categories_cfg["categories"]:
        if cat["name"].lower() == category_name.lower():
            return {
                "category": cat["name"],
                "aqi_range": f"{cat['aqi_min']}–{cat['aqi_max']}",
                "color": cat["color"],
                "text_color": cat.get("text_color", "#ffffff"),
                "health_impact": cat["health_impact"],
                "advisory": cat["advisory"],
                "alert_level": cat["alert_level"],
            }

    return {
        "category": category_name or "Unavailable",
        "aqi_range": "N/A",
        "color": "#9e9e9e",
        "text_color": "#ffffff",
        "health_impact": "Data unavailable or out of bounds.",
        "advisory": "Maintain normal awareness.",
        "alert_level": "UNKNOWN",
    }

