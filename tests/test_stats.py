"""Unit tests for statistical computations, formulas, and category distributions."""

import numpy as np
import pandas as pd
import pytest

from airaware.stats import compute_descriptive_stats, compute_category_counts, compute_pm_ratio_analysis


@pytest.fixture
def sample_small_df():
    """Create a deterministic 5-day dataset for hand-verified statistics."""
    data = {
        "date": ["2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"],
        "aqi_reported": [50.0, 100.0, 150.0, 80.0, 120.0],
        "category_derived": ["Good", "Satisfactory", "Moderate", "Satisfactory", "Moderate"],
        "pm25": [28.0, 55.0, 75.0, 48.0, 68.0],
        "pm10": [48.0, 95.0, 130.0, 80.0, 115.0],
        "dominant_pm": ["PM2.5", "PM2.5", "PM2.5", "PM10", "PM2.5"],
    }
    df = pd.DataFrame(data)
    df["pm_ratio"] = df["pm25"] / df["pm10"]
    return df


def test_descriptive_statistics_hand_computed(sample_small_df):
    """Test mean, median, min, max, std match hand-computed values exactly."""
    stats = compute_descriptive_stats(sample_small_df, col="aqi_reported")

    assert stats["n"] == 5
    assert stats["mean"] == 100.0
    assert stats["median"] == 100.0
    assert stats["min"] == 50.0
    assert stats["min_date"] == "2026-11-01"
    assert stats["max"] == 150.0
    assert stats["max_date"] == "2026-11-03"
    # Sample std of [50, 100, 150, 80, 120]: sqrt(5800/4) = 38.08
    assert stats["std"] == 38.08

    # Verify formula keys and Excel equivalents are present
    assert "=AVERAGE" in stats["excel_equivalents"]["mean"]
    assert "=STDEV.S" in stats["excel_equivalents"]["std"]


def test_category_counts_all_six_categories(sample_small_df):
    """Verify that all six official CPCB categories appear in the counts table, including 0s."""
    cat_df = compute_category_counts(sample_small_df, category_col="category_derived")

    assert len(cat_df) == 6
    expected_categories = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    assert cat_df["Category"].tolist() == expected_categories

    count_dict = dict(zip(cat_df["Category"], cat_df["Count"]))
    assert count_dict["Good"] == 1
    assert count_dict["Satisfactory"] == 2
    assert count_dict["Moderate"] == 2
    assert count_dict["Poor"] == 0
    assert count_dict["Very Poor"] == 0
    assert count_dict["Severe"] == 0

    assert sum(cat_df["Count"]) == 5
    assert round(sum(cat_df["Percentage"]), 0) == 100.0


def test_pm_ratio_analysis(sample_small_df):
    """Verify PM2.5 / PM10 ratio computation."""
    res = compute_pm_ratio_analysis(sample_small_df)
    assert 0.5 <= res["mean_ratio"] <= 0.65
    assert "hints at a dominant contribution" in res["interpretation"]

