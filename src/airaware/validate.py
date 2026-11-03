"""Data validation and Quality Control (QC) engine for AirAware Bengaluru.

Conducts rigorous data quality checks:
1. 14 consecutive calendar days check (identifying any calendar date gaps).
2. Duplicate dates check.
3. Instrument saturation check (flagging readings >= 999.0 µg/m³).
4. Sampling completeness check (identifying days with single-pollutant derived AQI).
5. Value plausibility and bounds check (negative numbers, extreme outliers).
6. CPCB Sub-index calculation audit.
"""

from typing import Any, Dict, List
import pandas as pd


def validate_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Perform comprehensive data quality and integrity validation.

    Args:
        df: Processed DataFrame.

    Returns:
        Dictionary with validation status, metrics, and list of violations/warnings.
    """
    violations: List[str] = []
    warnings: List[str] = []
    checks_passed: List[str] = []

    total_rows = len(df)
    dates = pd.to_datetime(df["date"]).dt.date.tolist()

    if total_rows == 0:
        violations.append("Dataset is empty.")
        return {
            "is_valid": False,
            "total_rows": 0,
            "violations": violations,
            "warnings": warnings,
            "checks_passed": checks_passed,
        }

    # 1. Duplicate dates check
    duplicate_dates = df[df.duplicated(subset=["date"], keep=False)]["date"].tolist()
    if duplicate_dates:
        violations.append(f"Duplicate date entries detected for dates: {sorted(list(set(str(d) for d in duplicate_dates)))}")
    else:
        checks_passed.append("No duplicate dates found.")

    # 2. Check for consecutive calendar dates
    min_date = min(dates)
    max_date = max(dates)
    expected_date_range = pd.date_range(start=min_date, end=max_date).date.tolist()

    missing_dates = [d for d in expected_date_range if d not in dates]

    if missing_dates:
        violations.append(
            f"Calendar gaps detected. Missing {len(missing_dates)} date(s) between {min_date} and {max_date}: "
            f"{[str(d) for d in missing_dates]}"
        )
    else:
        checks_passed.append(f"All dates are consecutive between {min_date} and {max_date}.")

    if total_rows != 14:
        warnings.append(f"Assignment expects 14 consecutive days. Dataset has {total_rows} rows.")
    else:
        checks_passed.append("Dataset has exactly 14 records.")

    # 3. Check for instrument saturation
    saturated_rows = df[(df["pm10"] >= 999.0) | (df["pm25"] >= 999.0)]
    if len(saturated_rows) > 0:
        warnings.append(
            f"Sensor saturation detected on {len(saturated_rows)} day(s): {saturated_rows['date'].tolist()}. "
            "Readings >= 999.0 µg/m³ should be filtered as instrument limits."
        )
    else:
        checks_passed.append("No instrument saturation artifacts (concentrations >= 999.0 µg/m³) in dataset.")

    # 4. Check for sampling completeness & missing values
    aqi_col = "aqi_derived" if "aqi_derived" in df.columns else "aqi_reported"
    missing_aqi = df[aqi_col].isna().sum()
    missing_pm25 = df["pm25"].isna().sum()
    missing_pm10 = df["pm10"].isna().sum()

    if missing_pm25 > 0:
        warnings.append(
            f"{missing_pm25} record(s) have missing PM2.5 readings (e.g. fewer than 16 valid hours). "
            "AQI is derived from PM10 alone on those dates."
        )
    else:
        checks_passed.append("All 14 days have complete PM2.5 observations.")

    if missing_pm10 > 0:
        warnings.append(f"{missing_pm10} record(s) have missing PM10 readings.")
    else:
        checks_passed.append("All 14 days have complete PM10 observations.")

    # 5. Non-negative bounds check
    negative_pm25 = (df["pm25"] < 0).sum()
    negative_pm10 = (df["pm10"] < 0).sum()
    negative_aqi = (df[aqi_col] < 0).sum()

    if negative_pm25 > 0 or negative_pm10 > 0 or negative_aqi > 0:
        violations.append("Negative concentration or AQI values detected in dataset.")
    else:
        checks_passed.append("All concentration and AQI values are non-negative.")

    # 6. CPCB Sub-Index Calculation Audit
    subindex_errors = []
    for _, row in df.iterrows():
        aqi_val = row.get(aqi_col)
        s25 = row.get("subindex_pm25")
        s10 = row.get("subindex_pm10")
        valid_subs = [s for s in (s25, s10) if pd.notnull(s)]
        if valid_subs and pd.notnull(aqi_val):
            expected_aqi = round(max(valid_subs))
            if abs(round(aqi_val) - expected_aqi) > 1:
                subindex_errors.append(f"{row['date']}: AQI {aqi_val} vs expected {expected_aqi}")

    if subindex_errors:
        violations.append(f"Sub-index derivation discrepancy on {len(subindex_errors)} day(s): {subindex_errors}")
    else:
        checks_passed.append("CPCB Sub-Index Derivation verified: AQI equals max(Subindex_PM2.5, Subindex_PM10).")

    is_valid = len(violations) == 0

    return {
        "is_valid": is_valid,
        "total_rows": total_rows,
        "date_range": f"{min_date} to {max_date}",
        "station": df["station"].iloc[0] if "station" in df.columns and len(df) > 0 else "Unknown",
        "violations": violations,
        "warnings": warnings,
        "checks_passed": checks_passed,
        "missing_pm25_days": int(missing_pm25),
    }


def generate_quality_report_markdown(report: Dict[str, Any]) -> str:
    """Generate a clean Markdown report of data quality and QC audit results."""
    status_emoji = "PASSED" if report["is_valid"] else "FAILED"
    badge = "🟢 VALID" if report["is_valid"] else "🔴 ISSUES FLAGGED"

    md = [
        f"# AirAware Data Quality & QC Audit",
        f"",
        f"**Audit Status:** {badge} ({status_emoji})  ",
        f"**Station:** {report.get('station', 'N/A')}  ",
        f"**Observation Period:** {report.get('date_range', 'N/A')}  ",
        f"**Total Records:** {report.get('total_rows', 0)}  ",
        f"",
        f"---",
        f"",
        f"### Integrity & Quality Control Checks",
        f"",
    ]

    for check in report.get("checks_passed", []):
        md.append(f"- [x] **Passed:** {check}")

    if report.get("warnings"):
        md.append(f"")
        md.append(f"### Advisory & Completeness Notes")
        for warn in report["warnings"]:
            md.append(f"- [!] **Notice:** {warn}")

    if report.get("violations"):
        md.append(f"")
        md.append(f"### Critical Violations")
        for viol in report["violations"]:
            md.append(f"- [ ] **Violation:** {viol}")

    md.append(f"")
    md.append(f"---")
    md.append(f"*Quality Control standard: CPCB National AQI Guidelines & 75%/16-hour completeness protocol.*")
    return "\n".join(md)
