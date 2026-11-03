"""Unit tests for AlertEngine hysteresis, stale-data suppression, and immediate escalation."""

from datetime import datetime, timedelta
import pandas as pd
import pytest

from airaware.alerts import AlertEngine


def test_immediate_alert_escalation():
    """Verify that worsening air quality causes an immediate upgrade without delay."""
    engine = AlertEngine()

    # Initial satisfactory reading
    r1 = engine.evaluate(aqi=80, dominant_pollutant="PM2.5", station="BTM Layout")
    assert r1["alert_level"] == "INFO"
    assert engine.current_level_name == "INFO"

    # Sudden spike to Poor (220)
    r2 = engine.evaluate(aqi=220, dominant_pollutant="PM2.5", station="BTM Layout")
    assert r2["alert_level"] == "WARNING"
    assert engine.current_level_name == "WARNING"
    assert "Upgraded to WARNING immediately" in r2["action_note"]


def test_hysteresis_prevents_flip_flop():
    """Verify that a slight drop across the boundary does not oscillate the alert level."""
    engine = AlertEngine()
    # Force state to WARNING (201-300 range; lower bound = 201)
    # With hysteresis = 10, downgrade threshold is 201 - 10 = 191.
    engine.evaluate(aqi=215, dominant_pollutant="PM2.5", station="BTM Layout")
    assert engine.current_level_name == "WARNING"

    # Reading drops slightly to 198 (nominally 'ADVISORY' 101-200, but >= 191)
    r_slight_drop = engine.evaluate(aqi=198, dominant_pollutant="PM2.5", station="BTM Layout")
    assert r_slight_drop["alert_level"] == "WARNING"
    assert r_slight_drop["flip_flop_avoided"] is True
    assert engine.current_level_name == "WARNING"

    # Reading drops decisively to 185 (< 191)
    r_decisive_drop = engine.evaluate(aqi=185, dominant_pollutant="PM2.5", station="BTM Layout")
    assert r_decisive_drop["alert_level"] == "ADVISORY"
    assert r_decisive_drop["flip_flop_avoided"] is False
    assert engine.current_level_name == "ADVISORY"


def test_stale_data_guard_suppression():
    """Verify that an outdated reading suppresses alert generation."""
    engine = AlertEngine()
    t_now = datetime(2026, 11, 5, 12, 0, 0)
    # Last reading is 48 hours old (exceeds default 36-hour limit)
    t_stale = t_now - timedelta(hours=48)

    res = engine.evaluate(
        aqi=250,
        timestamp=t_now,
        last_reading_time=t_stale,
        dominant_pollutant="PM2.5",
        station="BTM Layout",
    )

    assert res["status"] == "STALE_DATA_SUPPRESSED"
    assert res["is_active_alert"] is False
    assert "Reading is stale" in res["message"]


def test_replay_backtest_on_dataframe():
    """Verify replay backtest generates valid log and summary."""
    engine = AlertEngine()
    dates = pd.date_range("2026-11-01", periods=5, freq="D").date
    df = pd.DataFrame({
        "date": dates,
        "station": ["BTM Layout"] * 5,
        "aqi_reported": [90.0, 210.0, 198.0, 180.0, 85.0],
        "dominant_pm": ["PM2.5"] * 5,
        "source": ["CPCB"] * 5,
    })

    log_df, summary = engine.replay(df)

    assert len(log_df) == 5
    assert summary["total_days_evaluated"] == 5
    # Day 3 (AQI 198) should have flip-flop avoided
    assert summary["flip_flops_prevented_by_hysteresis"] >= 1

