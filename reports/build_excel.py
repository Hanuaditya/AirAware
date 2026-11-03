"""Excel Generator for AirAware Bengaluru using openpyxl.

Creates outputs/AirAware_14day.xlsx with:
- Sheet 'Data': 14 windows of Silk Board CAAQMS data (KSPCB portal 24H means)
- Sheet 'Stats': Live Excel formulas (AVERAGE, MAX, MIN, MEDIAN, STDEV.S, COUNTIFS)
- Sheet 'Comparison': BTM Layout vs Silk Board comparison over common window
- Sheet 'QC_Audit': Station data quality exclusion report
- Native Excel charts with axis titles
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def _thin_border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)


def _header_style(ws, row, col, text, fill_hex="1A365D"):
    cell = ws.cell(row, col, text)
    cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    cell.fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = _thin_border()
    return cell


def _data_cell(ws, row, col, value):
    cell = ws.cell(row, col, value)
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = _thin_border()
    return cell


def _format_val(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "unavailable"
    return v


# CPCB category fill colours
CATEGORY_FILLS = {
    "Good":         "C8E6C9",
    "Satisfactory": "DCEDC8",
    "Moderate":     "FFF9C4",
    "Poor":         "FFE0B2",
    "Very Poor":    "F8BBD9",
    "Severe":       "CE93D8",
    "Unavailable":  "EEEEEE",
}


def create_excel_workbook(
    processed_csv: Path = Path("data/processed/aqi_14day.csv"),
    comparison_csv: Path = Path("data/processed/comparison_btm_silk_14day.csv"),
    output_excel: Path = Path("outputs/AirAware_14day.xlsx"),
):
    df = pd.read_csv(processed_csv)
    df_comp = pd.read_csv(comparison_csv) if comparison_csv.exists() else pd.DataFrame()

    output_excel.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()

    title_font   = Font(name="Calibri", size=13, bold=True, color="1A365D")
    sub_font     = Font(name="Calibri", size=10, italic=True, color="555555")
    bold_font    = Font(name="Calibri", size=11, bold=True)
    normal_font  = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")

    # ---------------------------------------------------------------
    # Sheet 1: Data
    # ---------------------------------------------------------------
    ws = wb.active
    ws.title = "Data"

    # Title block
    ws.merge_cells("A1:R1")
    t = ws["A1"]
    t.value = "AirAware Bengaluru — Silk Board KSPCB CAAQMS | 14-Day Portal 24H Means"
    t.font = title_font
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 22

    ws.merge_cells("A2:R2")
    s = ws["A2"]
    s.value = (
        "Station: Silk Board, Bengaluru - KSPCB  |  "
        "Window: 2026-10-20 to 2026-11-02  |  "
        "Accessed: 2026-11-03  |  "
        "AQI = max(subindex_PM2.5, subindex_PM10) — portal 24H means; 16-hr rule not applicable"
    )
    s.font = sub_font
    s.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[2].height = 28

    # Column headers
    headers = [
        "Date (Window Start)", "From Date (22:41)", "To Date (22:41)",
        "Station", "Agency",
        "PM2.5 (µg/m³)", "PM10 (µg/m³)",
        "Sub-index PM2.5", "Sub-index PM10",
        "AQI (Derived)", "CPCB Category",
        "Dominant Pollutant", "PM2.5/PM10 Ratio",
        "Exceed NAAQS PM2.5?", "Exceed NAAQS PM10?",
        "Exceed WHO PM2.5?", "Exceed WHO PM10?",
        "Accessed On",
    ]
    col_keys = [
        "date", "from_date_str", "to_date_str", "station", "agency",
        "pm25", "pm10", "subindex_pm25", "subindex_pm10",
        "aqi_derived", "category", "dominant_pollutant", "pm_ratio",
        "exceed_naaqs_pm25", "exceed_naaqs_pm10",
        "exceed_who_pm25", "exceed_who_pm10",
        "accessed_on",
    ]

    for ci, h in enumerate(headers, 1):
        _header_style(ws, 3, ci, h)

    for ri, (_, row) in enumerate(df.iterrows(), 4):
        cat = str(row.get("category", ""))
        fill_hex = CATEGORY_FILLS.get(cat, "FFFFFF")
        cat_fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")

        for ci, key in enumerate(col_keys, 1):
            raw = row.get(key, "")
            val = _format_val(raw) if isinstance(raw, float) and np.isnan(raw) else raw
            # Round floats
            if isinstance(val, float) and key not in ["pm_ratio", "exceed_naaqs_pm25",
                                                        "exceed_naaqs_pm10", "exceed_who_pm25",
                                                        "exceed_who_pm10"]:
                val = round(val, 2)
            elif key == "pm_ratio" and isinstance(val, float):
                val = round(val, 3)
            elif key in ["exceed_naaqs_pm25", "exceed_naaqs_pm10",
                         "exceed_who_pm25", "exceed_who_pm10"]:
                val = "YES" if val else "NO"

            cell = _data_cell(ws, ri, ci, val)
            if key == "category":
                cell.fill = cat_fill
                cell.font = Font(name="Calibri", size=10, bold=True)
            else:
                cell.font = normal_font

    # Column widths
    col_widths = [14, 18, 18, 30, 8, 12, 12, 14, 14, 12, 14, 16, 14, 16, 16, 14, 14, 13]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A4"

    # ---------------------------------------------------------------
    # Sheet 2: Stats (live formulas)
    # ---------------------------------------------------------------
    ws2 = wb.create_sheet("Stats")
    ws2.merge_cells("A1:G1")
    ws2["A1"].value = "AirAware Bengaluru — Descriptive Statistics (Live Excel Formulas)"
    ws2["A1"].font = title_font
    ws2["A1"].alignment = center_align

    ws2.merge_cells("A2:G2")
    ws2["A2"].value = (
        "Primary: Silk Board, Bengaluru - KSPCB | 2026-10-20 to 2026-11-02 | 14 windows | "
        "AQI = max(subindex_PM2.5, subindex_PM10) | portal 24H means as provided"
    )
    ws2["A2"].font = sub_font
    ws2["A2"].alignment = Alignment(horizontal="center", wrap_text=True)
    ws2.row_dimensions[2].height = 28

    stats_headers = ["Metric", "AQI (Derived)", "PM2.5 (µg/m³)", "PM10 (µg/m³)", "Formula", "Excel Function", "Notes"]
    for ci, h in enumerate(stats_headers, 1):
        _header_style(ws2, 3, ci, h)

    # Data range references in the Data sheet (rows 4:17 = 14 rows)
    aqi_ref  = "Data!J4:J17"
    p25_ref  = "Data!F4:F17"
    p10_ref  = "Data!G4:G17"
    cat_ref  = "Data!K4:K17"

    stats_rows = [
        ("Mean (Average)", f"=AVERAGE({aqi_ref})", f"=AVERAGE({p25_ref})", f"=AVERAGE({p10_ref})",
         "x_bar = SUM(xi) / N", "=AVERAGE(range)", ""),
        ("Maximum", f"=MAX({aqi_ref})", f"=MAX({p25_ref})", f"=MAX({p10_ref})",
         "max(xi)", "=MAX(range)", ""),
        ("Minimum", f"=MIN({aqi_ref})", f"=MIN({p25_ref})", f"=MIN({p10_ref})",
         "min(xi)", "=MIN(range)", ""),
        ("Median", f"=MEDIAN({aqi_ref})", f"=MEDIAN({p25_ref})", f"=MEDIAN({p10_ref})",
         "Middle sorted value", "=MEDIAN(range)", ""),
        ("Sample Std Dev", f"=STDEV.S({aqi_ref})", f"=STDEV.S({p25_ref})", f"=STDEV.S({p10_ref})",
         "s = sqrt(SUM((xi-xbar)^2)/(N-1))", "=STDEV.S(range)", ""),
    ]

    for ri, row_data in enumerate(stats_rows, 4):
        for ci, val in enumerate(row_data, 1):
            cell = ws2.cell(ri, ci, val)
            cell.alignment = Alignment(horizontal="center" if ci > 1 else "left", vertical="center")
            cell.border = _thin_border()
            if ci == 1:
                cell.font = Font(name="Calibri", size=10, bold=True)
            else:
                cell.font = normal_font

    # Category count rows
    ws2.cell(10, 1, "Category Counts").font = Font(name="Calibri", size=11, bold=True, color="1A365D")
    cat_headers = ["Category", "Count (COUNTIFS)", "% of 14 Days", "AQI Range", "CPCB Health Impact"]
    for ci, h in enumerate(cat_headers, 1):
        _header_style(ws2, 11, ci, h, fill_hex="2B6CB0")

    cpcb_cats = [
        ("Good",        "0-50",    "Minimal impact"),
        ("Satisfactory","51-100",  "Minor breathing discomfort to sensitive people"),
        ("Moderate",    "101-200", "Breathing discomfort to people with lung/asthma/heart diseases"),
        ("Poor",        "201-300", "Breathing discomfort to most people on prolonged exposure"),
        ("Very Poor",   "301-400", "Respiratory illness on prolonged exposure"),
        ("Severe",      "401-500", "Affects healthy people; seriously impacts those with existing diseases"),
    ]

    for ri, (cat, aqi_range, health) in enumerate(cpcb_cats, 12):
        ws2.cell(ri, 1, cat).font = Font(name="Calibri", size=10, bold=True)
        ws2.cell(ri, 2, f'=COUNTIFS({cat_ref},"{cat}")')
        pct_cell = ws2.cell(ri, 3, f'=COUNTIFS({cat_ref},"{cat}")/14*100')
        pct_cell.number_format = "0.0%"
        ws2.cell(ri, 4, aqi_range)
        ws2.cell(ri, 5, health)
        fill_hex = CATEGORY_FILLS.get(cat, "FFFFFF")
        for ci in range(1, 6):
            c = ws2.cell(ri, ci)
            c.fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
            c.alignment = Alignment(horizontal="center" if ci > 1 else "left", vertical="center")
            c.border = _thin_border()

    ws2.column_dimensions["A"].width = 16
    ws2.column_dimensions["B"].width = 18
    ws2.column_dimensions["C"].width = 14
    ws2.column_dimensions["D"].width = 22
    ws2.column_dimensions["E"].width = 16
    ws2.column_dimensions["F"].width = 22
    ws2.column_dimensions["G"].width = 24

    # Native Excel Line Chart — Daily AQI
    line_chart = LineChart()
    line_chart.title = "Silk Board — 14-Day Derived AQI Trend (2026-10-20 to 2026-11-02)"
    line_chart.style = 10
    line_chart.y_axis.title = "Derived AQI"
    line_chart.x_axis.title = "Window Start Date"
    line_chart.height = 12
    line_chart.width  = 22

    aqi_data  = Reference(wb["Data"], min_col=10, min_row=3, max_row=17)
    aqi_dates = Reference(wb["Data"], min_col=1,  min_row=4, max_row=17)
    line_chart.add_data(aqi_data, titles_from_data=True)
    line_chart.set_categories(aqi_dates)
    ws2.add_chart(line_chart, "A20")

    # Native Excel Bar Chart — Category distribution
    bar_chart = BarChart()
    bar_chart.type = "col"
    bar_chart.title = "Silk Board — Category Frequency Distribution"
    bar_chart.y_axis.title = "Number of Days"
    bar_chart.x_axis.title = "CPCB AQI Category"
    bar_chart.height = 12
    bar_chart.width  = 18

    cat_data   = Reference(ws2, min_col=2, min_row=11, max_row=18)
    cat_labels = Reference(ws2, min_col=1, min_row=12, max_row=18)
    bar_chart.add_data(cat_data, titles_from_data=True)
    bar_chart.set_categories(cat_labels)
    ws2.add_chart(bar_chart, "L20")

    # ---------------------------------------------------------------
    # Sheet 3: Comparison (BTM vs Silk Board)
    # ---------------------------------------------------------------
    ws3 = wb.create_sheet("Comparison")
    ws3.merge_cells("A1:J1")
    ws3["A1"].value = "Multi-Station Comparison: BTM Layout (CPCB) vs Silk Board (KSPCB)"
    ws3["A1"].font = title_font
    ws3["A1"].alignment = center_align

    ws3.merge_cells("A2:J2")
    ws3["A2"].value = (
        "Common window: 2026-10-08 to 2026-10-21 (14 windows) | "
        "Both PM2.5 and PM10 valid for both stations | Portal 24H means | window start date label"
    )
    ws3["A2"].font = sub_font
    ws3["A2"].alignment = Alignment(horizontal="center", wrap_text=True)

    comp_headers = [
        "Date", "Station", "Agency",
        "PM2.5 (µg/m³)", "PM10 (µg/m³)",
        "Sub-index PM2.5", "Sub-index PM10",
        "AQI (Derived)", "Category", "Dominant Pollutant"
    ]
    comp_keys = [
        "date", "station_key", "agency",
        "pm25", "pm10", "subindex_pm25", "subindex_pm10",
        "aqi_derived", "category", "dominant_pollutant"
    ]
    for ci, h in enumerate(comp_headers, 1):
        _header_style(ws3, 3, ci, h)

    if not df_comp.empty:
        # Sort by date then station
        df_comp_sorted = df_comp.sort_values(["date", "station_key"])
        for ri, (_, row) in enumerate(df_comp_sorted.iterrows(), 4):
            cat = str(row.get("category", ""))
            fill_hex = CATEGORY_FILLS.get(cat, "FFFFFF")
            for ci, key in enumerate(comp_keys, 1):
                raw = row.get(key, "")
                if isinstance(raw, float) and np.isnan(raw):
                    val = "N/A"
                elif isinstance(raw, float):
                    val = round(raw, 2)
                else:
                    val = raw
                cell = _data_cell(ws3, ri, ci, val)
                cell.fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")

    # Summary rows
    last_row = 3 + (len(df_comp) if not df_comp.empty else 0) + 2
    ws3.cell(last_row, 1, "Summary Statistics").font = Font(name="Calibri", size=11, bold=True, color="1A365D")
    ws3.merge_cells(f"A{last_row}:J{last_row}")

    if not df_comp.empty:
        for station_key in df_comp["station_key"].unique():
            sub = df_comp[df_comp["station_key"] == station_key]
            last_row += 1
            ws3.cell(last_row, 1, station_key).font = bold_font
            ws3.cell(last_row, 2, f"Mean AQI: {sub['aqi_derived'].mean():.2f}").font = normal_font
            ws3.cell(last_row, 3, f"Max AQI: {sub['aqi_derived'].max():.1f}").font = normal_font
            ws3.cell(last_row, 4, f"Min AQI: {sub['aqi_derived'].min():.1f}").font = normal_font
            ws3.cell(last_row, 5, f"Mean PM10: {sub['pm10'].mean():.2f}").font = normal_font
            ws3.cell(last_row, 6, f"Mean PM2.5: {sub['pm25'].mean():.2f}").font = normal_font

    for i, w in enumerate([12, 28, 10, 13, 13, 15, 15, 13, 14, 16], 1):
        ws3.column_dimensions[get_column_letter(i)].width = w

    # ---------------------------------------------------------------
    # Sheet 4: QC_Audit
    # ---------------------------------------------------------------
    ws4 = wb.create_sheet("QC_Audit")
    ws4.merge_cells("A1:F1")
    ws4["A1"].value = "Data Quality & Station Exclusion Audit Report"
    ws4["A1"].font = title_font
    ws4["A1"].alignment = center_align

    audit_rows = [
        ("", ""),
        ("Primary Station", "Silk Board, Bengaluru - KSPCB"),
        ("Observation Window", "2026-10-20 to 2026-11-02 (14 windows)"),
        ("Access Date", "2026-11-03"),
        ("Portal URL", "https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/data"),
        ("AQI Nature", "Derived from portal 24H mean PM2.5 and PM10 using CPCB piecewise linear sub-index formulas"),
        ("Validity Note", "portal 24H mean as provided — no sub-hourly records; 16-hour completeness rule not applicable"),
        ("Date Label Convention", "window start date (YYYY-MM-DD of 22:41 rolling window opening)"),
        ("", ""),
        ("=== STATION AUDIT ===", ""),
        ("Silk Board (KSPCB) — PRIMARY", "PM10: 14/14 valid | PM2.5: 14/14 valid | No flat-line issues"),
        ("BTM Layout (CPCB) — COMPARISON", "PM10: 8/14 valid (6 null Oct 22-27) | Toluene flat-lined 16 windows; WD/WS flat-lined all 29"),
        ("Peenya (CPCB) — EXCLUDED", "PM10: 0/14 valid (sensor failure) | Toluene flat-lined 19 windows"),
        ("", ""),
        ("=== QC RULES APPLIED ===", ""),
        ("Instrument Range QC", "Values >= 999.0 ug/m3 or < 0 flagged as invalid (NaN)"),
        ("Flat-Line Detection", "Columns with >= 10 consecutive identical values flagged (advisory)"),
        ("Peenya Exclusion Reason", "PM10 sensor failure: 0/14 valid readings in primary window. Without PM10, dominant-pollutant analysis (PM2.5 vs PM10) is not possible."),
        ("", ""),
        ("=== CPCB BREAKPOINTS USED ===", ""),
        ("PM2.5 Good", "0-30 ug/m3 -> AQI 0-50"),
        ("PM2.5 Satisfactory", "31-60 ug/m3 -> AQI 51-100"),
        ("PM2.5 Moderate", "61-90 ug/m3 -> AQI 101-200"),
        ("PM2.5 Poor", "91-120 ug/m3 -> AQI 201-300"),
        ("PM2.5 Very Poor", "121-250 ug/m3 -> AQI 301-400"),
        ("PM2.5 Severe", "251-400 ug/m3 -> AQI 401-500"),
        ("PM10 Good", "0-50 ug/m3 -> AQI 0-50"),
        ("PM10 Satisfactory", "51-100 ug/m3 -> AQI 51-100"),
        ("PM10 Moderate", "101-250 ug/m3 -> AQI 101-200"),
        ("PM10 Poor", "251-350 ug/m3 -> AQI 201-300"),
        ("PM10 Very Poor", "351-430 ug/m3 -> AQI 301-400"),
        ("PM10 Severe", "431-600 ug/m3 -> AQI 401-500"),
    ]

    for ri, (k, v) in enumerate(audit_rows, 2):
        ws4.cell(ri, 1, k).font = Font(name="Calibri", size=10, bold=True, color="1A365D")
        ws4.cell(ri, 2, v).font = Font(name="Calibri", size=10)
        ws4.cell(ri, 2).alignment = Alignment(wrap_text=True)

    ws4.column_dimensions["A"].width = 32
    ws4.column_dimensions["B"].width = 70

    wb.save(output_excel)
    print(f"Saved: {output_excel}")


if __name__ == "__main__":
    create_excel_workbook()
