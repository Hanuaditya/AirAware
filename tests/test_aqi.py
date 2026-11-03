"""Unit tests for CPCB AQI sub-index calculations, boundary conditions, and categories."""

import pytest
from airaware.aqi import calculate_subindex, aqi_from_pollutants, categorize_aqi


def test_pm25_boundary_values():
    """Verify PM2.5 concentration boundary transitions across all 6 CPCB brackets."""
    # Good / Satisfactory boundary (30 / 31)
    assert calculate_subindex("pm25", 30.0) == 50.0
    assert calculate_subindex("pm25", 31.0) == 51.0

    # Satisfactory / Moderate boundary (60 / 61)
    assert calculate_subindex("pm25", 60.0) == 100.0
    assert calculate_subindex("pm25", 61.0) == 101.0

    # Moderate / Poor boundary (90 / 91)
    assert calculate_subindex("pm25", 90.0) == 200.0
    assert calculate_subindex("pm25", 91.0) == 201.0

    # Poor / Very Poor boundary (120 / 121)
    assert calculate_subindex("pm25", 120.0) == 300.0
    assert calculate_subindex("pm25", 121.0) == 301.0

    # Very Poor / Severe boundary (250 / 251)
    assert calculate_subindex("pm25", 250.0) == 400.0
    assert calculate_subindex("pm25", 251.0) == 401.0


def test_pm10_boundary_values():
    """Verify PM10 concentration boundary transitions across all 6 CPCB brackets."""
    # Good / Satisfactory boundary (50 / 51)
    assert calculate_subindex("pm10", 50.0) == 50.0
    assert calculate_subindex("pm10", 51.0) == 51.0

    # Satisfactory / Moderate boundary (100 / 101)
    assert calculate_subindex("pm10", 100.0) == 100.0
    assert calculate_subindex("pm10", 101.0) == 101.0

    # Moderate / Poor boundary (250 / 251)
    assert calculate_subindex("pm10", 250.0) == 200.0
    assert calculate_subindex("pm10", 251.0) == 201.0

    # Poor / Very Poor boundary (350 / 351)
    assert calculate_subindex("pm10", 350.0) == 300.0
    assert calculate_subindex("pm10", 351.0) == 301.0

    # Very Poor / Severe boundary (430 / 431)
    assert calculate_subindex("pm10", 430.0) == 400.0
    assert calculate_subindex("pm10", 431.0) == 401.0


def test_max_not_average_rule():
    """Verify that overall AQI is the MAXIMUM sub-index and never an average."""
    # PM2.5 = 75 (Moderate sub-index ~ 148.7), PM10 = 60 (Satisfactory sub-index = 60)
    pollutants = {"pm25": 75.0, "pm10": 60.0}
    overall_aqi, dominant, subindices = aqi_from_pollutants(pollutants)

    sub_pm25 = calculate_subindex("pm25", 75.0)
    sub_pm10 = calculate_subindex("pm10", 60.0)

    # Must equal max(sub_pm25, sub_pm10), which is sub_pm25
    assert overall_aqi == sub_pm25
    assert dominant == "pm25"
    # Verify it is NOT the average
    avg = (sub_pm25 + sub_pm10) / 2.0
    assert overall_aqi != avg


def test_dominant_pollutant_switch():
    """Verify dominant pollutant identifies PM10 when coarse dust dominates."""
    # PM2.5 = 20 (Good sub-index ~ 33.3), PM10 = 150 (Moderate sub-index ~ 133.6)
    pollutants = {"pm25": 20.0, "pm10": 150.0}
    overall_aqi, dominant, _ = aqi_from_pollutants(pollutants)

    assert dominant == "pm10"
    assert overall_aqi > 100


def test_categorize_aqi():
    """Verify CPCB category assignment at exact boundary edges."""
    assert categorize_aqi(0)[0] == "Good"
    assert categorize_aqi(50)[0] == "Good"
    assert categorize_aqi(51)[0] == "Satisfactory"
    assert categorize_aqi(100)[0] == "Satisfactory"
    assert categorize_aqi(101)[0] == "Moderate"
    assert categorize_aqi(200)[0] == "Moderate"
    assert categorize_aqi(201)[0] == "Poor"
    assert categorize_aqi(300)[0] == "Poor"
    assert categorize_aqi(301)[0] == "Very Poor"
    assert categorize_aqi(400)[0] == "Very Poor"
    assert categorize_aqi(401)[0] == "Severe"
    assert categorize_aqi(500)[0] == "Severe"

