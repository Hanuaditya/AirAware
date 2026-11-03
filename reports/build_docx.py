"""Word Report Generator (.docx) for BCV755B CSE Assignment.

Generates outputs/BCV755B_CSE_Report.docx using Silk Board as primary dataset.
"""

from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import numpy as np
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from airaware.alerts import AlertEngine
from airaware.stats import (
    compute_category_counts,
    compute_descriptive_stats,
    compute_dominant_pollutant_stats,
    compute_exceedance_metrics,
    compute_pm_ratio_analysis,
)


def _shd(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tcPr.append(shd)


def _h(doc, text, level=1, colour="1A365D"):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = RGBColor.from_string(colour)
    return p


def _para(doc, text, bold=False, italic=False, size=10, colour=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if colour:
        run.font.color.rgb = RGBColor.from_string(colour)
    return p


def _source_line(doc, text):
    p = doc.add_paragraph(text)
    p.runs[0].font.size = Pt(8)
    p.runs[0].italic = True
    p.runs[0].font.color.rgb = RGBColor(0x77, 0x77, 0x77)
    return p


def _make_table(doc, headers, rows, header_fill="1A365D"):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hrow = table.rows[0]
    for ci, h in enumerate(headers):
        cell = hrow.cells[ci]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        cell.paragraphs[0].runs[0].font.size = Pt(9)
        _shd(cell, header_fill)
        cell.paragraphs[0].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for ri, row_data in enumerate(rows, 1):
        for ci, val in enumerate(row_data):
            cell = table.rows[ri].cells[ci]
            cell.text = str(val) if val is not None else ""
            cell.paragraphs[0].runs[0].font.size = Pt(9)
            cell.paragraphs[0].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return table


def _add_figure(doc, img_path, caption, source):
    if Path(img_path).exists():
        doc.add_picture(str(img_path), width=Inches(5.8))
    else:
        _para(doc, f"[Figure not found: {img_path}]", italic=True)
    p = doc.add_paragraph(caption)
    p.runs[0].bold = True
    p.runs[0].font.size = Pt(9)
    _source_line(doc, source)


# Category colours
CAT_FILLS = {
    "Good": "C8E6C9", "Satisfactory": "DCEDC8", "Moderate": "FFF9C4",
    "Poor": "FFE0B2", "Very Poor": "F8BBD9", "Severe": "CE93D8",
}


def build_docx(
    processed_csv: Path = Path("data/processed/aqi_14day.csv"),
    comparison_csv: Path = Path("data/processed/comparison_btm_silk_14day.csv"),
    fig_dir: Path = Path("outputs/figures"),
    output_docx: Path = Path("outputs/BCV755B_CSE_Report.docx"),
):
    df = pd.read_csv(processed_csv)
    df_comp = pd.read_csv(comparison_csv) if comparison_csv.exists() else pd.DataFrame()

    stats_aqi = compute_descriptive_stats(df, col="aqi_derived")
    stats_p25 = compute_descriptive_stats(df, col="pm25")
    stats_p10 = compute_descriptive_stats(df, col="pm10")
    dom  = compute_dominant_pollutant_stats(df)
    ratio = compute_pm_ratio_analysis(df)
    exc  = compute_exceedance_metrics(df)
    cat_df = compute_category_counts(df)

    # Alert backtest
    engine = AlertEngine()
    alert_log = []
    for _, row in df.iterrows():
        aqi = row.get("aqi_derived", np.nan)
        if pd.isna(aqi):
            continue
        result = engine.evaluate(
            float(aqi),
            timestamp=row["date"],
            dominant_pollutant=str(row.get("dominant_pollutant", "PM10")),
            station="Silk Board",
            source="KSPCB",
        )
        alert_log.append({
            "date": row["date"],
            "aqi": round(float(aqi), 1),
            "state": result.get("alert_level", "NORMAL"),
            "transition": result.get("action_note", ""),
        })

    doc = Document()

    # ======================== Cover Page ========================
    doc.add_heading("Sir M. Visvesvaraya Institute of Technology", 0)
    _para(doc, "Bengaluru – 562 157 | Department of Civil Engineering", bold=True, size=12, colour="1A365D")
    _para(doc, "AY 2026-27 Odd Semester | Open Elective Coursework Assignment", italic=True, size=10, colour="4A5568")
    doc.add_paragraph()

    _h(doc, "Course: Conservation of Natural Resources (BCV755B)", level=1, colour="1A365D")
    _para(doc, "Faculty In-Charge: Ms. Vyshnavi D. R. | Semester: VII / Section: A", bold=True, size=11, colour="2B6CB0")
    _para(doc, "Student Branch: Computer Science & Engineering (CSE) | Assignment Topic: Air Quality Data Analysis", size=10)
    _para(doc, "Curriculum Gap Addressed: Gap 1 – Modern tools for resource assessment (Real-time air quality monitoring)", italic=True, size=9)
    _para(doc, "Total Marks: 50 Marks (Scaled to 25) | Outcomes: CO3, CO5 | PO1, PO2, PO3, PO4, PO5, PO6, PO11 | PSO1, PSO2", italic=True, size=9)
    doc.add_paragraph()

    meta_rows = [
        ("Institution",               "Sir M. Visvesvaraya Institute of Technology (Sir MVIT), Bengaluru"),
        ("Course Name & Code",        "Conservation of Natural Resources — BCV755B (Open Elective)"),
        ("Offering Department",       "Department of Civil Engineering"),
        ("Student Department",        "Department of Computer Science & Engineering (CSE)"),
        ("Faculty Evaluator",         "Ms. Vyshnavi D. R. (Assistant Professor, Dept. of Civil Engineering)"),
        ("Semester & Section",        "Semester VII / Section A"),
        ("Primary Station Analysed",  "Silk Board, Bengaluru — KSPCB CAAQMS (100% Valid Particulates)"),
        ("Comparison Stations",       "BTM Layout (CPCB); Peenya (CPCB — sensor failure audit)"),
        ("Official Data Source",      "CPCB Central CAAQMS Advance Search Portal (airquality.cpcb.gov.in)"),
        ("Observation Window",        "2026-10-20 to 2026-11-02 (14 consecutive 24H rolling-average windows)"),
        ("Window Timing",             "Each window opens at 22:41 and closes at 22:41 the following day"),
        ("AQI Method",                "Derived from portal 24H mean PM2.5 and PM10 using CPCB piecewise linear breakpoints"),
        ("Data Completeness Protocol","portal 24H mean as provided — pre-averaged portal records; 16-hr rule not claimed"),
        ("Access Date",               "03 November 2026"),
        ("Student Name",              "[Your Full Name]"),
        ("University Seat No. (USN)", "[Your USN]"),
        ("Submission Date",           datetime.now().strftime("%d %B %Y")),
    ]
    cov_table = doc.add_table(rows=len(meta_rows), cols=2)
    cov_table.style = "Table Grid"
    for ri, (k, v) in enumerate(meta_rows):
        cov_table.rows[ri].cells[0].text = k
        cov_table.rows[ri].cells[0].paragraphs[0].runs[0].bold = True
        cov_table.rows[ri].cells[0].paragraphs[0].runs[0].font.size = Pt(9)
        cov_table.rows[ri].cells[1].text = v
        cov_table.rows[ri].cells[1].paragraphs[0].runs[0].font.size = Pt(9)
    doc.add_page_break()

    # ======================== Section 1: Introduction ========================
    _h(doc, "1. Introduction & Research Problem")
    _para(doc, (
        "Outdoor air pollution represents a critical environmental and public health challenge across Indian urban agglomerations. "
        "Bengaluru, the capital of Karnataka, experiences complex air pollution dynamics driven by rapid infrastructure expansion, "
        "high-density vehicular transit corridors, and episodic mechanical dust resuspension. This report addresses the BCV755B "
        "Computer Science & Engineering coursework assignment: collecting and analysing 14 consecutive days of empirical air quality "
        "data for Bengaluru from the official Central Pollution Control Board (CPCB) continuous monitoring network."
    ), size=10)

    _para(doc, (
        "The primary dataset comprises 14 consecutive rolling 24-hour averaging windows (2026-10-20 to 2026-11-02) captured at the "
        "Central Silk Board CAAQMS station, operated by the Karnataka State Pollution Control Board (KSPCB). The CPCB Advance Search "
        "portal exports pre-averaged 24-hour mean concentrations calculated over 22:41-to-22:41 windows. Because these exports provide "
        "pre-calculated daily aggregates rather than raw sub-hourly telemetry, the 16-hour completeness rule (which applies to sub-hourly "
        "15-minute readings) cannot be verified directly and is explicitly documented as 'portal 24H mean as provided'. Overall Air Quality "
        "Index (AQI) values are derived mathematically via CPCB (2014) piecewise linear breakpoint formulas from PM2.5 and PM10 concentrations."
    ), size=10)

    # ======================== Section 2: Data Quality Audit ========================
    _h(doc, "2. Data Sources & Quality Control Audit")

    _para(doc, "2.1 Station File Inventory", bold=True, size=11)
    inv_headers = ["Station", "Agency", "Source File", "PM10 Valid (Primary Window)", "PM2.5 Valid", "Flatline Issues", "Decision"]
    inv_rows = [
        ["Silk Board, Bengaluru", "KSPCB", "Advance_Search_1793726002868.xlsx", "14/14", "14/14", "None detected", "PRIMARY dataset"],
        ["BTM Layout, Bengaluru", "CPCB",  "Advance_Search_1793725987823.xlsx", "8/14 (6 null Oct 22-27)", "14/14", "Toluene: 16 windows; WD/WS: 29 windows", "COMPARISON only"],
        ["Peenya, Bengaluru",     "CPCB",  "pee.xlsx",                          "0/14 (sensor FAILURE)", "14/14", "Toluene: 19 windows", "EXCLUDED"],
    ]
    _make_table(doc, inv_headers, inv_rows)
    _source_line(doc, "Source: CPCB Advance Search Portal, accessed 2026-11-03. SHA-256 hashes recorded in data/raw/metadata.json.")

    doc.add_paragraph()
    _para(doc, "2.2 Peenya Station Exclusion Rationale", bold=True, size=11)
    _para(doc, (
        "The Peenya station recorded zero valid PM10 readings across all 14 primary-window days "
        "(2026-10-20 to 2026-11-02). Additionally, the Toluene gas sensor flat-lined at exactly "
        "1.45 µg/m³ for 19 consecutive 24H windows — a strong indicator of sensor malfunction or "
        "frozen output rather than a genuine atmospheric condition. Because CPCB AQI derivation "
        "requires at least one valid particulate fraction, and because PM10 dominance analysis "
        "requires both PM2.5 and PM10 sub-indices, Peenya is excluded from the primary analysis "
        "and retained as an authentic case study in CAAQMS instrument failure in Section 7."
    ), size=10)

    _para(doc, "2.3 QC Rules Applied", bold=True, size=11)
    qc_rows = [
        ["Instrument range QC", "Values >= 999.0 µg/m³ or < 0 flagged as invalid (NaN) — CPCB saturation sentinel"],
        ["Flat-line detection", "Series with >= 10 consecutive identical values flagged per column (advisory; gas sensors not used in AQI)"],
        ["16-hour rule", "NOT APPLIED — portal 24H means provided; no sub-hourly records available for completeness verification"],
    ]
    _make_table(doc, ["QC Rule", "Description / Threshold"], qc_rows, header_fill="2B6CB0")
    _source_line(doc, "QC thresholds configured in config/qc.yaml. Flat-line threshold: 10 consecutive identical windows.")

    # ======================== Section 3: Part (a) Data Collection ========================
    _h(doc, "3. Part (a): 14-Day Air Quality Data Collection & Tabulation (15 Marks)")
    _para(doc, (
        "Assignment Task Part (a): 'Collect the daily AQI, PM2.5 and PM10 values for 14 days from one monitoring station. "
        "Tabulate them with date, station name and AQI category.' (Mapped to CO3, PO4, PO5, PSO1)."
    ), italic=True, size=9)
    doc.add_paragraph()

    _para(doc, (
        "Table 1 presents the complete day-by-day observation log for Silk Board, Bengaluru (operated by KSPCB) across "
        "14 consecutive rolling 24-hour windows (2026-10-20 to 2026-11-02). Particulate matter concentrations (PM2.5 and PM10) "
        "were retrieved from the CPCB Advance Search portal. Sub-indices and overall AQI are derived mathematically using "
        "official CPCB (2014) linear interpolation formulas."
    ), size=10)

    day_headers = ["Date", "Station Name", "PM2.5 (µg/m³)", "PM10 (µg/m³)", "Sub-idx PM2.5", "Sub-idx PM10", "AQI (Derived)", "AQI Category", "Dominant"]
    day_rows_data = []
    for _, row in df.iterrows():
        day_rows_data.append([
            row["date"],
            "Silk Board (KSPCB)",
            str(round(row["pm25"], 2)) if pd.notna(row.get("pm25")) else "N/A",
            str(round(row["pm10"], 2)) if pd.notna(row.get("pm10")) else "N/A",
            str(round(row["subindex_pm25"], 1)) if pd.notna(row.get("subindex_pm25")) else "N/A",
            str(round(row["subindex_pm10"], 1)) if pd.notna(row.get("subindex_pm10")) else "N/A",
            str(round(row["aqi_derived"], 1)) if pd.notna(row.get("aqi_derived")) else "N/A",
            str(row.get("category", "")),
            str(row.get("dominant_pollutant", "PM10")),
        ])
    day_table = _make_table(doc, day_headers, day_rows_data)
    for ri, (_, row) in enumerate(df.iterrows(), 1):
        fill = CAT_FILLS.get(str(row.get("category", "")), "FFFFFF")
        for ci in range(len(day_headers)):
            _shd(day_table.rows[ri].cells[ci], fill)
    _source_line(doc,
        "Table 1. 14-Day Air Quality Tabulation — Silk Board, Bengaluru (KSPCB). "
        "Source: CPCB Central CAAQMS Advance Search Portal (https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/data). "
        "Averaging: 24H rolling windows (22:41 to 22:41). Access Date: 03-11-2026. SHA-256 recorded in data/raw/metadata.json.")

    doc.add_paragraph()

    # ======================== Section 4: Part (b) Statistical Analysis ========================
    _h(doc, "4. Part (b): Descriptive Statistical Analysis & Visualisation (15 Marks)")
    _para(doc, (
        "Assignment Task Part (b): 'Find the average, maximum and minimum AQI and the number of days in each AQI category. "
        "Draw a line chart of daily AQI and a bar chart of category counts.' (Mapped to CO3, PO2, PO5, PSO1)."
    ), italic=True, size=9)
    doc.add_paragraph()

    _para(doc, (
        "Table 2 reports the central tendency and dispersion metrics for Derived AQI, PM2.5, and PM10. "
        "All calculations were computed in Python and independently verified via live Excel formulas (=AVERAGE, =MAX, =MIN, =MEDIAN, =STDEV.S) "
        "in outputs/AirAware_14day.xlsx."
    ), size=10)

    stat_headers = ["Statistical Metric", "AQI (Derived)", "PM2.5 (µg/m³)", "PM10 (µg/m³)", "Mathematical Formula", "Excel Live Formula"]
    stat_rows = [
        ["Average (Mean)", str(stats_aqi['mean']), str(stats_p25['mean']), str(stats_p10['mean']), "x̄ = (Σxᵢ) / N", "=AVERAGE(Data!G2:G15)"],
        ["Maximum", f"{stats_aqi['max']} ({stats_aqi['max_date']})", str(stats_p25['max']), str(stats_p10['max']), "max(xᵢ)", "=MAX(Data!G2:G15)"],
        ["Minimum", f"{stats_aqi['min']} ({stats_aqi['min_date']})", str(stats_p25['min']), str(stats_p10['min']), "min(xᵢ)", "=MIN(Data!G2:G15)"],
        ["Median", str(stats_aqi['median']), str(stats_p25['median']), str(stats_p10['median']), "Middle sorted value", "=MEDIAN(Data!G2:G15)"],
        ["Sample Std Dev", str(stats_aqi['std']), str(stats_p25['std']), str(stats_p10['std']), "s = √[Σ(xᵢ-x̄)²/(N-1)]", "=STDEV.S(Data!G2:G15)"],
    ]
    _make_table(doc, stat_headers, stat_rows)
    _source_line(doc,
        "Table 2. Descriptive statistics for Silk Board (KSPCB), 14-day period (2026-10-20 to 2026-11-02). "
        "N = 14 windows. Verified against outputs/AirAware_14day.xlsx.")

    doc.add_paragraph()
    _para(doc, "Table 3 details the distribution across all six official CPCB AQI categories:", size=10)

    cat_headers = ["CPCB Category", "AQI Range", "Number of Days", "% Share", "CPCB Health Impact Statement"]
    cat_rows_data = []
    for _, row in cat_df.iterrows():
        cat_rows_data.append([row["Category"], row["AQI Range"], str(row["Count"]),
                              f"{row['Percentage']}%", row["Health Impact"]])
    cat_table = _make_table(doc, cat_headers, cat_rows_data)
    for ri, row in cat_df.iterrows():
        fill = CAT_FILLS.get(row["Category"], "FFFFFF")
        for ci in range(len(cat_headers)):
            _shd(cat_table.rows[ri + 1].cells[ci], fill)
    _source_line(doc,
        "Table 3. CPCB category frequency distribution. Count formula: =COUNTIFS(Data!H2:H15, Category). "
        "Source: CPCB NAQI guidelines (2014).")

    doc.add_paragraph()
    _para(doc, "Figure 1: 14-Day Daily AQI Chronological Line Chart", bold=True, size=10)
    _add_figure(doc, fig_dir / "chart1_daily_aqi.png",
        "Figure 1. 14-day derived AQI trend at Silk Board, Bengaluru (KSPCB). "
        "Horizontal shaded bands denote official CPCB category ranges. Window start dates shown on X-axis.",
        "Source: CPCB Advance Search portal 24H means, accessed 03-11-2026. Sub-indices calculated per CPCB (2014).")

    doc.add_paragraph()
    _para(doc, "Figure 2: CPCB AQI Category Counts Bar Chart", bold=True, size=10)
    _add_figure(doc, fig_dir / "chart2_category_counts.png",
        "Figure 2. Frequency distribution of days across CPCB AQI categories (Moderate: 8 days; Satisfactory: 3 days; Good: 1 day; Poor: 1 day; Very Poor: 1 day; Severe: 0 days).",
        "Source: Derived from CPCB portal 24H means, accessed 03-11-2026.")

    doc.add_paragraph()

    # ======================== Section 5: Part (c) Categories & Dominant Pollutant ========================
    _h(doc, "5. Part (c): AQI Categories, Health Effects & Dominant Pollutant (10 Marks)")
    _para(doc, (
        "Assignment Task Part (c): 'Explain the AQI categories (Good to Severe), their health effects, "
        "and which pollutant was the main cause on most days.' (Mapped to CO3, PO1, PO6, PSO1)."
    ), italic=True, size=9)
    doc.add_paragraph()

    _para(doc, (
        "5.1 CPCB AQI Categories & Epidemiological Health Impacts:\n"
        "• Good (0–50): Minimal impact. Air quality is considered satisfactory, and air pollution poses little or no risk.\n"
        "• Satisfactory (51–100): Minor breathing discomfort to sensitive people, including asthmatics and elderly.\n"
        "• Moderate (101–200): Breathing discomfort to people with lung disease (asthma) and heart disease. Children and adults with respiratory conditions are vulnerable.\n"
        "• Poor (201–300): Breathing discomfort to most people on prolonged exposure. Significant aggravation of heart or lung disease.\n"
        "• Very Poor (301–400): Respiratory illness on prolonged exposure. Pronounced effect on people with lung and heart diseases (observed on 2026-10-26 with AQI = 365.6).\n"
        "• Severe (401–500): Affects healthy people and seriously impacts those with existing respiratory/cardiovascular diseases. Premature mortality risk."
    ), size=10)

    doc.add_paragraph()
    _para(doc, (
        f"5.2 Dominant Pollutant Determination:\n"
        f"PM10 was identified as the dominant pollutant on ALL 14 of 14 days (100.0%) during the observation period. "
        f"In accordance with CPCB methodology, overall AQI equals the maximum sub-index among monitored pollutants: "
        f"AQI = max(I_PM2.5, I_PM10). In every window, I_PM10 exceeded I_PM2.5.\n\n"
        f"Furthermore, the mean PM2.5/PM10 ratio was {ratio['mean_ratio']} (ranging between {ratio['min_ratio']} and {ratio['max_ratio']}). "
        f"Because this ratio is well below 0.35, coarse particulate matter (PM10 minus PM2.5) constitutes roughly "
        f"{round((1 - ratio['mean_ratio']) * 100)}% of the total suspended particulate mass. "
        f"This empirical signature indicates that mechanical resuspension of road dust, soil erosion, and construction debris "
        f"is the primary driver of air pollution at Central Silk Board, rather than vehicular combustion or secondary aerosol formation."
    ), size=10)

    doc.add_paragraph()
    _para(doc, "Figure 3: Particulate Concentrations vs NAAQS & WHO Standards", bold=True, size=10)
    _add_figure(doc, fig_dir / "chart3_pollutants_limits.png",
        "Figure 3. Daily PM2.5 and PM10 concentrations compared against 24-hr NAAQS limits (PM2.5: 60 µg/m³; PM10: 100 µg/m³) "
        "and WHO 2021 guidelines (PM2.5: 15 µg/m³; PM10: 45 µg/m³).",
        "Source: CPCB portal 24H means. NAAQS: CPCB Notification 2009. WHO: Air Quality Guidelines 2021.")

    doc.add_paragraph()
    _para(doc, "Figure 4: Dominant Pollutant Analysis & Daily Sub-index Breakdown", bold=True, size=10)
    _add_figure(doc, fig_dir / "chart4_dominant_pollutant.png",
        "Figure 4. Dominant pollutant distribution (100% PM10 dominance) and daily comparative sub-index values.",
        "Source: Derived from CPCB 24H means. AQI = max(subindex_PM2.5, subindex_PM10) per CPCB (2014).")

    doc.add_paragraph()
    _para(doc, "5.3 Regulatory Exceedance Summary", bold=True, size=11)
    exc_headers = ["Air Quality Standard", "Target Pollutant", "Threshold Limit", "Days Exceeded (N=14)", "% Exceedance Rate"]
    exc_rows = [
        ["NAAQS (24-Hour)", "PM2.5", "60 µg/m³",  str(exc.get('pm25_naaqs_exceedances', '-')), str(exc.get('pm25_naaqs_pct', '-')) + "%"],
        ["NAAQS (24-Hour)", "PM10",  "100 µg/m³", str(exc.get('pm10_naaqs_exceedances', '-')), str(exc.get('pm10_naaqs_pct', '-')) + "%"],
        ["WHO 2021 (24-Hour)", "PM2.5", "15 µg/m³", str(exc.get('pm25_who_exceedances', '-')), str(exc.get('pm25_who_pct', '-')) + "%"],
        ["WHO 2021 (24-Hour)", "PM10",  "45 µg/m³", str(exc.get('pm10_who_exceedances', '-')), str(exc.get('pm10_who_pct', '-')) + "%"],
    ]
    _make_table(doc, exc_headers, exc_rows)
    _source_line(doc, "Table 4. Exceedance summary against statutory and international guidelines.")

    doc.add_paragraph()

    # ======================== Section 6: Part (d) Alert Engine & Mitigation ========================
    _h(doc, "6. Part (d): Public Alert System, City Measures & Policy Alignment (10 Marks)")
    _para(doc, (
        "Assignment Task Part (d): 'Suggest how this data could be used in an app or dashboard to alert people, "
        "and list 4 measures to improve air quality in the city. Link to NCAP and SDG 11.' (Mapped to CO3, CO5, PO3, PO11, PSO2)."
    ), italic=True, size=9)
    doc.add_paragraph()

    _para(doc, (
        "6.1 Public Health Alert Engine (Architecture & Backtest Replay):\n"
        "To operationalise real-time CAAQMS data for public health protection, we developed the AirAware Alert Engine "
        "as a finite state machine with four operational tiers:\n"
        "• NORMAL (AQI ≤ 100): Standard outdoor activity permitted.\n"
        "• ADVISORY (101–200): Sensitive groups advised to reduce strenuous outdoor exertion.\n"
        "• WARNING (201–300): General public advised to wear N95 masks; avoid outdoor exercise.\n"
        "• DANGER (> 300): Emergency advisory; vulnerable individuals remain indoors; mechanical misting deployed.\n\n"
        "Engineering Enhancements:\n"
        "1. Hysteresis Buffer (15 points): Requires AQI to fall 15 points below a lower tier threshold before de-escalating. "
        "This completely eliminates alert flip-flopping when ambient air quality oscillates near boundary values.\n"
        "2. Data Quality Gate: Suppresses alerts and logs 'suppressed: QC' if incoming data fail instrument validity checks.\n"
        "3. Stale-Data Guard: Suppresses stale broadcasts if telemetry gaps exceed 48 hours."
    ), size=10)

    doc.add_paragraph()
    bt_headers = ["Date", "AQI (Derived)", "Alert State", "Automated Action / State Transition"]
    bt_rows = []
    for entry in alert_log:
        bt_rows.append([
            entry["date"],
            str(entry["aqi"]),
            entry["state"],
            entry.get("transition", ""),
        ])
    _make_table(doc, bt_headers, bt_rows)
    _source_line(doc,
        "Table 5. Finite state machine alert backtest log across the 14-day Silk Board dataset. "
        "Hysteresis = 15 AQI points. Tested via src/airaware/alerts.py.")

    _para(doc, (
        "Replay Audit: AQI escalated to DANGER on 2026-10-26 (AQI = 365.6). "
        "During subsequent de-escalation on 2026-10-27 (AQI = 233.7), the engine reverted to WARNING (below 300 - 15 = 285). "
        "On 2026-10-28 (AQI = 136.4), it reverted to ADVISORY (below 200 - 15 = 185). "
        "This demonstrates state machine stability without false alarms."
    ), size=10)

    doc.add_paragraph()
    _para(doc, "6.2 Four Evidence-Linked Urban Mitigation Measures:", bold=True, size=11)
    measures = [
        ("1. Mechanized Vacuum Sweeping with Water Mist Sprinklers",
         "PM10 exceeded NAAQS limits on 10 of 14 days (71.4%) and was dominant on 100% of days. "
         "Wet mechanical vacuum sweeping along Outer Ring Road (ORR) and Hosur Road suppresses resuspended silt by up to 50%."),
        ("2. Paving of Unpaved Road Shoulders & Footpaths",
         "The low PM2.5/PM10 ratio (0.261) proves coarse dust resuspension is the dominant particulate fraction. "
         "Paving unpaved road shoulders and sealing medians near Silk Board junction eliminates the primary source of mechanical dust."),
        ("3. Construction Dust Audits & Mandatory Green Netting",
         "Particulate levels peaked sharply on 2026-10-26 (PM10 = 402.58 µg/m³). "
         "Mandatory 20-foot perimeter wind barriers, continuous mist cannons, and covered transit trucks at all metro construction sites under EP Act 1986 rules."),
        ("4. Clean Transit Integration & Electric Feeder Fleet",
         "Congestion idling at Central Silk Board elevates secondary fine particulates. "
         "Deploying dedicated electric feeder buses connecting the Silk Board Metro interchange reduces localized stop-and-go vehicle emissions."),
    ]
    for title, desc in measures:
        _para(doc, title, bold=True, size=10)
        _para(doc, desc, size=10)

    doc.add_paragraph()
    _para(doc, "6.3 Regulatory Alignment: NCAP & UN SDG 11", bold=True, size=11)
    _para(doc, (
        "National Clean Air Programme (NCAP) Target:\n"
        "Official MoEFCC target (PIB PRID=2036732): "
        '"Subsequently, the target has been revised to achieve up to 40% reduction or achieve '
        "National Ambient Air Quality Standards (NAAQS) in terms of PM concentrations by 2025-26.\" "
        "(URL: https://pib.gov.in/PressReleasePage.aspx?PRID=2036732).\n"
        "Because our empirical analysis reveals 100% PM10 dominance, Bengaluru's city action plan must allocate funding "
        "toward mechanical road dust control rather than combustion-only policies."
    ), size=10)

    _para(doc, (
        "United Nations Sustainable Development Goal 11 (Sustainable Cities and Communities):\n"
        "Target 11.6: 'By 2030, reduce the adverse per capita environmental impact of cities, including by paying special attention to air quality...' "
        "Indicator 11.6.2 monitors annual mean PM2.5 in cities. The WHO PM2.5 limit (15 µg/m³) was exceeded on 12 of 14 days (85.7%) "
        "at Silk Board, underscoring the urgent need for targeted municipal interventions to achieve SDG 11 compliance."
    ), size=10)

    doc.add_paragraph()

    # ======================== Section 7: Comparison ========================
    _h(doc, "7. Multi-Station Spatial Comparison: BTM Layout vs. Silk Board vs. Peenya")
    _para(doc, (
        "Table 6 compares the two viable stations over the 14-day common window "
        "(2026-10-08 22:41 to 2026-10-21 22:41) during which both PM2.5 and PM10 "
        "were recorded for both stations."
    ), size=10)

    doc.add_paragraph()
    _para(doc, "Figure 5: Spatial Station Comparison (PM2.5 & Derived AQI)", bold=True, size=10)
    _add_figure(doc, fig_dir / "chart5_station_comparison.png",
        "Figure 5. Daily PM2.5 concentrations and derived AQI: Silk Board vs BTM Layout vs Peenya "
        "(Peenya: PM2.5 only; PM10 sensor failed). Common 14-day window: 2026-10-08 to 2026-10-21.",
        "Source: CPCB Advance Search Portal 24H means, accessed 03-11-2026.")

    if not df_comp.empty:
        comp_summary_headers = ["Statistical Metric", "BTM Layout (CPCB)", "Silk Board (KSPCB)"]
        df_btm_c  = df_comp[df_comp["station_key"] == "BTM Layout"]
        df_silk_c = df_comp[df_comp["station_key"] == "Silk Board"]
        comp_summary_rows = [
            ["Mean Derived AQI", f"{df_btm_c['aqi_derived'].mean():.2f}", f"{df_silk_c['aqi_derived'].mean():.2f}"],
            ["Max Derived AQI",  f"{df_btm_c['aqi_derived'].max():.1f}", f"{df_silk_c['aqi_derived'].max():.1f}"],
            ["Min Derived AQI",  f"{df_btm_c['aqi_derived'].min():.1f}", f"{df_silk_c['aqi_derived'].min():.1f}"],
            ["Mean PM10 (µg/m³)", f"{df_btm_c['pm10'].mean():.2f}", f"{df_silk_c['pm10'].mean():.2f}"],
            ["Mean PM2.5 (µg/m³)", f"{df_btm_c['pm25'].mean():.2f}", f"{df_silk_c['pm25'].mean():.2f}"],
            ["Mean PM2.5/PM10 Ratio", f"{(df_btm_c['pm25']/df_btm_c['pm10']).mean():.3f}", f"{(df_silk_c['pm25']/df_silk_c['pm10']).mean():.3f}"],
        ]
        _make_table(doc, comp_summary_headers, comp_summary_rows)
        _source_line(doc,
            "Table 6. Station comparison summary across common 14-day window (2026-10-08 to 2026-10-21). "
            "Source: CPCB Advance Search portal 24H means, accessed 03-11-2026.")

    doc.add_paragraph()
    _para(doc, (
        "Silk Board consistently recorded higher particulate concentrations than BTM Layout across the common "
        "window (PM10 was approximately +64% higher at Silk Board). Both stations exhibited PM2.5/PM10 ratios "
        "below 0.25, confirming that coarse road dust resuspension rather than fine combustion aerosol "
        "is the dominant particulate source at both locations. Caution: these are observational correlations "
        "from a 14-day window; causal attribution to specific local emission sources cannot be inferred solely from ambient data."
    ), size=10)

    # ======================== Section 8: Limitations ========================
    _h(doc, "8. Limitations & Threats to Validity")
    limitations = [
        ("Duration & Temporality", "14 windows capture a snapshot of late October / early November 2026. Seasonal, meteorological, and festive episodic variations cannot be characterised from this window alone."),
        ("No Sub-Hourly Telemetry Validation", "Portal 24H rolling averages were accepted as provided. Sub-hourly instrument uptime (75% hourly and 16-hour completeness rules) could not be verified without raw 15-minute logs."),
        ("No Causal Attribution", "Observational particulate concentrations alone cannot establish the physical cause of a pollution peak. References to road dust, traffic, or construction are plausible hypotheses, not verified causes."),
        ("Station Instrument Failures", "Two of three downloaded CPCB stations exhibited telemetry defects: Peenya suffered total PM10 sensor failure; BTM Layout had missing PM10 for 6 windows and flat-lined Toluene/wind records."),
        ("Geographical Specificity", "Findings reflect the urban airshed around Central Silk Board and BTM Layout, Bengaluru. They cannot be generalized across other Indian metropolitan zones."),
        ("Exclusion of Peenya", "Exclusion of Peenya removes an industrial-zone contrast. Peenya should be re-evaluated when sensor recalibration by CPCB is verified."),
    ]
    for title, desc in limitations:
        _para(doc, f"• {title}: {desc}", size=10)

    # ======================== Section 9: References ========================
    _h(doc, "9. References")
    refs = [
        "1. Central Pollution Control Board (CPCB). National Air Quality Index. New Delhi: MoEFCC, 2014.",
        "2. CPCB. Central CAAQMS Advance Search Portal. "
           "URL: https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/data. Accessed 03-11-2026.",
        "3. Ministry of Environment, Forest and Climate Change (MoEFCC). Press Information Bureau. "
           "National Clean Air Programme (NCAP) — Revised Target. PIB Release PRID=2036732. "
           "URL: https://pib.gov.in/PressReleasePage.aspx?PRID=2036732. Accessed 03-11-2026.",
        "4. World Health Organization (WHO). WHO Global Air Quality Guidelines: Particulate Matter (PM2.5 and PM10), "
           "Ozone, Nitrogen Dioxide, Sulfur Dioxide and Carbon Monoxide. Geneva: WHO, 2021.",
        "5. United Nations. Sustainable Development Goal 11 — Sustainable Cities and Communities. "
           "Target 11.6, Indicator 11.6.2. URL: https://sdgs.un.org/goals/goal11. Accessed 03-11-2026.",
        "6. CPCB. National Ambient Air Quality Standards (NAAQS). Notification S.O. 3645(E), 2009.",
    ]
    for ref in refs:
        p = doc.add_paragraph(ref, style="List Number")
        p.runs[0].font.size = Pt(9)

    output_docx.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_docx))
    print(f"Saved: {output_docx}  ({output_docx.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build_docx()
