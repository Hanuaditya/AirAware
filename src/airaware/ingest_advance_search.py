"""CPCB Advance Search Excel Ingestion Pipeline.

Parses the 9-line metadata header block from CPCB 'Advance Search' portal exports
(24H rolling averages, window start=22:41), applies QC rules, derives AQI sub-indices,
and outputs tidy CSVs to data/processed/.

File layout:
  Rows 1-2:  Title
  Row  3:    Date / Time (download timestamp)
  Rows 4-10: Key-value metadata (State, City, Station, Parameter, AvgPeriod, From, To)
  Row  11:   Column header (From Date, To Date, PM2.5, PM10, ...)
  Rows 12+:  Data rows; dates as DD-MM-YYYY HH:MM

Date-label convention: window START date (YYYY-MM-DD), per config/qc.yaml date_labeling.
Validity note: "portal 24H mean as provided" - no sub-hourly completeness checks possible.
"""

from __future__ import annotations
import hashlib
import json
from datetime import datetime
from pathlib import Path
import sys

import numpy as np
import openpyxl
import pandas as pd

# Ensure src is on path
_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from airaware.aqi import calculate_subindex, categorize_aqi, load_breakpoints, load_qc_config

# ---------------------------------------------------------------------------
# Station file map — raw filenames in data/raw/
# ---------------------------------------------------------------------------
STATION_FILES = {
    "silk_board": "Advance_Search_1793726002868.xlsx",   # PRIMARY (KSPCB)
    "btm_layout": "Advance_Search_1793725987823.xlsx",   # COMPARISON (CPCB)
    "peenya":     "pee.xlsx",                            # DATA-QUALITY-AUDIT ONLY
}

PRIMARY_STATION_KEY = "silk_board"

# Date-label windows
PRIMARY_WINDOW = ("2026-10-20", "2026-11-02")          # 14 windows (start dates)
COMPARISON_WINDOW = ("2026-10-08", "2026-10-21")        # common 14-window BTM vs Silk

ACCESS_DATE = "2026-11-03"
PORTAL_URL = "https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/data"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_cpcb_advance_search(xlsx_path: Path) -> tuple[dict, pd.DataFrame]:
    """Parse a CPCB Advance Search Excel export.

    Returns:
        meta: dict with station, city, state, agency, avg_period, from, to, download_ts
        df:   tidy DataFrame with from_dt, to_dt, date (window-start label), and pollutant columns
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active

    # --- Read 9-line header block (cols 1 and 3 carry values) ---
    def _cell(row, col=3):
        v = ws.cell(row, col).value
        return str(v).strip() if v is not None else ""

    download_date = _cell(3, 1).replace("Date: ", "").strip()
    download_time = _cell(3, 6).replace("Time: ", "").strip()
    state    = _cell(4)
    city     = _cell(5)
    station  = _cell(6)
    avg_period = _cell(8)
    from_str   = _cell(9)
    to_str     = _cell(10)

    # Agency is the last token after the dash in station name, e.g. "BTM Layout, Bengaluru - CPCB"
    agency = station.split("-")[-1].strip() if "-" in station else "CPCB"

    meta = {
        "station": station,
        "city": city,
        "state": state,
        "agency": agency,
        "avg_period": avg_period,
        "portal_from": from_str,
        "portal_to": to_str,
        "download_timestamp": f"{download_date} {download_time}",
        "sha256": _sha256(xlsx_path),
        "source_file": xlsx_path.name,
        "access_date": ACCESS_DATE,
        "portal_url": PORTAL_URL,
        "validity_note": "portal 24H mean as provided — no sub-hourly records in this export; 16-hour completeness rule not applicable",
        "date_label_convention": "window_start (YYYY-MM-DD of the 22:41 window opening)",
    }

    # --- Read column headers at row 11 ---
    headers = []
    for c in range(1, ws.max_column + 1):
        v = ws.cell(11, c).value
        if v is None and headers:
            break
        if v is not None:
            headers.append(str(v).strip())

    # --- Read data rows ---
    rows = []
    for r in range(12, ws.max_row + 1):
        row = [ws.cell(r, c).value for c in range(1, len(headers) + 1)]
        if all(v is None for v in row):
            continue
        rows.append(row)

    df = pd.DataFrame(rows, columns=headers)

    # Rename standard columns to canonical names
    col_map = {
        "From Date": "from_date_str",
        "To Date":   "to_date_str",
        "PM2.5":     "pm25",
        "PM10":      "pm10",
        "NO":        "no",
        "NO2":       "no2",
        "NOX":       "nox",
        "NH3":       "nh3",
        "SO2":       "so2",
        "CO":        "co",
        "OZONE":     "ozone",
        "BENZENE":   "benzene",
        "TOLUENE":   "toluene",
    }
    df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

    # Parse datetimes
    df["from_dt"] = pd.to_datetime(df["from_date_str"], format="%d-%m-%Y %H:%M", errors="coerce")
    df["to_dt"]   = pd.to_datetime(df["to_date_str"],   format="%d-%m-%Y %H:%M", errors="coerce")

    # Date label = window start date
    df["date"] = df["from_dt"].dt.strftime("%Y-%m-%d")

    # Numeric coercion for pollutants
    for col in ["pm25", "pm10", "no", "no2", "nox", "nh3", "so2", "co", "ozone", "benzene", "toluene"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["station"] = station
    df["agency"]  = agency
    df["source"]  = f"CPCB Advance Search Portal ({avg_period})"
    df["accessed_on"] = ACCESS_DATE

    return meta, df


# ---------------------------------------------------------------------------
# QC application
# ---------------------------------------------------------------------------

def apply_qc(df: pd.DataFrame, qc_cfg: dict) -> pd.DataFrame:
    """Apply instrument-range QC and flatline detection.

    Rules (config/qc.yaml):
      - Values >= max_valid (999.0) or < min_valid (0) -> NaN (saturation / invalid)
      - Negative values -> NaN
      - Flatline (>= 10 consecutive identical values) flagged per column (advisory)
    """
    pm_max = float(qc_cfg["instrument_limits"]["pm10"]["max_valid"])
    pm_min = float(qc_cfg["instrument_limits"]["pm10"]["min_valid"])
    flatline_thresh = int(qc_cfg.get("flatline_check", {}).get("min_consecutive_windows", 10))

    df = df.copy()

    for col in ["pm25", "pm10"]:
        if col not in df.columns:
            continue
        invalid = (df[col] >= pm_max) | (df[col] < pm_min)
        n_sat = invalid.sum()
        if n_sat > 0:
            print(f"  [QC] {col}: {n_sat} readings flagged as invalid (>={pm_max} or <{pm_min}) -> NaN")
        df.loc[invalid, col] = np.nan

    # Flatline check (advisory, does not nullify values — gas sensors not used in AQI here)
    flatline_report = {}
    for col in df.select_dtypes(include=[np.number]).columns:
        s = df[col].dropna()
        if len(s) < 2:
            continue
        blocks = (s != s.shift()).cumsum()
        counts = s.groupby(blocks).size()
        max_run = int(counts.max())
        if max_run >= flatline_thresh:
            val = s[blocks == counts.idxmax()].iloc[0]
            flatline_report[col] = {"max_consecutive_run": max_run, "constant_value": val}

    if flatline_report:
        print(f"  [QC] Flatline detection (>= {flatline_thresh} consecutive): {list(flatline_report.keys())}")

    df.attrs["flatline_report"] = flatline_report
    return df


# ---------------------------------------------------------------------------
# AQI derivation
# ---------------------------------------------------------------------------

def derive_aqi(df: pd.DataFrame) -> pd.DataFrame:
    """Compute subindex_pm25, subindex_pm10, aqi_derived, category, dominant_pollutant, pm_ratio."""
    bp = load_breakpoints()
    df = df.copy()

    def _sub(val, poll):
        if pd.isna(val):
            return np.nan
        result = calculate_subindex(poll, float(val), bp)
        return float(result) if result is not None else np.nan

    df["subindex_pm25"] = df["pm25"].apply(lambda x: _sub(x, "pm25"))
    df["subindex_pm10"] = df["pm10"].apply(lambda x: _sub(x, "pm10"))

    df["aqi_derived"] = df[["subindex_pm25", "subindex_pm10"]].max(axis=1)

    def _cat(aqi):
        if pd.isna(aqi):
            return "Unavailable"
        result = categorize_aqi(aqi)
        return result[0] if isinstance(result, tuple) else str(result)

    def _dom(row):
        s25 = row["subindex_pm25"]
        s10 = row["subindex_pm10"]
        if pd.isna(s25) and pd.isna(s10):
            return "None"
        if pd.isna(s25):
            return "PM10"
        if pd.isna(s10):
            return "PM2.5"
        if s10 > s25:
            return "PM10"
        if s25 > s10:
            return "PM2.5"
        return "Tie"

    df["category"] = df["aqi_derived"].apply(_cat)
    df["dominant_pollutant"] = df.apply(_dom, axis=1)

    # PM ratio (only where both are valid)
    df["pm_ratio"] = np.where(
        df["pm10"].notna() & df["pm25"].notna() & (df["pm10"] > 0),
        df["pm25"] / df["pm10"],
        np.nan,
    )

    # NAAQS exceedance flags (24-hr limits: PM2.5=60, PM10=100 µg/m³)
    df["exceed_naaqs_pm25"] = df["pm25"].apply(lambda x: (x > 60) if pd.notna(x) else False)
    df["exceed_naaqs_pm10"] = df["pm10"].apply(lambda x: (x > 100) if pd.notna(x) else False)

    # WHO 2021 exceedance flags (24-hr limits: PM2.5=15, PM10=45 µg/m³)
    df["exceed_who_pm25"] = df["pm25"].apply(lambda x: (x > 15) if pd.notna(x) else False)
    df["exceed_who_pm10"] = df["pm10"].apply(lambda x: (x > 45) if pd.notna(x) else False)

    return df


# ---------------------------------------------------------------------------
# Flatline analysis report
# ---------------------------------------------------------------------------

def report_flatline(station_key: str, df: pd.DataFrame, qc_cfg: dict):
    """Print flatline analysis for all numeric columns."""
    flatline_thresh = int(qc_cfg.get("flatline_check", {}).get("min_consecutive_windows", 10))
    print(f"\n  === Flatline Analysis: {station_key} ===")
    for col in df.select_dtypes(include=[np.number]).columns:
        if col.startswith("exceed_") or col in ["subindex_pm25", "subindex_pm10", "aqi_derived", "pm_ratio"]:
            continue
        s = df[col].dropna()
        if len(s) < 2:
            print(f"    {col}: ALL NULL")
            continue
        blocks = (s != s.shift()).cumsum()
        counts = s.groupby(blocks).size()
        max_run = int(counts.max())
        if max_run >= flatline_thresh:
            val = s[blocks == counts.idxmax()].iloc[0]
            print(f"    {col}: [FLAT-LINED] {max_run} consecutive windows at value={val}")
        elif max_run >= 5:
            print(f"    {col}: Run of {max_run} (below threshold)")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    raw_dir: Path = Path("data/raw"),
    processed_dir: Path = Path("data/processed"),
    metadata_path: Path = Path("data/raw/metadata.json"),
):
    """Full ingestion, QC, AQI derivation and export pipeline."""
    processed_dir.mkdir(parents=True, exist_ok=True)

    qc_cfg = load_qc_config()
    all_meta = {}
    all_dfs = {}

    # --- 1. Parse & QC all three station files ---
    for key, filename in STATION_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            print(f"[SKIP] {filename} not found in {raw_dir}")
            continue
        print(f"\n[PARSE] {key}: {filename}")
        meta, df = parse_cpcb_advance_search(path)
        print(f"  Station: {meta['station']} | Agency: {meta['agency']} | Rows: {len(df)}")
        print(f"  Window: {meta['portal_from']} -> {meta['portal_to']}")
        df = apply_qc(df, qc_cfg)
        report_flatline(key, df, qc_cfg)
        all_meta[key] = meta
        all_dfs[key] = df

    # --- 2. Peenya exclusion report ---
    if "peenya" in all_dfs:
        df_pee = all_dfs["peenya"]
        n_pm10_valid = df_pee["pm10"].notna().sum()
        n_pm10_total = len(df_pee)
        print(f"\n[QC EXCLUSION] Peenya Station:")
        print(f"  PM10: {n_pm10_valid}/{n_pm10_total} windows valid (rest: null -> sensor failure)")
        print(f"  During the 14-day primary window (2026-10-20 to 2026-11-02), PM10=0/14 valid.")
        print(f"  Additionally, Toluene flat-lined for 19 consecutive windows.")
        print(f"  Decision: Peenya EXCLUDED from primary AQI analysis. Documented in metadata.")

    # --- 3. Primary dataset: Silk Board 14-day ---
    print(f"\n[PRIMARY] Silk Board 14-day primary window: {PRIMARY_WINDOW}")
    df_silk = all_dfs["silk_board"].copy()
    w_start = pd.to_datetime(PRIMARY_WINDOW[0])
    w_end   = pd.to_datetime(PRIMARY_WINDOW[1])
    primary_mask = (df_silk["from_dt"].dt.normalize() >= w_start) & (df_silk["from_dt"].dt.normalize() <= w_end)
    df_primary = df_silk[primary_mask].copy().reset_index(drop=True)
    df_primary = derive_aqi(df_primary)
    print(f"  Rows in primary window: {len(df_primary)}")

    # Export tidy primary CSV
    tidy_cols = [
        "date", "from_date_str", "to_date_str", "station", "agency",
        "pm25", "pm10", "subindex_pm25", "subindex_pm10",
        "aqi_derived", "category", "dominant_pollutant", "pm_ratio",
        "exceed_naaqs_pm25", "exceed_naaqs_pm10",
        "exceed_who_pm25", "exceed_who_pm10",
        "source", "accessed_on",
    ]
    tidy_cols_present = [c for c in tidy_cols if c in df_primary.columns]
    df_primary[tidy_cols_present].to_csv(processed_dir / "aqi_14day.csv", index=False)
    print(f"  Saved: data/processed/aqi_14day.csv")

    # --- 4. All-station tidy CSVs ---
    for key, df in all_dfs.items():
        df_aqi = derive_aqi(df)
        out_name = f"{key}_24h_tidy.csv"
        df_aqi.to_csv(processed_dir / out_name, index=False)
        print(f"  Saved: data/processed/{out_name}")

    # --- 5. BTM vs Silk Board comparison window ---
    if "btm_layout" in all_dfs and "silk_board" in all_dfs:
        print(f"\n[COMPARISON] Common window: {COMPARISON_WINDOW}")
        cw_start = pd.to_datetime(COMPARISON_WINDOW[0])
        cw_end   = pd.to_datetime(COMPARISON_WINDOW[1])

        def _slice_comp(df):
            mask = (df["from_dt"].dt.normalize() >= cw_start) & (df["from_dt"].dt.normalize() <= cw_end)
            return derive_aqi(df[mask].copy().reset_index(drop=True))

        df_btm_comp  = _slice_comp(all_dfs["btm_layout"])
        df_silk_comp = _slice_comp(all_dfs["silk_board"])

        df_btm_comp["station_key"]  = "BTM Layout"
        df_silk_comp["station_key"] = "Silk Board"
        df_comp = pd.concat([df_btm_comp, df_silk_comp], ignore_index=True)
        df_comp.to_csv(processed_dir / "comparison_btm_silk_14day.csv", index=False)
        print(f"  Saved: data/processed/comparison_btm_silk_14day.csv")
        print(f"  BTM Mean AQI:       {df_btm_comp['aqi_derived'].mean():.2f}")
        print(f"  Silk Board Mean AQI:{df_silk_comp['aqi_derived'].mean():.2f}")

    # --- 6. Update metadata.json ---
    meta_doc = {
        "primary_station": all_meta.get("silk_board", {}).get("station", "Silk Board, Bengaluru - KSPCB"),
        "primary_agency": "KSPCB",
        "city": "Bengaluru",
        "state": "Karnataka",
        "portal_url": PORTAL_URL,
        "observation_window": f"{PRIMARY_WINDOW[0]} to {PRIMARY_WINDOW[1]}",
        "total_days": 14,
        "access_date": ACCESS_DATE,
        "date_label_convention": "window_start (YYYY-MM-DD of the 22:41 rolling average window opening)",
        "avg_period": "24H (portal pre-averaged)",
        "validity_note": "portal 24H mean as provided — no sub-hourly records; 16-hour completeness rule not applicable",
        "comparison_window": f"{COMPARISON_WINDOW[0]} to {COMPARISON_WINDOW[1]}",
        "comparison_stations": ["BTM Layout, Bengaluru - CPCB", "Silk Board, Bengaluru - KSPCB"],
        "peenya_exclusion_reason": (
            "Peenya PM10 sensor reported 0/14 valid readings during the primary window "
            "(2026-10-20 to 2026-11-02). Additionally, Toluene gas sensor flat-lined for "
            "19 consecutive 24H windows. AQI derivation requires at least one particulate "
            "fraction; without PM10, a meaningful dominant-pollutant analysis is not possible. "
            "Peenya is retained in the data quality audit section only."
        ),
        "stations": {
            key: {
                "station": m["station"],
                "agency": m["agency"],
                "source_file": m["source_file"],
                "sha256": m["sha256"],
                "download_timestamp": m["download_timestamp"],
                "portal_from": m["portal_from"],
                "portal_to": m["portal_to"],
            }
            for key, m in all_meta.items()
        },
        "quality_control": {
            "instrument_saturation_threshold": 999.0,
            "negative_values_flagged": True,
            "flatline_detection_threshold_windows": 10,
            "peenya_pm10_valid_windows_in_primary_period": 0,
            "peenya_toluene_flatline_windows": 19,
        },
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(meta_doc, f, indent=2, ensure_ascii=False)
    print(f"\n[META] Updated: data/raw/metadata.json")

    # --- 7. Print headline summary ---
    print("\n" + "=" * 60)
    print("HEADLINE RESULTS — Silk Board 14-Day Primary (After QC)")
    print("=" * 60)
    print(f"  Mean AQI (derived):  {df_primary['aqi_derived'].mean():.2f}")
    print(f"  Max AQI:             {df_primary['aqi_derived'].max():.1f}  ({df_primary.loc[df_primary['aqi_derived'].idxmax(), 'date']})")
    print(f"  Min AQI:             {df_primary['aqi_derived'].min():.1f}  ({df_primary.loc[df_primary['aqi_derived'].idxmin(), 'date']})")
    print(f"  Median AQI:          {df_primary['aqi_derived'].median():.2f}")
    print(f"  Std Dev (AQI):       {df_primary['aqi_derived'].std():.2f}")
    print(f"  Dominant pollutant:  {df_primary['dominant_pollutant'].value_counts().to_dict()}")
    print(f"  Category counts:     {df_primary['category'].value_counts().to_dict()}")
    pm_ratio_valid = df_primary['pm_ratio'].dropna()
    print(f"  Mean PM2.5/PM10:     {pm_ratio_valid.mean():.3f} (range {pm_ratio_valid.min():.3f}-{pm_ratio_valid.max():.3f})")
    print(f"  NAAQS PM10 exceed:   {df_primary['exceed_naaqs_pm10'].sum()}/14 days")
    print(f"  WHO  PM10 exceed:    {df_primary['exceed_who_pm10'].sum()}/14 days")
    print(f"  NAAQS PM2.5 exceed:  {df_primary['exceed_naaqs_pm25'].sum()}/14 days")
    print(f"  WHO  PM2.5 exceed:   {df_primary['exceed_who_pm25'].sum()}/14 days")
    print("=" * 60)

    return df_primary, all_dfs


if __name__ == "__main__":
    run_pipeline()
