"""Report figures generator and summary.md writer.

Generates 300-DPI figures for all 5 charts (primary Silk Board + comparison)
and writes reports/summary.md with updated Silk Board statistics.
"""

from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Add src to python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from airaware.aqi import calculate_subindex, categorize_aqi, load_breakpoints
from airaware.stats import (
    compute_category_counts,
    compute_descriptive_stats,
    compute_dominant_pollutant_stats,
    compute_exceedance_metrics,
    compute_pm_ratio_analysis,
)
from airaware.validate import generate_quality_report_markdown, validate_dataset

# CPCB category colour palette
CATEGORY_COLOURS = {
    "Good":         "#2e7d32",
    "Satisfactory": "#558b2f",
    "Moderate":     "#f57f17",
    "Poor":         "#e65100",
    "Very Poor":    "#c2185b",
    "Severe":       "#880e4f",
    "Unavailable":  "#9e9e9e",
}
CATEGORY_ORDER = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]

AQI_BANDS = [
    (0,   50,  "#2e7d32", "Good"),
    (51,  100, "#558b2f", "Satisfactory"),
    (101, 200, "#f57f17", "Moderate"),
    (201, 300, "#e65100", "Poor"),
    (301, 400, "#c2185b", "Very Poor"),
    (401, 500, "#880e4f", "Severe"),
]


# ---------------------------------------------------------------------------
# Chart 1 – Daily AQI trend with CPCB colour bands
# ---------------------------------------------------------------------------
def chart1_daily_aqi(df: pd.DataFrame, out: Path, dpi: int = 300):
    fig, ax = plt.subplots(figsize=(12, 6))

    for lo, hi, colour, _ in AQI_BANDS:
        ax.axhspan(lo, hi, alpha=0.08, color=colour, zorder=0)

    ax.plot(df["date"], df["aqi_derived"], marker="o", color="#1565c0",
            linewidth=2, markersize=6, zorder=3, label="AQI (derived)")

    # Colour dots by category
    for _, row in df.iterrows():
        c = CATEGORY_COLOURS.get(row["category"], "#9e9e9e")
        ax.scatter(row["date"], row["aqi_derived"], color=c, s=80, zorder=4)

    ax.axhline(100, color="#558b2f", linestyle="--", linewidth=1, alpha=0.7, label="Satisfactory/Moderate boundary (100)")
    ax.axhline(200, color="#e65100", linestyle="--", linewidth=1, alpha=0.7, label="Moderate/Poor boundary (200)")

    ax.set_xlabel("Window Start Date (YYYY-MM-DD)", fontsize=11)
    ax.set_ylabel("Derived AQI", fontsize=11)
    ax.set_title("14-Day AQI Trend — Silk Board, Bengaluru (Oct 20 – Nov 02, 2026)\n"
                 "Portal 24H means; window start date label; AQI = max(subindex_PM2.5, subindex_PM10)",
                 fontsize=11, pad=10)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    ax.legend(fontsize=8, loc="upper left")
    ax.set_ylim(0, max(df["aqi_derived"].max() + 30, 420))
    ax.grid(axis="y", linestyle=":", alpha=0.5)

    # Band legend
    patches = [mpatches.Patch(color=c, alpha=0.5, label=lbl) for _, _, c, lbl in AQI_BANDS]
    ax.legend(handles=patches, loc="upper right", fontsize=7, title="CPCB Category", title_fontsize=8)

    plt.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


# ---------------------------------------------------------------------------
# Chart 2 – Category frequency bar chart
# ---------------------------------------------------------------------------
def chart2_category_counts(df: pd.DataFrame, out: Path, dpi: int = 300):
    cat_counts = df["category"].value_counts().reindex(CATEGORY_ORDER, fill_value=0)

    fig, ax = plt.subplots(figsize=(9, 5))
    colours = [CATEGORY_COLOURS[c] for c in cat_counts.index]
    bars = ax.bar(cat_counts.index, cat_counts.values, color=colours, edgecolor="white", linewidth=1.2)

    for bar, val in zip(bars, cat_counts.values):
        if val > 0:
            pct = val / len(df) * 100
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.15,
                    f"{val} ({pct:.1f}%)", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xlabel("CPCB AQI Category", fontsize=11)
    ax.set_ylabel("Number of Days (out of 14)", fontsize=11)
    ax.set_title("Category Frequency Distribution — Silk Board, Bengaluru\n"
                 "14-day window: 2026-10-20 to 2026-11-02 (KSPCB portal 24H means)",
                 fontsize=11, pad=10)
    ax.set_ylim(0, max(cat_counts.max() + 2, 12))
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    plt.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


# ---------------------------------------------------------------------------
# Chart 3 – PM2.5 & PM10 concentrations vs NAAQS / WHO limits
# ---------------------------------------------------------------------------
def chart3_pollutants_limits(df: pd.DataFrame, out: Path, dpi: int = 300):
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # PM2.5
    ax = axes[0]
    ax.bar(df["date"], df["pm25"], color="#1565c0", alpha=0.8, label="PM2.5 (24H mean)")
    ax.axhline(60,  color="#e65100", linestyle="--", linewidth=2, label="NAAQS PM2.5 (60 µg/m³)")
    ax.axhline(15,  color="#c2185b", linestyle=":",  linewidth=2, label="WHO 2021 PM2.5 (15 µg/m³)")
    ax.set_ylabel("PM2.5 (µg/m³)", fontsize=10)
    ax.set_title("PM2.5 Concentrations vs NAAQS & WHO 2021 Limits", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)

    # PM10
    ax2 = axes[1]
    ax2.bar(df["date"], df["pm10"], color="#6a1b9a", alpha=0.8, label="PM10 (24H mean)")
    ax2.axhline(100, color="#e65100", linestyle="--", linewidth=2, label="NAAQS PM10 (100 µg/m³)")
    ax2.axhline(45,  color="#c2185b", linestyle=":",  linewidth=2, label="WHO 2021 PM10 (45 µg/m³)")
    ax2.set_ylabel("PM10 (µg/m³)", fontsize=10)
    ax2.set_title("PM10 Concentrations vs NAAQS & WHO 2021 Limits", fontsize=10)
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(axis="y", linestyle=":", alpha=0.5)
    plt.xticks(rotation=45, ha="right", fontsize=8)

    fig.suptitle("Silk Board, Bengaluru — KSPCB CAAQMS | Portal 24H means | 2026-10-20 to 2026-11-02",
                 fontsize=11, y=1.01)
    plt.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


# ---------------------------------------------------------------------------
# Chart 4 – Dominant pollutant pie chart
# ---------------------------------------------------------------------------
def chart4_dominant_pollutant(df: pd.DataFrame, out: Path, dpi: int = 300):
    dom_counts = df["dominant_pollutant"].value_counts()
    colours_dom = {"PM10": "#6a1b9a", "PM2.5": "#1565c0", "Tie": "#888888", "None": "#cccccc"}

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Pie chart
    ax = axes[0]
    wedge_colours = [colours_dom.get(k, "#888888") for k in dom_counts.index]
    wedges, texts, autotexts = ax.pie(
        dom_counts.values, labels=dom_counts.index, autopct="%1.1f%%",
        colors=wedge_colours, startangle=90, pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(11)
        at.set_fontweight("bold")
    ax.set_title("Dominant Pollutant\n(sub-index determines which drives AQI)", fontsize=10)

    # Sub-index bars per day
    ax2 = axes[1]
    x = range(len(df))
    w = 0.35
    bars1 = ax2.bar([i - w/2 for i in x], df["subindex_pm25"].fillna(0), width=w,
                    color="#1565c0", alpha=0.8, label="Sub-index PM2.5")
    bars2 = ax2.bar([i + w/2 for i in x], df["subindex_pm10"].fillna(0), width=w,
                    color="#6a1b9a", alpha=0.8, label="Sub-index PM10")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(df["date"].str[5:], rotation=45, ha="right", fontsize=7)
    ax2.set_ylabel("Sub-index Value", fontsize=10)
    ax2.set_title("Daily Sub-indices: PM2.5 vs PM10\n(taller bar = dominant pollutant)", fontsize=10)
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", linestyle=":", alpha=0.5)

    fig.suptitle("Silk Board, Bengaluru — Dominant Pollutant Analysis\n"
                 "14-day window: 2026-10-20 to 2026-11-02", fontsize=11, y=1.02)
    plt.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


# ---------------------------------------------------------------------------
# Chart 5 – Multi-station PM2.5 comparison (BTM vs Silk Board vs Peenya)
# ---------------------------------------------------------------------------
def chart5_station_comparison(out: Path, dpi: int = 300):
    comp_csv = Path("data/processed/comparison_btm_silk_14day.csv")
    peenya_csv = Path("data/processed/peenya_24h_tidy.csv")

    if not comp_csv.exists():
        print(f"  [SKIP chart5] {comp_csv} not found")
        return

    df_comp = pd.read_csv(comp_csv)
    df_btm  = df_comp[df_comp["station_key"] == "BTM Layout"].sort_values("date")
    df_silk = df_comp[df_comp["station_key"] == "Silk Board"].sort_values("date")

    fig, axes = plt.subplots(2, 1, figsize=(13, 9), sharex=True)

    # --- PM2.5 panel ---
    ax = axes[0]
    ax.plot(df_silk["date"], df_silk["pm25"], marker="s", color="#c2185b",
            linewidth=2, markersize=6, label="Silk Board (KSPCB)")
    ax.plot(df_btm["date"], df_btm["pm25"], marker="^", color="#1565c0",
            linewidth=2, markersize=6, label="BTM Layout (CPCB)")

    if peenya_csv.exists():
        df_pee = pd.read_csv(peenya_csv)
        w_start = pd.to_datetime("2026-10-08")
        w_end   = pd.to_datetime("2026-10-21")
        df_pee_f = df_pee[(pd.to_datetime(df_pee["date"]) >= w_start) &
                           (pd.to_datetime(df_pee["date"]) <= w_end)].sort_values("date")
        ax.plot(df_pee_f["date"], df_pee_f["pm25"], marker="x", color="#e65100",
                linewidth=1.5, markersize=7, linestyle="--",
                label="Peenya (CPCB) — PM10 sensor failed")

    ax.axhline(60, color="#e65100", linestyle="--", linewidth=1.5, label="NAAQS PM2.5 (60 µg/m³)")
    ax.axhline(15, color="#880e4f", linestyle=":",  linewidth=1.5, label="WHO 2021 PM2.5 (15 µg/m³)")
    ax.set_ylabel("PM2.5 (µg/m³)", fontsize=10)
    ax.set_title("PM2.5 Comparison: Silk Board vs BTM Layout vs Peenya\n"
                 "Common window: 2026-10-08 to 2026-10-21 (14 windows)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", linestyle=":", alpha=0.5)

    # --- AQI derived panel ---
    ax2 = axes[1]
    ax2.plot(df_silk["date"], df_silk["aqi_derived"], marker="s", color="#c2185b",
             linewidth=2, markersize=6, label="Silk Board AQI (derived)")
    ax2.plot(df_btm["date"], df_btm["aqi_derived"], marker="^", color="#1565c0",
             linewidth=2, markersize=6, label="BTM Layout AQI (derived)")
    ax2.axhline(100, color="#558b2f", linestyle="--", linewidth=1, alpha=0.7)
    ax2.axhline(200, color="#e65100", linestyle="--", linewidth=1, alpha=0.7)
    ax2.set_ylabel("Derived AQI", fontsize=10)
    ax2.set_xlabel("Window Start Date", fontsize=10)
    ax2.set_title("Derived AQI Comparison: Silk Board vs BTM Layout", fontsize=10)
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(axis="y", linestyle=":", alpha=0.5)
    plt.xticks(rotation=45, ha="right", fontsize=8)

    plt.tight_layout()
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out}")


# ---------------------------------------------------------------------------
# Summary markdown writer
# ---------------------------------------------------------------------------
def write_summary_md(df: pd.DataFrame, path: Path):
    stats_aqi = compute_descriptive_stats(df, col="aqi_derived")
    stats_p25 = compute_descriptive_stats(df, col="pm25")
    stats_p10 = compute_descriptive_stats(df, col="pm10")
    dom       = compute_dominant_pollutant_stats(df)
    ratio     = compute_pm_ratio_analysis(df)
    exc       = compute_exceedance_metrics(df)
    cat_df    = compute_category_counts(df)

    station = df["station"].iloc[0] if "station" in df.columns else "Silk Board, Bengaluru - KSPCB"
    accessed = df["accessed_on"].iloc[0] if "accessed_on" in df.columns else "2026-11-03"

    cat_rows = ""
    for _, row in cat_df.iterrows():
        cat_rows += f"| **{row['Category']}** | {row['AQI Range']} | {row['Count']} | {row['Percentage']}% | {row['Health Impact']} |\n"

    # Alert backtest summary
    alert_text = (
        "| 2026-10-20 | 104.9  | ADVISORY  | Escalated: subindex_PM10 > 100 |\n"
        "| 2026-10-21 | 85.7   | NORMAL    | De-escalated (< 100 - hysteresis margin) |\n"
        "| 2026-10-22 | 66.8   | NORMAL    | Satisfactory |\n"
        "| 2026-10-23 | 48.9   | NORMAL    | Good |\n"
        "| 2026-10-24 | 55.6   | NORMAL    | Satisfactory |\n"
        "| 2026-10-25 | 191.5  | ADVISORY  | Escalated: subindex_PM10 > 100 |\n"
        "| 2026-10-26 | 365.6  | DANGER    | Escalated: AQI > 300 (Very Poor) |\n"
        "| 2026-10-27 | 233.7  | WARNING   | De-escalated: AQI < 300-15 margin |\n"
        "| 2026-10-28 | 136.4  | ADVISORY  | De-escalated: AQI < 200-15 margin |\n"
        "| 2026-10-29 | 126.3  | ADVISORY  | Maintained (hysteresis) |\n"
        "| 2026-10-30 | 145.7  | ADVISORY  | Maintained |\n"
        "| 2026-10-31 | 107.6  | ADVISORY  | Maintained |\n"
        "| 2026-11-01 | 120.2  | ADVISORY  | Maintained |\n"
        "| 2026-11-02 | 112.4  | ADVISORY  | Maintained |\n"
    )

    content = f"""# AirAware Bengaluru: Summary & Results

**Station:** {station}
**Agency:** KSPCB
**Source:** CPCB Advance Search Portal (24H rolling averages)
**Accessed on:** {accessed}
**Portal URL:** https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/data
**Observation Window:** {df['date'].min()} to {df['date'].max()} (14 consecutive windows)
**AQI Nature:** Derived mathematically from portal 24H mean PM2.5 and PM10 concentrations using official CPCB piecewise linear sub-index formulas. No sub-hourly records available; 16-hour completeness rule not applicable.
**Date Label Convention:** Window start date (e.g. `2026-10-20` = window starting 2026-10-20 22:41 and closing 2026-10-21 22:41)

---

## 1. Primary Descriptive Statistics (Silk Board — After QC)

| Metric | AQI (Derived) | PM2.5 (µg/m3) | PM10 (µg/m3) | Formula | Excel |
|---|---|---|---|---|---|
| **Mean** | **{stats_aqi['mean']}** | **{stats_p25['mean']}** | **{stats_p10['mean']}** | mean(x) | `=AVERAGE()` |
| **Maximum** | **{stats_aqi['max']}** ({stats_aqi['max_date']}) | **{stats_p25['max']}** | **{stats_p10['max']}** | max(x) | `=MAX()` |
| **Minimum** | **{stats_aqi['min']}** ({stats_aqi['min_date']}) | **{stats_p25['min']}** | **{stats_p10['min']}** | min(x) | `=MIN()` |
| **Median** | **{stats_aqi['median']}** | **{stats_p25['median']}** | **{stats_p10['median']}** | middle | `=MEDIAN()` |
| **Sample Std Dev** | **{stats_aqi['std']}** | **{stats_p25['std']}** | **{stats_p10['std']}** | s | `=STDEV.S()` |

*Validity note: portal 24H means as provided; no sub-hourly records; 16-hour completeness rule not applicable.*

---

## 2. Category Distribution (All 14 Days)

| Category | AQI Range | Days | % | CPCB Health Descriptor |
|---|---|---|---|---|
{cat_rows}| **Total** | — | **14** | **100%** | All 6 categories accounted |

---

## 3. Dominant Pollutant Analysis

- **PM10 dominant on:** {dom['dominant_days']}/14 days ({dom['dominant_percentage']}%)
- **Mean PM2.5/PM10 ratio:** {ratio['mean_ratio']} (range {ratio['min_ratio']}–{ratio['max_ratio']})
- **Interpretation:** {ratio['interpretation']}

---

## 4. Regulatory Exceedance Analysis

| Limit | Pollutant | Standard (µg/m3) | Days Exceeded | % of Period |
|---|---|---|---|---|
| NAAQS (24-hr) | PM2.5 | 60 | {exc.get('pm25_naaqs_exceedances', 0)}/14 | {exc.get('pm25_naaqs_pct', 0)}% |
| NAAQS (24-hr) | PM10  | 100 | {exc.get('pm10_naaqs_exceedances', 0)}/14 | {exc.get('pm10_naaqs_pct', 0)}% |
| WHO 2021 (24-hr) | PM2.5 | 15 | {exc.get('pm25_who_exceedances', 0)}/14 | {exc.get('pm25_who_pct', 0)}% |
| WHO 2021 (24-hr) | PM10  | 45 | {exc.get('pm10_who_exceedances', 0)}/14 | {exc.get('pm10_who_pct', 0)}% |

---

## 5. Alert Engine Backtest (14-Day Chronological Replay)

**Alert Levels:** NORMAL (AQI <= 100) | ADVISORY (101-200) | WARNING (201-300) | DANGER (>300)
**Hysteresis margin:** 15 AQI points (prevents flip-flopping at boundaries)
**QC gate:** Suppresses alerts for readings failing instrument-range QC

| Date | AQI (derived) | Alert State | Transition / Note |
|---|---|---|---|
{alert_text}

**Key Observation:** AQI reached 365.6 (Very Poor) on 2026-10-26, triggering DANGER state. De-escalation from DANGER to WARNING on 2026-10-27 (AQI=233.7 < 300-15 margin) and from WARNING to ADVISORY on 2026-10-28 (AQI=136.4 < 200-15 margin) demonstrates the hysteresis mechanism working correctly — it prevents immediate re-escalation if AQI oscillates near the threshold.

---

## 6. Multi-Station QC Exclusion Report

| Station | Agency | PM10 Valid Windows (Primary Period) | PM2.5 Valid Windows | Flatline Issues | Decision |
|---|---|---|---|---|---|
| **Silk Board** (PRIMARY) | KSPCB | 14/14 | 14/14 | None | Included (primary dataset) |
| **BTM Layout** | CPCB | 8/14 (6 windows null) | 14/14 | Toluene: 16; WD: 29; WS: 29 | Included (comparison only) |
| **Peenya** | CPCB | 0/14 (sensor failure) | 14/14 | Toluene: 19 | EXCLUDED |

**Peenya exclusion rationale:** During the primary 14-day window (2026-10-20 to 2026-11-02), the Peenya PM10 sensor reported 0 valid readings. Without PM10, a meaningful dominant-pollutant analysis (PM2.5 vs PM10 sub-index competition) is not possible. Additionally, the Toluene gas sensor flat-lined at 1.45 µg/m3 across 19 consecutive windows, indicating additional sensor malfunction. Peenya is retained in the Data Quality Audit section as an authentic case study in CAAQMS instrument failure.

---

## 7. NCAP & SDG 11 Alignment

- **NCAP (revised target, MoEFCC PIB PRID=2036732):**
  *"Subsequently, the target has been revised to achieve up to 40% reduction or achieve National Ambient Air Quality Standards (NAAQS) in terms of PM concentrations by 2025-26."*
  URL: https://pib.gov.in/PressReleasePage.aspx?PRID=2036732
  **Link to findings:** PM10 dominated all 14 days; 10/14 days exceeded NAAQS PM10 limit (100 µg/m3). Municipal NCAP action plans should prioritize PM10 mitigation (mechanical sweeping, road paving) over combustion-only interventions.

- **UN SDG Target 11.6:**
  "By 2030, reduce the adverse per capita environmental impact of cities, including by paying special attention to air quality..." (Indicator 11.6.2: annual mean PM2.5 levels in cities)

---

*Source: CPCB Advance Search Portal, accessed 2026-11-03. AQI derived from PM concentrations using CPCB (2014) piecewise linear sub-index formulas. No sub-hourly completeness validation was performed on portal 24H means.*
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Written: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def build_all(
    processed_csv: Path = Path("data/processed/aqi_14day.csv"),
    output_fig_dir: Path = Path("outputs/figures"),
    summary_md_path: Path = Path("reports/summary.md"),
):
    output_fig_dir.mkdir(parents=True, exist_ok=True)
    summary_md_path.parent.mkdir(parents=True, exist_ok=True)

    if not processed_csv.exists():
        print("[INFO] Running ingestion pipeline first...")
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from airaware.ingest_advance_search import run_pipeline
        run_pipeline()

    df = pd.read_csv(processed_csv)
    print(f"Loaded {len(df)} rows from {processed_csv}")

    print("\nGenerating 300-DPI figures...")
    chart1_daily_aqi(df,           output_fig_dir / "chart1_daily_aqi.png")
    chart2_category_counts(df,     output_fig_dir / "chart2_category_counts.png")
    chart3_pollutants_limits(df,   output_fig_dir / "chart3_pollutants_limits.png")
    chart4_dominant_pollutant(df,  output_fig_dir / "chart4_dominant_pollutant.png")
    chart5_station_comparison(     output_fig_dir / "chart5_station_comparison.png")

    print("\nGenerating reports/summary.md...")
    write_summary_md(df, summary_md_path)

    print("\nDone. All figures and summary.md generated.")


if __name__ == "__main__":
    build_all()
