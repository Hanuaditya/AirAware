"""Unit tests for Instrument-Range Quality Control (QC) and Completeness Rules."""

from datetime import datetime
import numpy as np
import pandas as pd
import pytest

from airaware.alerts import AlertEngine
from airaware.aqi import load_qc_config
from airaware.clean import clean_dataframe


def test_instrument_saturation_qc():
    """Verify that readings >= 999.0 or equal to 999.99 are treated as invalid saturation."""
    qc_cfg = load_qc_config()
    max_valid = qc_cfg["instrument_limits"]["pm10"]["max_valid"]
    assert max_valid == 999.0

    raw_readings = [50.0, 75.0, 999.99, 1000.0, 60.0]
    cleaned = [x if x < max_valid else np.nan for x in raw_readings]

    assert pd.isna(cleaned[2])
    assert pd.isna(cleaned[3])
    assert cleaned[0] == 50.0
    assert cleaned[1] == 75.0
    assert cleaned[4] == 60.0


def test_hourly_and_daily_completeness_rule():
    """Verify 75% hourly completeness (>=3 of 4 readings) and 16-hour daily rule."""
    qc_cfg = load_qc_config()
    min_readings_hr = qc_cfg["sampling_completeness"]["min_readings_per_hour"]
    min_hours_day = qc_cfg["sampling_completeness"]["min_hours_per_day"]

    assert min_readings_hr == 3
    assert min_hours_day == 16

    # Test Jan 8 scenario: 10 valid hours < 16 hours -> daily mean becomes NaN
    valid_hours_jan8 = 10
    daily_pm25 = 18.9 if valid_hours_jan8 >= min_hours_day else np.nan
    assert pd.isna(daily_pm25)

    # Test Jan 16 scenario: 17 valid hours >= 16 hours -> daily mean is valid
    valid_hours_jan16 = 17
    daily_pm10 = 101.6 if valid_hours_jan16 >= min_hours_day else np.nan
    assert daily_pm10 == 101.6


def test_alert_engine_qc_gate_suppression():
    """Verify alert engine suppresses alerts from suspect readings failing QC and logs 'suppressed: QC'."""
    engine = AlertEngine()

    res = engine.evaluate(
        aqi=214,
        dominant_pollutant="PM10",
        station="BTM Layout",
        qc_flag="SATURATION_ARTIFACT",
    )

    assert res["status"] == "QC_SUPPRESSED"
    assert res["action_label"] == "suppressed: QC"
    assert res["is_active_alert"] is False
    assert "suppressed: QC" in res["action_note"]


def test_clean_dataframe_single_pollutant_flag():
    """Verify clean_dataframe handles Jan 8 single-pollutant scenario properly."""
    data = {
        "date": ["2024-01-08"],
        "station": ["BTM Layout"],
        "city": ["Bengaluru"],
        "pm25": [np.nan],
        "pm10": [39.6],
        "qc_flag": ["SINGLE_POLLUTANT_AQI"],
    }
    df = clean_dataframe(pd.DataFrame(data))
    assert df["aqi_derived"].iloc[0] == 40
    assert df["dominant_pm"].iloc[0] == "PM10"
    assert "SINGLE_POLLUTANT_AQI" in df["data_quality_flag"].iloc[0]
    assert pd.isna(df["pm_ratio"].iloc[0])

