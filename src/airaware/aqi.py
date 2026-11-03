"""AQI calculation and sub-index interpolation engine according to CPCB guidelines.

Reference: Central Pollution Control Board (CPCB), Ministry of Environment,
Forest and Climate Change, Govt of India - "National Air Quality Index" (2014).
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import yaml
import math


def get_config_path(filename: str) -> Path:
    """Resolve config file path relative to project root or config directory."""
    # Look in ../../config, ../config, ./config
    current = Path(__file__).resolve().parent
    candidates = [
        current.parent.parent / "config" / filename,
        current.parent / "config" / filename,
        Path("config") / filename,
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_breakpoints(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load pollutant breakpoints from YAML config."""
    path = config_path or get_config_path("breakpoints.yaml")
    if not path.exists():
        raise FileNotFoundError(f"Breakpoints config not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_categories(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load AQI categories and descriptors from YAML config."""
    path = config_path or get_config_path("categories.yaml")
    if not path.exists():
        raise FileNotFoundError(f"Categories config not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_qc_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load quality control configuration from YAML config."""
    path = config_path or get_config_path("qc.yaml")
    if not path.exists():
        raise FileNotFoundError(f"QC config not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_subindex(pollutant: str, concentration: Optional[float], breakpoints_cfg: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """Calculate the sub-index for a specific pollutant concentration using linear interpolation.

    Formula:
        I_p = ((I_hi - I_lo) / (BP_hi - BP_lo)) * (C_p - BP_lo) + I_lo

    Args:
        pollutant: Pollutant identifier, e.g. 'pm25' or 'pm10'.
        concentration: 24-hour average concentration in µg/m³.
        breakpoints_cfg: Optional preloaded breakpoints dict.

    Returns:
        Sub-index value (rounded to 1 decimal place), or None if concentration is invalid/NaN.
    """
    if concentration is None or math.isnan(concentration) or concentration < 0:
        return None

    if breakpoints_cfg is None:
        breakpoints_cfg = load_breakpoints()

    pollutant_key = pollutant.lower().replace(".", "")
    if pollutant_key not in breakpoints_cfg:
        raise ValueError(f"Unknown pollutant '{pollutant}'. Configured: {list(breakpoints_cfg.keys())}")

    brackets = breakpoints_cfg[pollutant_key]

    # Find the appropriate bracket; also handle decimal gaps between integer bracket endpoints
    # (e.g. CPCB breakpoints define integer boundaries: 30/31, 60/61, etc. but portal exports
    # may yield fractional concentrations like 60.33 that fall in the inter-bracket gap).
    for i, b in enumerate(brackets):
        bp_lo = float(b["bp_lo"])
        bp_hi = float(b["bp_hi"])
        i_lo = float(b["i_lo"])
        i_hi = float(b["i_hi"])

        if bp_lo <= concentration <= bp_hi:
            subindex = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (concentration - bp_lo) + i_lo
            return round(subindex, 1)

        # Handle gap between consecutive integer brackets (e.g. value=60.33, gap=[60,61])
        if i + 1 < len(brackets):
            next_b = brackets[i + 1]
            next_bp_lo = float(next_b["bp_lo"])
            next_i_lo = float(next_b["i_lo"])
            next_bp_hi = float(next_b["bp_hi"])
            next_i_hi = float(next_b["i_hi"])
            if bp_hi < concentration < next_bp_lo:
                # Interpolate using the next bracket (concentration is just above current ceiling)
                subindex = ((next_i_hi - next_i_lo) / (next_bp_hi - next_bp_lo)) * (concentration - next_bp_lo) + next_i_lo
                return round(subindex, 1)

    # If concentration exceeds the highest configured bracket, extrapolate using the top bracket
    top = brackets[-1]
    bp_lo = float(top["bp_lo"])
    bp_hi = float(top["bp_hi"])
    i_lo = float(top["i_lo"])
    i_hi = float(top["i_hi"])
    if concentration > bp_hi:
        subindex = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (concentration - bp_lo) + i_lo
        return min(500.0, round(subindex, 1))

    return None


def aqi_from_pollutants(
    pollutants: Dict[str, Optional[float]],
    breakpoints_cfg: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[float], Optional[str], Dict[str, Optional[float]]]:
    """Compute overall AQI from a dictionary of pollutant concentrations.

    According to CPCB rules:
    - Overall AQI is the MAXIMUM of individual sub-indices.
    - At least PM2.5 or PM10 must be present.
    - The pollutant causing the maximum sub-index is the dominant (prominent) pollutant.

    Args:
        pollutants: Dictionary mapping pollutant names (e.g. 'pm25', 'pm10') to concentrations.
        breakpoints_cfg: Optional preloaded breakpoints.

    Returns:
        Tuple of (max_subindex, dominant_pollutant_name, subindices_dict)
    """
    if breakpoints_cfg is None:
        breakpoints_cfg = load_breakpoints()

    subindices: Dict[str, Optional[float]] = {}
    for pol, conc in pollutants.items():
        subindices[pol] = calculate_subindex(pol, conc, breakpoints_cfg)

    valid_subindices = {k: v for k, v in subindices.items() if v is not None}

    if not valid_subindices:
        return None, None, subindices

    # Find maximum sub-index and dominant pollutant
    max_val = -1.0
    dominant_pol = None

    for pol, subidx in valid_subindices.items():
        if subidx > max_val:
            max_val = subidx
            dominant_pol = pol

    return max_val, dominant_pol, subindices


def categorize_aqi(aqi: Optional[float], categories_cfg: Optional[Dict[str, Any]] = None) -> Tuple[str, str, str]:
    """Map an AQI numerical value to its official CPCB category, color, and health impact statement.

    Args:
        aqi: Numerical AQI value (0 to 500+).
        categories_cfg: Optional preloaded categories dict.

    Returns:
        Tuple of (category_name, hex_color, health_impact)
    """
    if aqi is None or math.isnan(aqi):
        return "Unavailable", "#9e9e9e", "Insufficient data to compute AQI."

    if categories_cfg is None:
        categories_cfg = load_categories()

    rounded_aqi = round(aqi)

    for cat in categories_cfg["categories"]:
        if cat["aqi_min"] <= rounded_aqi <= cat["aqi_max"]:
            return cat["name"], cat["color"], cat["health_impact"]

    if rounded_aqi > 500:
        last = categories_cfg["categories"][-1]
        return last["name"], last["color"], last["health_impact"]

    return "Unknown", "#9e9e9e", "Unknown AQI range."

