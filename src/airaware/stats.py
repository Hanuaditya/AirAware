"""Statistical analytics and environmental metrics computation engine.

Computes:
1. Descriptive statistics (Mean, Max with date, Min with date, Median, Sample Std Dev)
   along with exact mathematical formulas and Excel equivalent formulas.
2. Category frequency counts across all 6 official CPCB categories (ensuring 0s are included).
3. Dominant pollutant distribution based on maximum constituent sub-indices.
4. Exceedance metrics against Indian NAAQS and WHO 2021 air quality guidelines.
5. Particulate ratio (PM2.5 / PM10) analysis with aerosol characterization.
"""

from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

from airaware.aqi import load_categories


def compute_descriptive_stats(df: pd.DataFrame, col: str = "aqi_derived") -> Dict[str, Any]:
    """Compute comprehensive descriptive statistics with formulas and Excel equivalents.

    Args:
        df: Cleaned DataFrame.
        col: Target numeric column name.

    Returns:
        Dictionary of statistics, dates of extremes, formulas, and Excel equivalents.
    """
    if col not in df.columns:
        if col == "aqi_derived" and "aqi_reported" in df.columns:
            col = "aqi_reported"
        elif col == "aqi_reported" and "aqi_derived" in df.columns:
            col = "aqi_derived"

    series = df[col].dropna()
    n = len(series)

    if n == 0:
        return {
            "column": col,
            "n": 0,
            "mean": np.nan,
            "median": np.nan,
            "min": np.nan,
            "min_date": "N/A",
            "max": np.nan,
            "max_date": "N/A",
            "std": np.nan,
            "formulas": {},
            "excel_equivalents": {},
        }

    mean_val = float(series.mean())
    median_val = float(series.median())
    min_val = float(series.min())
    max_val = float(series.max())
    std_val = float(series.std(ddof=1)) if n > 1 else 0.0

    # Locate dates for min and max
    min_rows = df[df[col] == min_val]
    max_rows = df[df[col] == max_val]

    min_date = str(min_rows["date"].iloc[0]) if len(min_rows) > 0 else "N/A"
    max_date = str(max_rows["date"].iloc[0]) if len(max_rows) > 0 else "N/A"

    return {
        "column": col,
        "n": n,
        "mean": round(mean_val, 2),
        "median": round(median_val, 2),
        "min": round(min_val, 2),
        "min_date": min_date,
        "max": round(max_val, 2),
        "max_date": max_date,
        "std": round(std_val, 2),
        "formulas": {
            "mean": r"\bar{x} = \frac{1}{N}\sum_{i=1}^N x_i",
            "median": r"\text{Middle value of sorted series}",
            "min": r"\min(x_i)",
            "max": r"\max(x_i)",
            "std": r"s = \sqrt{\frac{1}{N-1}\sum_{i=1}^N (x_i - \bar{x})^2}",
        },
        "excel_equivalents": {
            "mean": f"=AVERAGE({col.upper()}_RANGE)",
            "median": f"=MEDIAN({col.upper()}_RANGE)",
            "min": f"=MIN({col.upper()}_RANGE)",
            "max": f"=MAX({col.upper()}_RANGE)",
            "std": f"=STDEV.S({col.upper()}_RANGE)",
        },
    }


def compute_category_counts(
    df: pd.DataFrame,
    category_col: str = "category_derived",
    categories_cfg: Optional[dict] = None,
) -> pd.DataFrame:
    """Compute frequency counts for all six official CPCB categories (including zero counts).

    Args:
        df: Cleaned DataFrame.
        category_col: Name of category column to count.
        categories_cfg: Optional preloaded categories dict.

    Returns:
        DataFrame containing Category, AQI Range, Count, Percentage, and Color.
    """
    if categories_cfg is None:
        categories_cfg = load_categories()

    total_records = len(df)
    counts = df[category_col].value_counts().to_dict() if category_col in df.columns else {}

    rows = []
    for cat in categories_cfg["categories"]:
        name = cat["name"]
        count = counts.get(name, 0)
        pct = (count / total_records * 100.0) if total_records > 0 else 0.0

        rows.append({
            "Category": name,
            "AQI Range": f"{cat['aqi_min']}–{cat['aqi_max']}",
            "Count": count,
            "Percentage": round(pct, 1),
            "Color": cat["color"],
            "Health Impact": cat["health_impact"],
        })

    cat_df = pd.DataFrame(rows)
    return cat_df


def compute_dominant_pollutant_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute dominant pollutant counts and percentage breakdown."""
    # Support multiple column name conventions
    for _try in ("dominant_pollutant", "dominant_pm", "prominent_pollutant"):
        if _try in df.columns:
            dom_col = _try
            break
    else:
        dom_col = "dominant_pollutant"  # will raise KeyError below with a clear message
    valid_series = df[dom_col].dropna()
    total_valid = len(valid_series)

    if total_valid == 0:
        return {"total_days": 0, "counts": {}, "dominant_overall": "None", "summary_sentence": "No valid data."}

    counts = valid_series.value_counts().to_dict()
    dominant_overall = max(counts, key=counts.get) if counts else "None"
    dominant_days = counts.get(dominant_overall, 0)

    summary_sentence = (
        f"During the observation period, {dominant_overall} was identified as the dominant pollutant "
        f"on {dominant_days} of {total_valid} days ({round(dominant_days / total_valid * 100, 1)}%)."
    )

    return {
        "total_days": total_valid,
        "counts": counts,
        "dominant_overall": dominant_overall,
        "dominant_days": dominant_days,
        "dominant_percentage": round(dominant_days / total_valid * 100.0, 1),
        "summary_sentence": summary_sentence,
    }


def compute_exceedance_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute exceedance days against Indian NAAQS and WHO 2021 air quality guidelines."""
    total_days = len(df)
    if total_days == 0:
        return {}

    pm25_valid = df["pm25"].dropna()
    pm10_valid = df["pm10"].dropna()

    pm25_naaqs = int((pm25_valid > 60.0).sum())
    pm10_naaqs = int((pm10_valid > 100.0).sum())
    pm25_who = int((pm25_valid > 15.0).sum())
    pm10_who = int((pm10_valid > 45.0).sum())

    return {
        "total_days": total_days,
        "pm25_valid_days": len(pm25_valid),
        "pm10_valid_days": len(pm10_valid),
        "pm25_naaqs_exceedances": pm25_naaqs,
        "pm25_naaqs_pct": round(pm25_naaqs / len(pm25_valid) * 100, 1) if len(pm25_valid) > 0 else 0.0,
        "pm10_naaqs_exceedances": pm10_naaqs,
        "pm10_naaqs_pct": round(pm10_naaqs / len(pm10_valid) * 100, 1) if len(pm10_valid) > 0 else 0.0,
        "pm25_who_exceedances": pm25_who,
        "pm25_who_pct": round(pm25_who / len(pm25_valid) * 100, 1) if len(pm25_valid) > 0 else 0.0,
        "pm10_who_exceedances": pm10_who,
        "pm10_who_pct": round(pm10_who / len(pm10_valid) * 100, 1) if len(pm10_valid) > 0 else 0.0,
    }


def compute_pm_ratio_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze PM2.5 / PM10 ratio on days where both pollutants have valid measurements."""
    valid_ratios = df["pm_ratio"].dropna()
    n_valid = len(valid_ratios)

    if n_valid == 0:
        return {
            "n_valid_days": 0,
            "mean_ratio": np.nan,
            "min_ratio": np.nan,
            "max_ratio": np.nan,
            "interpretation": "Insufficient paired data",
        }

    mean_ratio = float(valid_ratios.mean())
    min_ratio = float(valid_ratios.min())
    max_ratio = float(valid_ratios.max())

    if mean_ratio >= 0.5:
        hint = (
            "Higher PM2.5/PM10 ratio (>0.5) hints at a dominant contribution from fine combustion particles, "
            "vehicular tailpipe emissions, or secondary chemical aerosol formation."
        )
    else:
        hint = (
            "Lower PM2.5/PM10 ratio (<0.5) hints at substantial contributions from coarse mechanical dust, "
            "unpaved road dust resuspension, and construction activities."
        )

    return {
        "n_valid_days": n_valid,
        "mean_ratio": round(mean_ratio, 3),
        "min_ratio": round(min_ratio, 3),
        "max_ratio": round(max_ratio, 3),
        "interpretation": hint,
    }
