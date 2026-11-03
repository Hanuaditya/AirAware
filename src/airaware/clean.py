"""Data cleaning and derivation pipeline for AirAware Bengaluru.

Takes raw CPCB CSV data, enforces schema and data types, parses dates,
recomputes sub-indices according to official CPCB linear interpolation formulas,
identifies daily dominant pollutants, evaluates regulatory standards,
and writes the cleaned dataset to data/processed/aqi_14day.csv while preserving
raw inputs untouched.
"""

from pathlib import Path
from typing import Optional, Union
import numpy as np
import pandas as pd

from airaware.aqi import calculate_subindex, categorize_aqi, load_breakpoints


REQUIRED_COLUMNS = [
    "date",
    "station",
    "city",
    "pm10",
]


def clean_dataframe(df: pd.DataFrame, breakpoints_cfg: Optional[dict] = None) -> pd.DataFrame:
    """Clean, type-cast, and compute all derived metrics for air quality data.

    Args:
        df: Raw DataFrame matching expected columns.
        breakpoints_cfg: Optional preloaded breakpoints.

    Returns:
        DataFrame with standardized columns and derived fields.
    """
    df = df.copy()

    # Standardize column names (strip, lowercase)
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Support aqi_derived or aqi_reported
    if "aqi_reported" in df.columns and "aqi_derived" not in df.columns:
        df["aqi_derived"] = df["aqi_reported"]

    # Check required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"Missing required column in dataset: '{col}'")

    if "pm25" not in df.columns:
        df["pm25"] = np.nan

    # Clean date
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df.sort_values(by="date").reset_index(drop=True)

    # Clean textual fields
    df["station"] = df["station"].astype(str).str.strip()
    df["city"] = df["city"].astype(str).str.strip()

    if "source" not in df.columns:
        df["source"] = "CPCB CAAQMS Data Repository"
    else:
        df["source"] = df["source"].fillna("CPCB CAAQMS Data Repository").astype(str).str.strip()

    if "accessed_on" not in df.columns:
        df["accessed_on"] = pd.to_datetime("today").date()
    else:
        df["accessed_on"] = pd.to_datetime(df["accessed_on"]).dt.date

    # Clean numeric fields (coerce errors to NaN; never invent values)
    numeric_cols = ["pm25", "pm10"]
    if "aqi_derived" in df.columns:
        numeric_cols.append("aqi_derived")

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Load breakpoints
    if breakpoints_cfg is None:
        breakpoints_cfg = load_breakpoints()

    # Derive PM subindices
    sub_pm25 = []
    sub_pm10 = []
    aqi_from_pm_list = []
    dominant_pm_list = []
    category_derived_list = []
    flag_list = []

    for _, row in df.iterrows():
        p25 = row["pm25"] if pd.notnull(row["pm25"]) else None
        p10 = row["pm10"] if pd.notnull(row["pm10"]) else None
        derived_input_aqi = row.get("aqi_derived") if pd.notnull(row.get("aqi_derived")) else None

        s25 = calculate_subindex("pm25", p25, breakpoints_cfg)
        s10 = calculate_subindex("pm10", p10, breakpoints_cfg)

        sub_pm25.append(s25)
        sub_pm10.append(s10)

        # Compute PM-derived AQI (maximum of available constituent PM sub-indices)
        valid_pm_subs = [s for s in (s25, s10) if s is not None]
        if valid_pm_subs:
            pm_aqi = max(valid_pm_subs)
            aqi_from_pm_list.append(round(pm_aqi))

            if s25 is not None and s10 is not None:
                if s25 > s10:
                    dominant_pm_list.append("PM2.5")
                elif s10 > s25:
                    dominant_pm_list.append("PM10")
                else:
                    dominant_pm_list.append("PM2.5 & PM10")
            elif s25 is not None:
                dominant_pm_list.append("PM2.5")
            else:
                dominant_pm_list.append("PM10")
        else:
            aqi_from_pm_list.append(np.nan)
            dominant_pm_list.append("None")

        eval_aqi = derived_input_aqi if derived_input_aqi is not None else (pm_aqi if valid_pm_subs else None)
        cat_name, _, _ = categorize_aqi(eval_aqi)
        category_derived_list.append(cat_name)

        # Quality flags
        flags = []
        if str(row.get("qc_flag", "")).strip() == "SINGLE_POLLUTANT_AQI" or (p25 is None and p10 is not None):
            flags.append("SINGLE_POLLUTANT_AQI")
        elif str(row.get("qc_flag", "")).strip() == "INSUFFICIENT_DATA":
            flags.append("INSUFFICIENT_DATA")

        if p25 is None and "SINGLE_POLLUTANT_AQI" not in flags:
            flags.append("MISSING_PM25")
        if p10 is None:
            flags.append("MISSING_PM10")

        if p10 is not None and p10 >= 999.0:
            flags.append("SATURATION_ARTIFACT")
        if p25 is not None and p25 >= 999.0:
            flags.append("SATURATION_ARTIFACT")

        if not flags:
            flag_list.append("VALID")
        else:
            flag_list.append("; ".join(flags))

    df["subindex_pm25"] = sub_pm25
    df["subindex_pm10"] = sub_pm10
    df["aqi_derived"] = aqi_from_pm_list
    df["dominant_pm"] = dominant_pm_list
    df["category_derived"] = category_derived_list
    df["aqi_category"] = category_derived_list
    df["data_quality_flag"] = flag_list

    # Exceedance indicators
    # India NAAQS (24-h): PM2.5 = 60 µg/m³, PM10 = 100 µg/m³
    # WHO 2021 Guideline (24-h): PM2.5 = 15 µg/m³, PM10 = 45 µg/m³
    df["exceeds_naaqs_pm25"] = df["pm25"].apply(lambda x: x > 60.0 if pd.notnull(x) else False)
    df["exceeds_naaqs_pm10"] = df["pm10"].apply(lambda x: x > 100.0 if pd.notnull(x) else False)
    df["exceeds_who_pm25"] = df["pm25"].apply(lambda x: x > 15.0 if pd.notnull(x) else False)
    df["exceeds_who_pm10"] = df["pm10"].apply(lambda x: x > 45.0 if pd.notnull(x) else False)

    # PM2.5 to PM10 ratio (valid only when both are present)
    df["pm_ratio"] = df.apply(
        lambda r: (r["pm25"] / r["pm10"]) if (pd.notnull(r["pm25"]) and pd.notnull(r["pm10"]) and r["pm10"] > 0) else np.nan,
        axis=1,
    )

    return df


def process_dataset(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """Read raw CSV, clean it, and write processed dataset."""
    input_p = Path(input_path)
    if not input_p.exists():
        raise FileNotFoundError(f"Input data file not found: {input_p}")

    df_raw = pd.read_csv(input_p)
    df_clean = clean_dataframe(df_raw)

    if output_path is not None:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_csv(out_p, index=False)

    return df_clean
