"""Unit tests for data validation, gap detection, and CPCB sub-index consistency checks."""

import numpy as np
import pandas as pd
import pytest

from airaware.clean import clean_dataframe
from airaware.validate import validate_dataset


def test_calendar_gap_detection():
    """Verify that a missing date inside an observation sequence triggers a gap violation."""
    data = {
        "date": ["2026-11-01", "2026-11-02", "2026-11-04"],  # Missing 2026-11-03!
        "station": ["BTM Layout"] * 3,
        "city": ["Bengaluru"] * 3,
        "pm25": [38.0, 42.0, 45.0],
        "pm10": [70.0, 75.0, 80.0],
    }
    df = clean_dataframe(pd.DataFrame(data))
    report = validate_dataset(df)

    assert not report["is_valid"]
    gap_violations = [v for v in report["violations"] if "Calendar gaps detected" in v]
    assert len(gap_violations) == 1
    assert "2026-11-03" in gap_violations[0]


def test_duplicate_date_detection():
    """Verify that duplicate rows for the same date trigger a violation."""
    data = {
        "date": ["2026-11-01", "2026-11-01", "2026-11-02"],
        "station": ["BTM Layout"] * 3,
        "city": ["Bengaluru"] * 3,
        "aqi_derived": [65, 68, 70],
        "pm25": [38, 40, 42],
        "pm10": [70, 72, 75],
        "subindex_pm25": [63.0, 67.0, 70.0],
        "subindex_pm10": [65.0, 68.0, 70.0],
    }
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    report = validate_dataset(df)

    assert not report["is_valid"]
    dup_violations = [v for v in report["violations"] if "Duplicate date entries detected" in v]
    assert len(dup_violations) == 1


def test_cpcb_subindex_consistency_violation():
    """Verify that an inconsistent AQI lower than constituent PM sub-index triggers a violation."""
    data = {
        "date": ["2026-11-01"],
        "station": ["BTM Layout"],
        "city": ["Bengaluru"],
        "aqi_derived": [80.0],  # Inconsistent: PM2.5 sub-index is ~138.6
        "pm25": [72.0],
        "pm10": [60.0],
        "subindex_pm25": [138.6],
        "subindex_pm10": [60.0],
    }
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    report = validate_dataset(df)

    assert not report["is_valid"]
    assert any("Sub-index derivation discrepancy" in v for v in report["violations"])


def test_valid_consecutive_14_days():
    """Verify that a compliant 14-day dataset passes all validation rules cleanly."""
    dates = pd.date_range("2026-10-01", periods=14, freq="D").strftime("%Y-%m-%d").tolist()
    data = {
        "date": dates,
        "station": ["BTM Layout, Bengaluru - CPCB"] * 14,
        "city": ["Bengaluru"] * 14,
        "pm25": [40.0 + i for i in range(14)],
        "pm10": [70.0 + i for i in range(14)],
    }
    df = clean_dataframe(pd.DataFrame(data))
    report = validate_dataset(df)

    assert report["is_valid"]
    assert len(report["violations"]) == 0
    assert report["total_rows"] == 14
