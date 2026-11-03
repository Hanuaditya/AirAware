# AirAware Bengaluru: Evidence-First Air Quality Analytics and Resilient Alerting System

**Course Code:** BCV755B — Computer Science & Engineering  
**Assignment:** Air Quality Monitoring, Analytics, and Mobile/Web Alert System  
**Station Analyzed:** BTM Layout, Bengaluru — CPCB (Station ID: site_162)  
**Observation Period:** January 8, 2024 to January 21, 2024 (14 Consecutive Calendar Days)  
**Data Provenance:** Central Pollution Control Board (CPCB) CAAQMS / OpenCity Portal  
**Date of Access:** 03-11-2026  

---

## Page 1: Title, Aim, Objectives & AQI Domain Foundation

### 1.1 Project Overview & Pitch
Conventional student submissions treat air quality assignments as simple data entry exercises in Excel, copying unverified numbers, plotting generic charts, and arbitrarily assuming that PM2.5 is the dominant pollutant. **AirAware Bengaluru** takes an evidence-first, production-grade approach:
1. **Mathematical Re-derivation:** Every published AQI value is cross-checked against CPCB segmented linear interpolation formulas using verified 24-hour mean PM2.5 and PM10 concentrations.
2. **Dominant Pollutant Detection:** The prominent pollutant is determined daily from constituent sub-indices, empirically proving which pollutant dictates ambient risk.
3. **Demonstrated Alert Engine:** Part (d) is not merely described as an abstract proposal; it is implemented as a functioning engine equipped with a **stale-data guard** and **hysteresis stabilization**, backtested across the 14-day observation window.
4. **Targeted City Interventions:** Four environmental mitigation measures are directly coupled to our empirical findings, accompanied by alignment with India's **National Clean Air Programme (NCAP)** and **UN Sustainable Development Goal 11 (Target 11.6)**.

### 1.2 Assignment Objectives
- **Part (a):** Acquire and tabulate 14 consecutive calendar days of verified air quality readings (AQI, PM2.5, PM10) from an official CPCB continuous station in Bengaluru with strict provenance metadata.
- **Part (b):** Compute descriptive statistical parameters (mean, maximum, minimum, median, sample standard deviation) in both Python and Excel; compile the complete 6-category frequency distribution; generate high-resolution publication charts.
- **Part (c):** Detail official CPCB categories and health impacts; empirically determine dominant pollutant frequencies; conduct PM2.5/PM10 ratio analysis to identify possible aerosol sources without causal overclaiming.
- **Part (d):** Architect and backtest the AirAware alert engine; formulate four targeted, evidence-linked city mitigation measures; establish explicit linkages to NCAP reduction targets and SDG 11.6.

### 1.3 The CPCB National AQI Mathematical Framework
The Indian National Air Quality Index (IND-AQI) translates raw ambient concentrations into a normalized metric (0–500) spanning six health categories:

$$\text{Sub-Index Formula: } I_p = \frac{I_{\text{Hi}} - I_{\text{Lo}}}{BP_{\text{Hi}} - BP_{\text{Lo}}} \cdot (C_p - BP_{\text{Lo}}) + I_{\text{Lo}}$$

Where $C_p$ is the truncated 24-hour pollutant concentration, $[BP_{\text{Lo}}, BP_{\text{Hi}}]$ is the breakpoint bracket enclosing $C_p$, and $[I_{\text{Lo}}, I_{\text{Hi}}]$ is the corresponding AQI sub-index range.

**Fundamental CPCB Aggregation Rule:**
$$\text{Overall AQI} = \max(I_{\text{PM2.5}}, I_{\text{PM10}}, I_{\text{NO2}}, I_{\text{SO2}}, I_{\text{CO}}, I_{\text{O3}}, I_{\text{NH3}})$$

The overall AQI is the **maximum sub-index, never an average**. The pollutant responsible for this maximum is officially designated the **prominent (dominant) pollutant**.

---

## Page 2: System Architecture, Methodology & Monitoring Station

### 2.1 End-to-End Pipeline Architecture

```
[ CPCB CAAQMS Station site_162 (BTM Layout) ]
                     │  (15-minute raw telemetry)
                     ▼
  1. INGESTION ENGINE (src/airaware/ingest.py)
     └── Writes data/raw/ + metadata.json (SHA-256 Checksum)
                     │
                     ▼
  2. CLEANING & VALIDATION (clean.py & validate.py)
     ├── Enforces schema, 24-hour mean aggregation, units (µg/m³)
     ├── Verifies 14 consecutive days (gap & duplicate guard)
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
  6. STREAMLIT APPLICATION & AUDIT INTERFACE (app/streamlit_app.py)
```

### 2.2 Station Characterization: BTM Layout, Bengaluru
- **Station Name:** BTM Layout, Bengaluru — CPCB
- **Station ID:** site_162 | **Coordinates:** 12.9135° N, 77.6101° E
- **Classification:** Urban Residential / Mixed Commercial & Arterial Transit Corridor
- **Surrounding Context:** Located near major traffic arteries (Hosur Road, Outer Ring Road, Silk Board Junction) with heavy commercial transit, construction activity, and residential colonies.

---

## Page 3: Assignment Part (a) — Verified 14-Day Dataset Table

*Source: CPCB National AQI Repository / CAAQMS site_162 (BTM Layout), accessed on 03-11-2026. Data aggregated to official 24-hour means according to CPCB guidelines.*

| Date | Station | Reported AQI | Derived Category | PM2.5 (µg/m³) | PM10 (µg/m³) | PM2.5 Sub-index | PM10 Sub-index | Dominant Pollutant | Data Integrity Status |
|---|---|---|---|---|---|---|---|---|---|
| **2024-01-08** | BTM Layout, Bengaluru | 40 | Good | 18.9 | 39.6 | 31.5 | 39.6 | PM10 | VALID |
| **2024-01-09** | BTM Layout, Bengaluru | 54 | Satisfactory | 15.7 | 54.0 | 26.2 | 54.0 | PM10 | VALID |
| **2024-01-10** | BTM Layout, Bengaluru | 56 | Satisfactory | 21.0 | 56.0 | 35.0 | 56.0 | PM10 | VALID |
| **2024-01-11** | BTM Layout, Bengaluru | 63 | Satisfactory | 17.7 | 62.7 | 29.5 | 62.7 | PM10 | VALID |
| **2024-01-12** | BTM Layout, Bengaluru | 61 | Satisfactory | 23.9 | 60.7 | 39.8 | 60.7 | PM10 | VALID |
| **2024-01-13** | BTM Layout, Bengaluru | 83 | Satisfactory | 17.3 | 82.6 | 28.8 | 82.6 | PM10 | VALID |
| **2024-01-14** | BTM Layout, Bengaluru | 86 | Satisfactory | 19.2 | 86.0 | 32.0 | 86.0 | PM10 | VALID |
| **2024-01-15** | BTM Layout, Bengaluru | 80 | Satisfactory | 19.7 | 80.2 | 32.8 | 80.2 | PM10 | VALID |
| **2024-01-16** | BTM Layout, Bengaluru | 214 | Poor | 19.3 | 263.9 | 32.2 | 213.9 | PM10 | VALID |
| **2024-01-17** | BTM Layout, Bengaluru | 84 | Satisfactory | 19.0 | 84.4 | 31.7 | 84.4 | PM10 | VALID |
| **2024-01-18** | BTM Layout, Bengaluru | 78 | Satisfactory | 15.0 | 77.7 | 25.0 | 77.7 | PM10 | VALID |
| **2024-01-19** | BTM Layout, Bengaluru | 66 | Satisfactory | 18.6 | 65.7 | 31.0 | 65.7 | PM10 | VALID |
| **2024-01-20** | BTM Layout, Bengaluru | 71 | Satisfactory | 19.0 | 70.7 | 31.7 | 70.7 | PM10 | VALID |
| **2024-01-21** | BTM Layout, Bengaluru | 71 | Satisfactory | 13.0 | 70.8 | 21.7 | 70.8 | PM10 | VALID |

---

## Page 4: Assignment Part (b) — Statistical Analysis & Formulas

### 4.1 Descriptive Statistics Cross-Verification (Python vs. Excel)

| Metric | AQI | PM2.5 (µg/m³) | PM10 (µg/m³) | Mathematical Formula | Excel Equivalent |
|---|---|---|---|---|---|
| **Mean ($\bar{x}$)** | **79.07** | **18.38** | **82.50** | $\bar{x} = \frac{1}{N}\sum_{i=1}^N x_i$ | `=AVERAGE(range)` |
| **Maximum** | **214.0** *(16-Jan)* | **23.9** *(12-Jan)* | **263.9** *(16-Jan)* | $\max(x_i)$ | `=MAX(range)` |
| **Minimum** | **40.0** *(08-Jan)* | **13.0** *(21-Jan)* | **39.6** *(08-Jan)* | $\min(x_i)$ | `=MIN(range)` |
| **Median** | **71.0** | **18.95** | **70.75** | Middle sorted value | `=MEDIAN(range)` |
| **Sample Std. Dev. ($s$)** | **41.01** | **2.64** | **53.87** | $s = \sqrt{\frac{\sum (x_i - \bar{x})^2}{N - 1}}$ | `=STDEV.S(range)` |

### 4.2 CPCB AQI Category Frequency Breakdown (All 6 Standard Classes)

| Category | AQI Range | Count (Days) | Frequency (%) | CPCB Health Impact Descriptor |
|---|---|---|---|---|
| **Good** | 0–50 | 1 | 7.1% | Minimal impact |
| **Satisfactory** | 51–100 | 12 | 85.7% | Minor breathing discomfort to sensitive people |
| **Moderate** | 101–200 | 0 | 0.0% | Breathing discomfort to people with lung, asthma, and heart diseases |
| **Poor** | 201–300 | 1 | 7.1% | Breathing discomfort to most people on prolonged exposure |
| **Very Poor** | 301–400 | 0 | 0.0% | Respiratory illness on prolonged exposure |
| **Severe** | 401–500 | 0 | 0.0% | Affects healthy people and seriously impacts those with existing diseases |
| **Total** | — | **14** | **100.0%** | Complete 14-day accounting verified |

---

## Page 5: Required Charts (High-Resolution Visualizations)

### Chart 1: Daily AQI 14-Day Trend with Category Color Bands
![Daily AQI Trend](../outputs/figures/chart1_daily_aqi.png)
*Figure 1: 14-day chronological line plot of daily Air Quality Index for BTM Layout, Bengaluru. Background bands represent official CPCB categories. A single episodic spike occurred on 16-Jan-2024 (AQI 214, Poor category).*

### Chart 2: Category Frequency Distribution
![Category Frequency Distribution](../outputs/figures/chart2_category_counts.png)
*Figure 2: Distribution of daily AQI across all six official CPCB categories. Satisfactory air quality predominated on 12 of 14 days (85.7%).*

### Chart 3: Particulate Concentrations vs. Indian NAAQS and WHO 2021 Limits
![Particulate Matter vs Standards](../outputs/figures/chart3_pm_vs_standards.png)
*Figure 3: Daily PM2.5 and PM10 concentrations plotted against Indian National Ambient Air Quality Standards (NAAQS: PM2.5=60, PM10=100 µg/m³) and WHO 2021 guidelines (PM2.5=15, PM10=45 µg/m³).*

---

## Page 6: Assignment Part (c) — Dominant Pollutant & Environmental Diagnostics

### 6.1 Dominant Pollutant Identification
Across the 14-day observation period, **PM10 was identified as the dominant pollutant on 14 out of 14 days (100.0%)**.
In typical textbook scenarios, students assume PM2.5 is dominant. However, authentic monitoring data from BTM Layout demonstrates that coarse particulate matter consistently drove the highest sub-indices.

### 6.2 PM2.5 / PM10 Ratio Diagnostic
- **Observed Mean Ratio:** $0.266 \pm 0.09$ (Range: 0.073 to 0.477).
- **Physical Interpretation:** A particulate ratio below 0.4 indicates a strong preponderance of **coarse mechanical particles** over fine combustion aerosols. 

### 6.3 Possible Contributing Sources (No Overclaiming)
While a 14-day observational window is statistically insufficient to prove causal attribution, the predominance of coarse PM10 alongside local land-use patterns suggests the following **possible contributing sources**:
1. **Resuspended Road Dust:** High vehicular traffic along the Central Silk Board and Bannerghatta Road corridors constantly pulverizes and resuspends silt from unpaved road shoulders.
2. **Construction and Demolition (C&D) Activities:** Active infrastructure, commercial civil works, and metro expansion generate substantial fugitive dust.
3. **Episodic Spike on January 16:** PM10 spiked sharply to 263.9 µg/m³ (while PM2.5 remained low at 19.3 µg/m³, ratio 0.073), pointing toward localized earthmoving, road excavation, or heavy construction dust rather than regional combustion.

---

## Page 7: Assignment Part (d) — AirAware Alert Engine & Backtest

### 7.1 Alert Engine Design
To protect public health without causing alert fatigue, AirAware incorporates three algorithmic safeguards:
1. **Immediate Escalation:** When air pollution worsens, the alert level immediately jumps to the higher severity tier.
2. **Hysteresis Stabilization (10 AQI Points):** To prevent rapid flickering/flip-flopping when AQI hovers near category boundaries, an alert is only downgraded when the AQI falls at least 10 points below the tier's lower bound.
3. **Stale-Data Guard (36 Hours):** If telemetry is interrupted or sensor readings are older than 36 hours, active alerts are suppressed to prevent broadcasting misleading health advice based on obsolete data.

### 7.2 14-Day Chronological Backtest Performance
Replaying the 14 verified days through the alert engine yielded:
- **Active Alert Days:** 1 day (16-Jan-2024, WARNING tier triggered by AQI 214).
- **Hysteresis Stabilization:** When AQI dropped on 17-Jan, the engine evaluated the downgrade criteria cleanly.
- **Alert Flip-Flops Avoided:** 0 false transitions during stable periods, demonstrating robust signal stability.

### 7.3 Four Evidence-Linked Interventions for Bengaluru
Each intervention is coupled directly to our data findings, with an explicit measurement metric:

| Measure | Target Pollutant | Empirical Rationale | Evaluation Metric via AirAware |
|---|---|---|---|
| **1. Mechanized Road Sweeping & Dust Control** | **PM10** | Directly addresses PM10 dominance (100% of days; ratio 0.27). Deploy regenerative air vacuum sweepers along Hosur Road, mandate misting curtains on C&D sites, and pave unpaved shoulders. | Compare subsequent 14-day mean PM10 concentrations against the 82.5 µg/m³ baseline. |
| **2. Intelligent Corridor Synchronization** | **PM2.5, NO₂** | Alleviates stop-and-go congestion at Silk Board and BTM junctions, suppressing fine diesel combustion spikes. | Measure reduction in 3-day rolling PM2.5 peaks and evening rush-hour particulate ratios. |
| **3. Commercial Generator Regulation** | **PM2.5, SO₂** | Regulate emissions from diesel backup generators across commercial parks during peak demand hours. | Track nocturnal baseline particulate concentrations across south Bengaluru. |
| **4. Dense Hyper-Local Sensor Mesh & Urban Green Buffers** | **All** | Addresses the limitation of relying on a single CAAQMS node by deploying low-cost optical sensors and planting multi-tier dust-trapping tree buffers. | Evaluate spatial variance across micro-clusters within a 3 km radius of BTM Layout. |

---

## Page 8: National Policy Alignment, Conclusions & Viva Defense

### 8.1 Alignment with National Clean Air Programme (NCAP)
- **Policy Context:** Launched in 2019 by the Ministry of Environment, Forest and Climate Change (MoEFCC), NCAP originally targeted a 20–30% reduction in particulate concentrations, updated in 2022 to mandate **up to 40% reduction or achieving NAAQS** by 2025–2026 across 131 non-attainment cities.
- **AirAware Contribution:** AirAware provides municipal corporations (BBMP) with automated sub-index validation, identifies whether coarse dust or fine combustion dominates, and measures intervention outcomes against verified baselines.

### 8.2 Alignment with UN Sustainable Development Goal 11
- **Goal:** Sustainable Cities and Communities.
- **Target 11.6:** *"By 2030, reduce the adverse per capita environmental impact of cities, including by paying special attention to air quality and municipal and other waste management."*
- **Indicator 11.6.2:** *Annual mean levels of fine particulate matter (PM2.5 and PM10) in cities (population weighted).*
- **AirAware Contribution:** Implements open, reproducible 24-hour aggregation aligned with international reporting guidelines, ensuring citizen-facing metrics are mathematically sound.

### 8.3 Limitations
1. **Temporal Horizon:** 14 days captures short-term weather fluctuations but cannot establish multi-year seasonal trends.
2. **Spatial Representativeness:** A single stationary monitor in BTM Layout cannot represent the micro-climates of north or east Bengaluru.
3. **Gaseous Pollutants:** While PM2.5 and PM10 were analyzed, secondary formation from gaseous precursors (NOx, SO2, VOCs) requires multi-pollutant monitoring.

### 8.4 Viva Questions & Model Answers
1. **Q: Why is overall AQI the maximum sub-index rather than an average?**  
   *A: Averaging conceals extreme health hazards. If PM10 is in the 'Severe' category while another pollutant is 'Good', an average would report 'Moderate', creating a perilous false sense of safety. The human respiratory system is harmed by the worst pollutant present.*
2. **Q: Why can recomputed PM AQI be lower than published AQI, but never higher?**  
   *A: Published AQI includes gases (NO2, SO2, CO, O3). Adding pollutants can only increase or maintain the maximum sub-index, never decrease it. If PM-only AQI exceeds published AQI, the published number violates CPCB's mathematical definition.*
3. **Q: Why shouldn't you claim that traffic caused a pollution spike from 14 days of data?**  
   *A: Correlation does not equal causation. 14 days cannot distinguish traffic emissions from wind speed changes, planetary boundary layer height, or construction activity without chemical speciation.*
4. **Q: How does hysteresis prevent alert flickering?**  
   *A: By requiring the AQI to drop 10 points below a category threshold before downgrading, it prevents oscillating notifications when air quality hovers around a boundary.*

---
*AirAware Bengaluru — Developed for BCV755B CSE Assignment | All Code, Configurations, and Unit Tests Verified.*

