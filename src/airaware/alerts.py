"""Alert Engine with Stale-Data Guard, Hysteresis Stabilization, and QC Quality Gate.

Implements real-time alerting and backtesting logic:
- Upgrades immediately upon exceeding severity boundaries.
- Downgrades only when AQI drops by `hysteresis_points` below the lower boundary.
- Suppresses alerts if data fails QC (e.g. instrument saturation >= 999 µg/m³), logging 'suppressed: QC'.
- Suppresses alerts if data age exceeds `stale_limit_hours`.
"""

from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import yaml
import pandas as pd

from airaware.aqi import get_config_path


def load_alerts_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load alert engine rules and levels from config/alerts.yaml."""
    path = config_path or get_config_path("alerts.yaml")
    if not path.exists():
        raise FileNotFoundError(f"Alerts configuration not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class AlertEngine:
    """Intelligent air quality alert engine with hysteresis and quality gate."""

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        if config_dict is None:
            config_dict = load_alerts_config()
        self.config = config_dict
        self.hysteresis = float(self.config.get("engine", {}).get("hysteresis_points", 10.0))
        self.stale_limit_hours = float(self.config.get("engine", {}).get("stale_limit_hours", 36.0))
        self.levels = sorted(self.config.get("levels", []), key=lambda x: x["severity"])
        self.level_by_name = {lvl["name"]: lvl for lvl in self.levels}

        # Internal state
        self.current_level_name: str = "NORMAL"

    def get_level_for_aqi(self, aqi: float) -> Dict[str, Any]:
        """Find the baseline level corresponding to an AQI value."""
        rounded = round(aqi)
        for lvl in self.levels:
            if lvl["min_aqi"] <= rounded <= lvl["max_aqi"]:
                return lvl
        if rounded > self.levels[-1]["max_aqi"]:
            return self.levels[-1]
        return self.levels[0]

    def evaluate(
        self,
        aqi: Optional[float],
        timestamp: Optional[Union[datetime, date, str]] = None,
        last_reading_time: Optional[Union[datetime, date, str]] = None,
        dominant_pollutant: str = "Unknown",
        station: str = "Unknown",
        source: str = "CPCB",
        qc_flag: str = "VALID",
    ) -> Dict[str, Any]:
        """Evaluate an air quality reading with QC quality gate, stale guard, and hysteresis."""
        # 1. QC Quality Gate: Check for saturation or invalid data
        if "SATURATION" in qc_flag.upper() or "INSUFFICIENT" in qc_flag.upper() or (aqi is not None and aqi >= 500 and "UNFILTERED" in qc_flag.upper()):
            return {
                "status": "QC_SUPPRESSED",
                "alert_level": "NORMAL",
                "severity": 0,
                "color": "gray",
                "action_label": "suppressed: QC",
                "action_note": "Alert suppressed: QC (instrument saturation or invalid reading detected)",
                "flip_flop_avoided": False,
                "is_active_alert": False,
                "message": f"Alert suppressed: QC for station {station} on {timestamp}. Suspect reading flagged.",
                "station": station,
                "dominant_pollutant": dominant_pollutant,
            }

        # 2. Check for missing AQI
        if aqi is None or pd.isna(aqi):
            return {
                "status": "DATA_UNAVAILABLE",
                "alert_level": self.current_level_name,
                "severity": self.level_by_name.get(self.current_level_name, {}).get("severity", 0),
                "action_label": "Data unavailable",
                "action_note": "AQI data unavailable; engine maintaining prior state.",
                "flip_flop_avoided": False,
                "is_active_alert": False,
                "message": f"AQI data unavailable for station {station}. Alert engine maintaining prior state.",
                "station": station,
                "dominant_pollutant": dominant_pollutant,
            }

        # Parse timestamp
        curr_dt = None
        if isinstance(timestamp, datetime):
            curr_dt = timestamp
        elif isinstance(timestamp, date):
            curr_dt = datetime.combine(timestamp, datetime.min.time())
        elif isinstance(timestamp, str):
            try:
                curr_dt = pd.to_datetime(timestamp).to_pydatetime()
            except Exception:
                curr_dt = None

        last_dt = None
        if isinstance(last_reading_time, datetime):
            last_dt = last_reading_time
        elif isinstance(last_reading_time, date):
            last_dt = datetime.combine(last_reading_time, datetime.min.time())
        elif isinstance(last_reading_time, str):
            try:
                last_dt = pd.to_datetime(last_reading_time).to_pydatetime()
            except Exception:
                last_dt = None

        # 3. Stale data guard
        if curr_dt and last_dt:
            age_hours = (curr_dt - last_dt).total_seconds() / 3600.0
            if age_hours > self.stale_limit_hours:
                return {
                    "status": "STALE_DATA_SUPPRESSED",
                    "alert_level": "NORMAL",
                    "severity": 0,
                    "color": "gray",
                    "action_label": "suppressed: Stale Data",
                    "action_note": f"Reading is stale ({round(age_hours, 1)} hrs old > limit of {self.stale_limit_hours} hrs)",
                    "flip_flop_avoided": False,
                    "is_active_alert": False,
                    "message": (
                        f"Alert suppressed: Reading is stale ({round(age_hours, 1)} hrs old > "
                        f"limit of {self.stale_limit_hours} hrs). Instrument verification required."
                    ),
                    "station": station,
                    "dominant_pollutant": dominant_pollutant,
                }

        raw_level_obj = self.get_level_for_aqi(aqi)
        raw_level_name = raw_level_obj["name"]
        raw_severity = raw_level_obj["severity"]

        current_level_obj = self.level_by_name.get(self.current_level_name, self.levels[0])
        current_severity = current_level_obj["severity"]

        final_level_obj = raw_level_obj
        flip_flop_avoided = False
        action_note = "Normal state"

        if raw_severity > current_severity:
            # Immediate upgrade
            final_level_obj = raw_level_obj
            self.current_level_name = final_level_obj["name"]
            action_note = f"Upgraded to {self.current_level_name} immediately"

        elif raw_severity < current_severity:
            # Potential downgrade: test hysteresis
            current_min_aqi = current_level_obj["min_aqi"]
            downgrade_threshold = current_min_aqi - self.hysteresis

            if aqi >= downgrade_threshold:
                final_level_obj = current_level_obj
                flip_flop_avoided = True
                action_note = (
                    f"Maintained {self.current_level_name} (AQI {aqi} >= threshold {downgrade_threshold}; "
                    f"hysteresis prevented downgrade to {raw_level_name})"
                )
            else:
                final_level_obj = raw_level_obj
                self.current_level_name = final_level_obj["name"]
                action_note = f"Downgraded to {self.current_level_name} (AQI fell below {downgrade_threshold})"

        is_active = final_level_obj["severity"] >= 2

        msg = (
            f"[{final_level_obj['name']}] AQI: {round(aqi)} at {station}. "
            f"Prominent: {dominant_pollutant}. {final_level_obj['description']} (Source: {source})"
        )

        return {
            "status": "EVALUATED",
            "aqi": round(aqi, 1),
            "alert_level": final_level_obj["name"],
            "severity": final_level_obj["severity"],
            "color": final_level_obj.get("badge", "blue"),
            "action_label": final_level_obj.get("action_label", ""),
            "action_note": action_note,
            "flip_flop_avoided": flip_flop_avoided,
            "is_active_alert": is_active,
            "message": msg,
            "station": station,
            "dominant_pollutant": dominant_pollutant,
            "source": source,
        }

    def replay(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Replay a chronological dataset through the alert engine to evaluate backtest performance."""
        self.current_level_name = "NORMAL"

        logs: List[Dict[str, Any]] = []
        total_flip_flops_avoided = 0
        total_active_alerts = 0
        days_with_alert = 0
        qc_suppressions = 0

        df_sorted = df.sort_values(by="date").reset_index(drop=True)

        aqi_col = "aqi_derived" if "aqi_derived" in df_sorted.columns else "aqi_reported"

        for _, row in df_sorted.iterrows():
            current_date = row["date"]
            aqi_val = row.get(aqi_col)
            dominant = row.get("dominant_pm", row.get("prominent_pollutant", "PM10"))
            station = row.get("station", "BTM Layout, Bengaluru - CPCB")
            source = row.get("source", "CPCB")
            qc_flag = str(row.get("data_quality_flag", row.get("qc_status", "VALID")))

            eval_res = self.evaluate(
                aqi=aqi_val,
                timestamp=current_date,
                last_reading_time=current_date,
                dominant_pollutant=dominant,
                station=station,
                source=source,
                qc_flag=qc_flag,
            )

            if eval_res["status"] == "QC_SUPPRESSED":
                qc_suppressions += 1

            if eval_res["flip_flop_avoided"]:
                total_flip_flops_avoided += 1

            if eval_res["is_active_alert"]:
                total_active_alerts += 1
                days_with_alert += 1

            logs.append({
                "date": str(current_date),
                "aqi": eval_res.get("aqi"),
                "alert_level": eval_res["alert_level"],
                "severity": eval_res.get("severity", 0),
                "action_label": eval_res.get("action_label", ""),
                "action_note": eval_res.get("action_note", ""),
                "flip_flop_avoided": eval_res["flip_flop_avoided"],
                "is_active_alert": eval_res["is_active_alert"],
                "dominant_pollutant": dominant,
                "message": eval_res["message"],
            })

        log_df = pd.DataFrame(logs)

        summary = {
            "total_days_evaluated": len(log_df),
            "days_with_active_alerts": days_with_alert,
            "total_active_alerts_raised": total_active_alerts,
            "flip_flops_prevented_by_hysteresis": total_flip_flops_avoided,
            "qc_suppressions": qc_suppressions,
            "alert_level_distribution": log_df["alert_level"].value_counts().to_dict(),
        }

        return log_df, summary
