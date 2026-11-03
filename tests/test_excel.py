"""Tests for Excel generation, formula integrity, and chart embedding.

Updated for Silk Board ingestion pipeline:
- Sheet names: Data, Stats, Comparison, QC_Audit
- Data rows start at row 4 (title at 1, subtitle at 2, headers at 3)
- AQI is column J (col 10) in the Data sheet
"""

from pathlib import Path
import numpy as np
import openpyxl
import pandas as pd
import pytest

from reports.build_excel import create_excel_workbook


def test_excel_workbook_structure_and_formulas(tmp_path):
    """Verify AirAware_14day.xlsx has correct sheets, data, formulas, and charts."""
    test_excel = tmp_path / "AirAware_test.xlsx"
    create_excel_workbook(output_excel=test_excel)

    assert test_excel.exists(), "Excel file was not created"

    wb = openpyxl.load_workbook(test_excel, data_only=False)

    # Sheet names check (new structure)
    assert "Data"       in wb.sheetnames, f"'Data' sheet missing. Found: {wb.sheetnames}"
    assert "Stats"      in wb.sheetnames, f"'Stats' sheet missing. Found: {wb.sheetnames}"
    assert "Comparison" in wb.sheetnames, f"'Comparison' sheet missing. Found: {wb.sheetnames}"
    assert "QC_Audit"   in wb.sheetnames, f"'QC_Audit' sheet missing. Found: {wb.sheetnames}"

    ws_data  = wb["Data"]
    ws_stats = wb["Stats"]

    # --- Data sheet: 14 data rows starting at row 4 (row 3 = headers) ---
    dates = [ws_data.cell(row=r, column=1).value for r in range(4, 18)]
    assert len(dates) == 14, f"Expected 14 date rows, got {len(dates)}: {dates}"
    # All date labels should be strings like "2026-10-20"
    for d in dates:
        assert d is not None, f"Null date found in data rows: {dates}"

    # --- AQI values (column J = 10) should be numeric ---
    aqi_vals = [ws_data.cell(row=r, column=10).value for r in range(4, 18)]
    assert all(v is not None for v in aqi_vals), f"Null AQI values found: {aqi_vals}"
    assert all(isinstance(v, (int, float)) for v in aqi_vals), f"Non-numeric AQI: {aqi_vals}"

    # --- Stats sheet: check that AVERAGE formula references correct range ---
    # AVERAGE for AQI is in col B (second stats column), row 4 of stats data
    # Find any cell with AVERAGE formula referencing Data!J
    stats_formulas = []
    for row in ws_stats.iter_rows():
        for cell in row:
            if cell.value and isinstance(cell.value, str) and "AVERAGE" in cell.value:
                stats_formulas.append(cell.value)
    assert len(stats_formulas) > 0, "No AVERAGE formula found in Stats sheet"
    assert any("Data!J" in f for f in stats_formulas), \
        f"No AVERAGE formula referencing Data!J (AQI column) found. Formulas: {stats_formulas}"

    # --- Stats sheet: native Excel charts present ---
    assert len(ws_stats._charts) >= 1, "Expected at least 1 native chart in Stats sheet"

    # --- Verify Python and Excel AQI values match ---
    df = pd.read_csv("data/processed/aqi_14day.csv")
    aqi_from_excel = [float(v) for v in aqi_vals if v is not None]
    assert round(float(np.mean(aqi_from_excel)), 1) == round(float(df["aqi_derived"].mean()), 1), \
        f"Mean mismatch: Excel={np.mean(aqi_from_excel):.1f} Python={df['aqi_derived'].mean():.1f}"
    assert round(float(np.max(aqi_from_excel)), 1) == round(float(df["aqi_derived"].max()), 1), \
        f"Max mismatch: Excel={np.max(aqi_from_excel):.1f} Python={df['aqi_derived'].max():.1f}"
    assert round(float(np.min(aqi_from_excel)), 1) == round(float(df["aqi_derived"].min()), 1), \
        f"Min mismatch: Excel={np.min(aqi_from_excel):.1f} Python={df['aqi_derived'].min():.1f}"
    assert round(float(np.median(aqi_from_excel)), 1) == round(float(df["aqi_derived"].median()), 1), \
        f"Median mismatch"

    # --- Comparison sheet present and has rows ---
    ws_comp = wb["Comparison"]
    comp_data_rows = [ws_comp.cell(row=r, column=1).value for r in range(4, 40) if ws_comp.cell(row=r, column=1).value]
    # Comparison sheet should have data from 2 stations × 14 windows = 28 rows
    assert len(comp_data_rows) >= 14, f"Expected >= 14 comparison rows, got {len(comp_data_rows)}"

    # --- QC_Audit sheet present and has Peenya exclusion note ---
    ws_audit = wb["QC_Audit"]
    audit_text = " ".join([
        str(ws_audit.cell(r, c).value or "")
        for r in range(1, 50)
        for c in range(1, 3)
    ])
    assert "Peenya" in audit_text, "Peenya exclusion not documented in QC_Audit sheet"
    assert "EXCLUDED" in audit_text, "EXCLUDED label not found in QC_Audit sheet"
