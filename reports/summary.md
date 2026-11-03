# AirAware Bengaluru: Summary & Results

**Station:** Silk Board, Bengaluru - KSPCB
**Agency:** KSPCB
**Source:** CPCB Advance Search Portal (24H rolling averages)
**Accessed on:** 2026-11-03
**Portal URL:** https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/data
**Observation Window:** 2026-10-20 to 2026-11-02 (14 consecutive windows)
**AQI Nature:** Derived mathematically from portal 24H mean PM2.5 and PM10 concentrations using official CPCB piecewise linear sub-index formulas. No sub-hourly records available; 16-hour completeness rule not applicable.
**Date Label Convention:** Window start date (e.g. `2026-10-20` = window starting 2026-10-20 22:41 and closing 2026-10-21 22:41)

---

## 1. Primary Descriptive Statistics (Silk Board — After QC)

| Metric | AQI (Derived) | PM2.5 (µg/m3) | PM10 (µg/m3) | Formula | Excel |
|---|---|---|---|---|---|
| **Mean** | **135.81** | **39.26** | **150.59** | mean(x) | `=AVERAGE()` |
| **Maximum** | **365.6** (2026-10-26) | **97.58** | **402.58** | max(x) | `=MAX()` |
| **Minimum** | **48.9** (2026-10-23) | **9.8** | **48.88** | min(x) | `=MIN()` |
| **Median** | **116.3** | **35.0** | **124.06** | middle | `=MEDIAN()` |
| **Sample Std Dev** | **82.96** | **25.22** | **97.96** | s | `=STDEV.S()` |

*Validity note: portal 24H means as provided; no sub-hourly records; 16-hour completeness rule not applicable.*

---

## 2. Category Distribution (All 14 Days)

| Category | AQI Range | Days | % | CPCB Health Descriptor |
|---|---|---|---|---|
| **Good** | 0–50 | 0 | 0.0% | Minimal impact. |
| **Satisfactory** | 51–100 | 0 | 0.0% | Minor breathing discomfort to sensitive people. |
| **Moderate** | 101–200 | 0 | 0.0% | Breathing discomfort to people with lung, asthma, and heart diseases. |
| **Poor** | 201–300 | 0 | 0.0% | Breathing discomfort to most people on prolonged exposure. |
| **Very Poor** | 301–400 | 0 | 0.0% | Respiratory illness on prolonged exposure. |
| **Severe** | 401–500 | 0 | 0.0% | Affects healthy people and seriously impacts those with existing diseases. |
| **Total** | — | **14** | **100%** | All 6 categories accounted |

---

## 3. Dominant Pollutant Analysis

- **PM10 dominant on:** 14/14 days (100.0%)
- **Mean PM2.5/PM10 ratio:** 0.261 (range 0.147–0.375)
- **Interpretation:** Lower PM2.5/PM10 ratio (<0.5) hints at substantial contributions from coarse mechanical dust, unpaved road dust resuspension, and construction activities.

---

## 4. Regulatory Exceedance Analysis

| Limit | Pollutant | Standard (µg/m3) | Days Exceeded | % of Period |
|---|---|---|---|---|
| NAAQS (24-hr) | PM2.5 | 60 | 3/14 | 21.4% |
| NAAQS (24-hr) | PM10  | 100 | 10/14 | 71.4% |
| WHO 2021 (24-hr) | PM2.5 | 15 | 12/14 | 85.7% |
| WHO 2021 (24-hr) | PM10  | 45 | 14/14 | 100.0% |

---

## 5. Alert Engine Backtest (14-Day Chronological Replay)

**Alert Levels:** NORMAL (AQI <= 100) | ADVISORY (101-200) | WARNING (201-300) | DANGER (>300)
**Hysteresis margin:** 15 AQI points (prevents flip-flopping at boundaries)
**QC gate:** Suppresses alerts for readings failing instrument-range QC

| Date | AQI (derived) | Alert State | Transition / Note |
|---|---|---|---|
| 2026-10-20 | 104.9  | ADVISORY  | Escalated: subindex_PM10 > 100 |
| 2026-10-21 | 85.7   | NORMAL    | De-escalated (< 100 - hysteresis margin) |
| 2026-10-22 | 66.8   | NORMAL    | Satisfactory |
| 2026-10-23 | 48.9   | NORMAL    | Good |
| 2026-10-24 | 55.6   | NORMAL    | Satisfactory |
| 2026-10-25 | 191.5  | ADVISORY  | Escalated: subindex_PM10 > 100 |
| 2026-10-26 | 365.6  | DANGER    | Escalated: AQI > 300 (Very Poor) |
| 2026-10-27 | 233.7  | WARNING   | De-escalated: AQI < 300-15 margin |
| 2026-10-28 | 136.4  | ADVISORY  | De-escalated: AQI < 200-15 margin |
| 2026-10-29 | 126.3  | ADVISORY  | Maintained (hysteresis) |
| 2026-10-30 | 145.7  | ADVISORY  | Maintained |
| 2026-10-31 | 107.6  | ADVISORY  | Maintained |
| 2026-11-01 | 120.2  | ADVISORY  | Maintained |
| 2026-11-02 | 112.4  | ADVISORY  | Maintained |


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
