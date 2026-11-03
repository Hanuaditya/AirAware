# AirAware Bengaluru 🌿
> **An Evidence-First Air Quality Analytics, Validation & Resilient Alerting Pipeline**  
> Developed for Academic Course Assignment **BCV755B (Computer Science & Engineering)**

---

## 🎯 The Core Concept & Thesis

Standard air quality coursework submissions often rely on unverified portal numbers entered into Excel, simple charts, and the unsubstantiated assumption that PM2.5 is always the dominant pollutant. **AirAware Bengaluru** provides a production-grade data engineering and environmental analytics pipeline:

1. **CPCB Sub-Index Recomputation & Audit:** Every published AQI reading is mathematically verified against CPCB segmented linear interpolation formulas using verified 24-hour mean PM2.5 and PM10 concentrations. Because overall AQI is officially defined as the **maximum** constituent sub-index ($\text{AQI} = \max(I_p)$), a recomputed PM sub-index exceeding the published value flags a critical data error.
2. **Empirical Dominant Pollutant Discovery:** The prominent pollutant is calculated daily from sub-indices rather than assumed. In our authentic 14-day CPCB dataset from BTM Layout, Bengaluru, **PM10 was dominant on 14 of 14 days (100.0%)** with a mean $\text{PM}_{2.5} / \text{PM}_{10}$ ratio of `0.266`. This empirically demonstrates that coarse mechanical dust (resuspended road dust, construction/demolition) drove air pollution in this corridor, rather than combustion.
3. **Demonstrated Alert Engine with Hysteresis (Part d):** Rather than describing an app hypothetically, AirAware includes a functioning alerting engine featuring **immediate escalation**, a **10-point hysteresis margin** (preventing alert flickering across category boundaries), and a **36-hour stale-data guard**, backtested over the 14-day period.
4. **Standards Benchmarking:** Daily concentrations of PM2.5 and PM10 are evaluated against both Indian **NAAQS** (60 & 100 µg/m³) and **WHO 2021** guidelines (15 & 45 µg/m³).
5. **Multi-Platform Deliverables:**
   - Interactive 8-page **Streamlit dashboard** (`app/streamlit_app.py`)
   - Native multi-sheet **Excel workbook** with live formulas (`outputs/AirAware_14day.xlsx`)
   - Complete 6–8 page **formal Word report** (`outputs/BCV755B_CSE_Report.docx`)
   - 300-DPI high-resolution publication figures (`outputs/figures/`)

---

## ⚙️ How It Works (Pipeline Architecture)

```
[ CPCB CAAQMS Station site_162 (BTM Layout) ]
                     │  (15-minute raw telemetry)
                     ▼
  1. INGESTION ENGINE (src/airaware/ingest.py)
     └── Saves data/raw/ + metadata.json (SHA-256 Checksum)
                     │
                     ▼
  2. CLEANING & VALIDATION (clean.py & validate.py)
     ├── Enforces schema, 24-hour mean aggregation, units (µg/m³)
     ├── Verifies 14 consecutive calendar days (gap & duplicate guard)
     └── CPCB Sub-Index Audit: AQI_published >= max(I_PM2.5, I_PM10)
                     │
                     ▼
  3. ANALYTICS & METRICS ENGINE (aqi.py, stats.py)
     ├── Computes sub-indices, dominant pollutant, PM ratio
     └── Descriptive statistics & 6-category distribution
            ┌────────┴────────┐
            ▼                 ▼
  4. ALERT ENGINE       5. VISUALIZATION ENGINE
     (alerts.py)           (charts.py)
     ├── Immediate esc.    ├── 300-DPI Publication PNGs
     ├── Hysteresis        └── Interactive Plotly figures
     └── 14-day backtest
            └────────┬────────┘
                     ▼
  6. DELIVERY & USER INTERFACES
     ├── Streamlit App (app/streamlit_app.py)
     ├── Live Excel Workbook (reports/build_excel.py -> outputs/AirAware_14day.xlsx)
     └── Academic Word Report (reports/build_docx.py -> outputs/BCV755B_CSE_Report.docx)
```

### Mathematical Formulation
$$\text{Linear Sub-Index: } I_p = \frac{I_{\text{Hi}} - I_{\text{Lo}}}{BP_{\text{Hi}} - BP_{\text{Lo}}} \cdot (C_p - BP_{\text{Lo}}) + I_{\text{Lo}}$$
$$\text{Overall AQI: } \text{AQI}_{\text{overall}} = \max(I_{\text{PM2.5}}, I_{\text{PM10}}, \dots)$$
$$\text{Audit Invariant: } \text{AQI}_{\text{reported}} \ge \max(I_{\text{PM2.5}}, I_{\text{PM10}})$$

---

## 📁 Repository Structure

```
cv/
├── README.md                      # Comprehensive project guide and instructions
├── PLAN.md                        # Master architecture plan and specification
├── requirements.txt               # Dependencies (pandas, openpyxl, python-docx, etc.)
├── pytest.ini                     # Pytest configuration
├── config/
│   ├── breakpoints.yaml           # CPCB concentration breakpoints for PM2.5 & PM10
│   ├── categories.yaml            # 6 CPCB categories, accessible colors & health advice
│   └── alerts.yaml                # Alert engine levels, hysteresis & staleness limits
├── data/
│   ├── raw/
│   │   ├── cpcb_btm_layout_15min_raw.csv  # 15-minute continuous observations (1307 rows)
│   │   ├── cpcb_btm_layout_14day_raw.csv  # Untouched 14-day aggregated table
│   │   └── metadata.json                  # Provenance, station ID, access date, SHA-256
│   ├── processed/
│   │   └── aqi_14day.csv          # Cleaned dataset with derived sub-indices & flags
│   └── sample/
│       └── DEMO_ONLY.csv          # Flagged synthetic demo data (with edge cases)
├── src/airaware/
│   ├── __init__.py
│   ├── aqi.py                     # Sub-index formula & category mapper
│   ├── clean.py                   # Data cleaning, schema enforcement & derivation
│   ├── validate.py                # Calendar gap detection & CPCB consistency audit
│   ├── stats.py                   # Descriptive statistics & category counts
│   ├── alerts.py                  # Alert engine with hysteresis & backtest replay
│   ├── health.py                  # CPCB official health advisory mapping
│   ├── charts.py                  # Matplotlib (300 DPI) & Plotly visualizers
│   ├── ingest.py                  # Provenance tracking with SHA-256 integrity checksums
│   └── fetch_cpcb.py              # Automated CPCB CAAQMS 15-minute aggregator
├── app/
│   └── streamlit_app.py           # Multi-page interactive Streamlit dashboard
├── reports/
│   ├── build_figures.py           # Exports 300-DPI PNGs & summary.md
│   ├── build_excel.py             # Generates outputs/AirAware_14day.xlsx
│   ├── build_docx.py              # Generates outputs/BCV755B_CSE_Report.docx
│   ├── summary.md                 # Markdown statistics, formulas & report tables
│   └── report_outline.md          # 8-page assignment report draft & viva defense
├── tests/
│   ├── test_aqi.py                # Sub-index boundary tests & max-not-average rule
│   ├── test_stats.py              # Hand-computed statistical verification
│   ├── test_validate.py           # Gap detection & CPCB sub-index violation checks
│   ├── test_alerts.py             # Escalation, hysteresis suppression & stale guards
│   └── test_excel.py              # Excel workbook structure, live formulas & charts
└── outputs/
    ├── AirAware_14day.xlsx        # Excel workbook with live formulas & native charts
    ├── BCV755B_CSE_Report.docx    # Complete 6–8 page formal submission report
    └── figures/                   # 300-DPI high-res figures for submission
        ├── chart1_daily_aqi.png
        ├── chart2_category_counts.png
        ├── chart3_pm_vs_standards.png
        └── chart4_dominant_pollutant.png
```

---

## 🛠️ Installation & Execution

### 1. Environment Setup
```bash
# Clone the repository and install dependencies
pip install -r requirements.txt
```

### 2. Run Test Suite (17 Unit Tests)
```bash
pytest -v
```
All unit tests verify:
- PM2.5 and PM10 sub-indices at boundary edges (30/31, 60/61, 90/91, 120/121, 250/251)
- The fundamental CPCB rule that overall AQI = max(sub-indices)
- Statistical formulas against hand-computed values
- Detection of missing calendar days, duplicate dates, and sub-index inconsistency
- Alert engine immediate escalation, 10-point hysteresis suppression, and stale-data guards
- Excel workbook sheets, live formulas, and native charts

### 3. Launch Interactive Streamlit Dashboard
```bash
streamlit run app/streamlit_app.py
```
Open `http://localhost:8501` to explore all 8 interactive pages.

### 4. Regenerate Submission Artifacts
```bash
# Export 300-DPI figures and markdown summary
python reports/build_figures.py

# Rebuild Excel workbook with live formulas and native charts
python reports/build_excel.py

# Rebuild formal Word report (.docx)
python reports/build_docx.py
```

---

## 🏛️ Data Provenance & Audit

- **Monitoring Station:** BTM Layout, Bengaluru — CPCB (Station ID: `site_162`)
- **Coordinates:** 12.9135° N, 77.6101° E
- **Data Source:** Central Pollution Control Board (CPCB) Continuous Ambient Air Quality Monitoring Station (CAAQMS) repository hosted on OpenCity Portal.
- **Access Date:** November 3, 2026
- **Observation Period:** January 8, 2024 to January 21, 2024 (14 consecutive calendar days).
- **Sampling Frequency:** 15-minute continuous monitoring telemetry (1,307 raw records across the 14 days).
- **Aggregation:** 15-minute observations were averaged to official 24-hour mean concentrations according to CPCB guidelines.
- **Completeness Audit:**
  - 13 of 14 days had 19 to 24 valid hours of data (exceeding the 16-hour CPCB minimum).
  - On January 8, PM10 had 21 valid hours while PM2.5 had 10 valid hours.
  - On January 16, PM10 reached the instrument saturation cap of 999.99 µg/m³ during morning hours (05:15–09:45 AM), producing a daily mean of 263.9 µg/m³ (AQI 214, Poor) and the lowest $\text{PM}_{2.5} / \text{PM}_{10}$ ratio of `0.073`.

---

## ⚠️ Limitations

1. **Short Observation Window (14 Days):** While fully compliant with assignment specifications, 14 days cannot distinguish seasonal shifts (e.g., monsoon washout vs. winter meteorological inversions) from long-term emission trends.
2. **Spatial Representativeness:** Telemetry from a single monitoring station in BTM Layout represents south-central transit and residential micro-environments, but cannot be generalized across all of Greater Bengaluru (e.g., Whitefield or Peenya industrial zones).
3. **Absence of Speciation & Causality:** 14 days of particulate mass data without chemical speciation (elemental carbon, sulfates, nitrates) cannot prove causal origins. Consequently, findings are reported strictly as *possible contributing sources*.

---

## 🎓 Viva Voce Preparation Guide

1. **Why is overall AQI the maximum sub-index rather than an average?**  
   *Averaging obscures hazardous exposure. If PM10 is in the 'Severe' category while another pollutant is 'Good', an average would report 'Moderate', creating a dangerous false sense of security. The human respiratory system is harmed by the worst pollutant present.*
2. **Why does recomputed PM AQI serve as a lower bound?**  
   *Published AQI includes gases (NO2, SO2, CO, O3). Adding pollutants can only increase or maintain the maximum sub-index. If $\text{AQI}_{\text{published}} < \text{AQI}_{\text{from\_PM}}$, the published record violates CPCB's mathematical definition.*
3. **Why did PM10 dominate in Bengaluru during the observation period?**  
   *The observed $\text{PM}_{2.5} / \text{PM}_{10}$ ratio of 0.27 indicates a high prevalence of coarse mechanical dust (resuspended road dust along arterial corridors, construction activity, unpaved shoulders) rather than combustion exhaust.*
4. **How does hysteresis prevent alert flickering?**  
   *By requiring the AQI to fall 10 points below the category boundary before downgrading, it prevents oscillating notifications when air quality hovers around a boundary.*
