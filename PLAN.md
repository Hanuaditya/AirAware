# AirAware Bengaluru — BCV755B CSE Assignment Master Plan

> An evidence-first air-quality analytics and alert system. It answers every part of the assignment (a–d), then goes further with data validation, dominant-pollutant analysis, an alert-engine backtest, and an NCAP / SDG 11 impact linkage.

---

## 0. The one-line pitch (say this to your teacher)

"I didn't just chart 14 days of AQI. I built a small data pipeline that collects official CPCB readings, **re-computes the AQI from PM2.5 and PM10 to verify the published numbers**, identifies the dominant pollutant per day, and **backtests an alert system on the same 14 days** — so the application proposal in part (d) is demonstrated, not just described."

## 1. Why this beats a typical submission

| Typical submission | This project |
|---|---|
| Table copied from a website | Reproducible pipeline with provenance (source, station, access date) for every row |
| Average / max / min in Excel | Same numbers in Excel *and* Python, cross-checked by unit tests |
| Two charts | Two required charts + station comparison, WHO/NAAQS threshold lines, dominant-pollutant chart |
| "PM2.5 is the main pollutant" (assumed) | Computed per day from sub-indices, counted, reported with evidence |
| App idea in words | Working Streamlit dashboard + alert engine replayed over the 14 days |
| Generic measures | Each of the 4 measures tied to the pollutant your data actually shows |

## 2. Non-negotiable integrity rules

1. **Never invent or "smooth" data.** If a value is missing, store `NaN` and show it as "unavailable".
2. The sample CSV in the repo is clearly flagged `DEMO ONLY` and must be replaced with real CPCB data before submission. The dashboard shows a red "DEMO DATA" banner when it is loaded.
3. Every table/figure in the report has a source line: *Source: CPCB, National AQI dashboard / data repository, station X, accessed on DD-MM-YYYY.*
4. 14 days cannot prove causes. The report says "possible contributing sources", never "caused by".

## 3. Mapping to the assignment (marks)

| Part | Marks | What the project delivers |
|---|---|---|
| (a) Collect and tabulate 14 days | 15 | `data/raw/` CSV from CPCB, cleaned table with date, station, AQI, PM2.5, PM10, category, source and access date |
| (b) Statistics and charts | 15 | Mean/max/min, category counts, line chart of daily AQI, bar chart of category counts (exported as PNG for the report) |
| (c) Categories, health effects, main pollutant | 10 | Category table, health-effect text, dominant pollutant per day from sub-indices, counts, source hypotheses |
| (d) App, 4 measures, NCAP, SDG 11 | 10 | Streamlit app + alert engine, 4 measures linked to findings, NCAP and SDG 11 section |

## 4. Scope (keep it finishable)

**Must have (covers the whole assignment):**
- Data loader and cleaner for one Bengaluru CPCB station, 14 consecutive days
- Statistics, category counts, 2 required charts
- Dominant pollutant analysis
- Streamlit dashboard
- Alert engine with simple backtest
- Report (PDF or DOCX, 6–8 pages)

**Stretch (only if time remains):**
- A second and third Bengaluru station for comparison
- A 60–90 day baseline to put the 14 days in context (clearly labelled as extra)
- Simple next-day AQI trend indicator (label it "indicative", not a forecast)

## 5. Domain knowledge you must understand (viva-proof)

### 5.1 CPCB AQI categories (India)

| AQI | Category |
|---|---|
| 0–50 | Good |
| 51–100 | Satisfactory |
| 101–200 | Moderate |
| 201–300 | Poor |
| 301–400 | Very Poor |
| 401–500 | Severe |

### 5.2 How AQI is computed

1. For each pollutant, compute a **sub-index** by linear interpolation between breakpoints:
   `I_p = (I_hi − I_lo) / (BP_hi − BP_lo) × (C_p − BP_lo) + I_lo`
2. **Overall AQI = the maximum sub-index.** It is not an average.
3. The pollutant giving that maximum is the **prominent (dominant) pollutant**.
4. PM2.5 and PM10 use 24-hour averages. CPCB requires at least 3 pollutants with a valid PM2.5 or PM10 to publish an AQI.

### 5.3 Breakpoints for the two required pollutants (µg/m³, 24-h)

| Sub-index range | PM2.5 | PM10 |
|---|---|---|
| 0–50 | 0–30 | 0–50 |
| 51–100 | 31–60 | 51–100 |
| 101–200 | 61–90 | 101–250 |
| 201–300 | 91–120 | 251–350 |
| 301–400 | 121–250 | 351–430 |
| 401–500 | 250+ | 430+ |

> Verify these against the CPCB "About National AQI" document before you cite them, and implement them in one config file so they are easy to correct.

### 5.4 Reference limits for context lines on charts
- India NAAQS 24-h: PM2.5 = 60, PM10 = 100 µg/m³
- WHO 2021 guideline 24-h: PM2.5 = 15, PM10 = 45 µg/m³

### 5.5 Why validation is valuable
Published AQI also includes gases (NO₂, SO₂, CO, O₃…). So recomputing from PM only gives a **lower bound**: `AQI_published ≥ AQI_from_PM`. If the PM-only AQI is higher than the published one, something is wrong (units, averaging window, wrong station). Flag it in the data-quality report. Note: the sample numbers in the earlier draft table (e.g. PM2.5 = 72 alongside AQI 165) would **fail** this check, which is exactly why you must use real data.

## 6. Architecture

```
          ┌─────────────────────────────┐
          │  CPCB (CCR data / dashboard)│   manual CSV download
          │  optional: OpenAQ API       │   or API (needs key)
          └──────────────┬──────────────┘
                         ▼
┌────────────────────────────────────────────────┐
│ 1. INGESTION   src/airaware/ingest.py          │
│    CSV/API → raw/ (immutable) + metadata.json  │
└──────────────┬─────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────┐
│ 2. CLEANING + VALIDATION  clean.py, validate.py│
│    schema, units, 14 consecutive days, NaN,    │
│    AQI-from-PM cross-check, quality report     │
└──────────────┬─────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────┐
│ 3. ANALYTICS ENGINE   aqi.py, stats.py         │
│    sub-indices, category, dominant pollutant,  │
│    mean/max/min, counts, exceedance days       │
└───────┬───────────────────────┬────────────────┘
        ▼                       ▼
┌──────────────────┐   ┌─────────────────────────┐
│ 4. ALERT ENGINE  │   │ 5. VISUALISATION        │
│ alerts.py        │   │ charts.py (matplotlib / │
│ thresholds,      │   │ plotly), report figures │
│ hysteresis,      │   └───────────┬─────────────┘
│ stale-data guard │               │
│ backtest         │               │
└───────┬──────────┘               │
        └──────────────┬───────────┘
                       ▼
┌────────────────────────────────────────────────┐
│ 6. DELIVERY                                    │
│  app/streamlit_app.py  (dashboard + alerts)    │
│  reports/build_report.py (figures + tables)    │
│  outputs/ (PNG, CSV, quality report)           │
└────────────────────────────────────────────────┘
```

### Design decisions to mention in the report
- **Immutable raw data**: raw files are never edited; cleaning writes to `data/processed/`.
- **Config-driven breakpoints** (`config/breakpoints.yaml`): easy to audit and correct.
- **Pure functions + unit tests** for AQI math.
- **Stale-data guard**: alerts are suppressed if the last valid reading is older than a set limit.
- **Hysteresis**: an alert only clears after the AQI drops a margin below the threshold, to avoid flip-flopping.

## 7. Repository structure

```
airaware-bengaluru/
├── README.md
├── PLAN.md
├── requirements.txt
├── config/
│   ├── breakpoints.yaml        # PM2.5, PM10 (+ optional gases) breakpoints
│   ├── categories.yaml         # AQI ranges, colours, health text
│   └── alerts.yaml             # thresholds, hysteresis, stale limit
├── data/
│   ├── raw/                    # untouched downloads + metadata.json
│   ├── processed/aqi_14day.csv
│   └── sample/DEMO_ONLY.csv    # clearly flagged demo data
├── src/airaware/
│   ├── __init__.py
│   ├── ingest.py
│   ├── clean.py
│   ├── validate.py
│   ├── aqi.py
│   ├── stats.py
│   ├── alerts.py
│   ├── charts.py
│   └── health.py
├── app/streamlit_app.py
├── reports/
│   ├── build_figures.py
│   └── report_outline.md
├── notebooks/analysis.ipynb
├── tests/
│   ├── test_aqi.py
│   ├── test_stats.py
│   ├── test_validate.py
│   └── test_alerts.py
└── outputs/figures/
```

## 8. Data schema (`aqi_14day.csv`)

| Column | Type | Notes |
|---|---|---|
| date | date | consecutive, ascending |
| station | str | exact CPCB station name |
| city | str | Bengaluru |
| aqi_reported | float | from CPCB |
| aqi_category | str | from CPCB, re-derived and compared |
| pm25 | float | µg/m³, may be NaN |
| pm10 | float | µg/m³, may be NaN |
| prominent_pollutant_reported | str | if CPCB provides it |
| source | str | "CPCB …" |
| accessed_on | date | actual access date |

Derived columns: `subindex_pm25`, `subindex_pm10`, `aqi_from_pm`, `dominant_pm`, `category_derived`, `category_match`, `exceeds_naaqs_pm25`, `exceeds_who_pm25`, `data_quality_flag`.

## 9. Analytics specification

1. **Descriptive stats**: mean, max (with date), min (with date), median, std. Use sample values, and show the formula and the Excel equivalent.
2. **Category counts**: all six categories, including zeros. Count must total 14 (or total valid days; state clearly).
3. **Dominant pollutant**: per day, compare `subindex_pm25` and `subindex_pm10` (and gases if available). Count days per pollutant. Report as "dominant on X of 14 days".
4. **Exceedance days**: days above NAAQS and WHO limits for PM2.5 and PM10.
5. **PM2.5 / PM10 ratio**: a high ratio hints at combustion/secondary particles; a low ratio hints at coarse dust. Present as a hint only.
6. **Trend note**: simple 3-day rolling mean. Say that 14 days is too short for any trend claim.

## 10. Alert engine specification (the "wow" for part d)

```
Levels: INFO (Satisfactory) → ADVISORY (Moderate) → WARNING (Poor)
        → DANGER (Very Poor) → EMERGENCY (Severe)
Rules:
  - Alert level derived from validated AQI category.
  - Suppress if last valid reading older than stale_limit_hours.
  - Upgrade immediately; downgrade only after AQI falls
    `hysteresis` points below the lower bound of the current level.
  - Every alert shows: station, reading time, AQI, category, dominant
    pollutant, health advice, data source.
Backtest:
  - Replay the 14 real days through the engine.
  - Output: alert log (day, level, message), number of alerts,
    days with alert, flip-flops avoided by hysteresis.
```

Health advice text must come from CPCB category wording, not from your own medical claims.

## 11. Dashboard pages (Streamlit)

1. **Overview**: latest AQI card with category colour, dominant pollutant, station, reading date, data-quality badge.
2. **14-Day Trend**: line chart of daily AQI with category colour bands. Required chart #1.
3. **Category Counts**: bar chart. Required chart #2.
4. **Pollutants**: PM2.5 and PM10 lines with NAAQS and WHO limit lines; dominant-pollutant donut/bar.
5. **Data Quality**: missing values, validation results, AQI-from-PM check.
6. **Alert Simulator**: slider for AQI / replay of the 14 days with the alert log.
7. **Actions and Policy**: 4 measures, NCAP and SDG 11 mapping.
8. **Download**: processed CSV and figures.

Accessibility: colour plus text labels for categories, mobile-friendly layout.

## 12. Four measures, linked to evidence

Choose the emphasis based on **your** result:

| Measure | Target pollutant | Link to your findings |
|---|---|---|
| Public transport and traffic management | PM2.5, NO₂ | If PM2.5 dominates / ratio high |
| Road and construction dust control | PM10 | If PM10 dominates / ratio low |
| Industrial and generator emission enforcement | PM2.5, SO₂ | Stations near industrial zones |
| Green infrastructure plus denser monitoring | all | Station-level gaps; trees complement, not replace, source reduction |

Add one sentence per measure on **how AirAware would measure the effect** (e.g. compare future 14-day means to this baseline).

## 13. NCAP and SDG 11 section (outline)

- **NCAP**: national programme for city clean-air action plans focused on monitoring, source apportionment and PM reduction targets. Explain how AirAware supports *monitoring, public information, and evaluating interventions*. Check the current NCAP target wording on the official MoEFCC/PIB pages and cite it with access date.
- **SDG 11 (Sustainable Cities and Communities)**: connect to Target 11.6 (reducing the adverse per-capita environmental impact of cities, with special attention to air quality). Verify wording on the UN SDG site.

## 14. Report structure (6–8 pages)

| Page | Content |
|---|---|
| 1 | Title, aim, objectives, AQI introduction |
| 2 | Method and architecture diagram, data source and station |
| 3 | Table (a): 14 days data with source line |
| 4 | Statistics (b): formulas, Excel and Python results, category count table |
| 5 | Charts: daily AQI line chart, category bar chart |
| 6 | (c): categories and health effects, dominant-pollutant analysis, limitations |
| 7 | (d): AirAware design, alert backtest, screenshots, 4 measures |
| 8 | NCAP, SDG 11, conclusion, references, GitHub link / appendix |

Add a one-page appendix: validation results and limitations.

## 15. Timeline (5 working sessions)

| Session | Goal | Done when |
|---|---|---|
| 1 | Pick station, download real 14-day data, fill table in Excel | Table complete with sources |
| 2 | Build `aqi.py`, `stats.py`, tests | Python results match Excel |
| 3 | Charts, dominant pollutant, validation | Figures exported |
| 4 | Streamlit app, alert engine and backtest | App runs end to end |
| 5 | Write report, screenshots, rehearse viva | PDF ready |

## 16. Viva questions to prepare

1. Why is AQI the max of the sub-indices, not the average?
2. Why do PM2.5 and PM10 use 24-hour averages?
3. What if the data has missing days? (Show how you handled it.)
4. Why can your PM-only AQI be lower than the published AQI but not higher?
5. Why shouldn't you say the cause of a spike from 14 days of data?
6. How does hysteresis help the alert system?
7. How would you scale this to all stations or real-time?
8. What are the limitations of one station representing a city?

---

# 17. PROMPT FOR YOUR IDE (copy everything inside the box)

````
You are a senior Python data engineer and environmental-analytics developer. Build the project "AirAware Bengaluru" in this repository following PLAN.md exactly. Work step by step, run the tests after each step, and explain what you did briefly.

CONTEXT
University assignment (BCV755B, CSE): collect 14 days of AQI, PM2.5, PM10 for one Bengaluru CPCB station; compute mean/max/min AQI and category counts; draw a line chart of daily AQI and a bar chart of category counts; explain AQI categories and health effects and identify the main pollutant; propose an app/dashboard with alerts, four city measures, and NCAP / SDG 11 links.

HARD RULES
1. Never fabricate or interpolate missing readings. Missing = NaN, shown as "unavailable".
2. Any sample data must live in data/sample/DEMO_ONLY.csv and the UI must show a red "DEMO DATA" banner whenever it is loaded.
3. All AQI breakpoints, categories and alert thresholds go in YAML under config/. No magic numbers in code.
4. Overall AQI = max of pollutant sub-indices (linear interpolation between breakpoints). Never average.
5. Use pure functions, type hints, docstrings, and pytest tests.
6. Do not claim causes of pollution from 14 days of data. Use "possible contributing sources".

STEP 1 – Scaffold
Create the structure in PLAN.md section 7, requirements.txt (pandas, numpy, matplotlib, plotly, streamlit, pyyaml, pytest, python-docx or reportlab optional), and README.md with setup/run instructions.

STEP 2 – Config
config/breakpoints.yaml: PM2.5 and PM10 24-h breakpoints from PLAN.md section 5.3, with a comment saying "verify against CPCB document".
config/categories.yaml: six CPCB categories with ranges, colours (accessible), and short CPCB-style health text.
config/alerts.yaml: levels, hysteresis (default 10 AQI points), stale_limit_hours (default 36).

STEP 3 – Core logic (src/airaware/)
- aqi.py: subindex(pollutant, conc), aqi_from_pollutants(dict) -> (aqi, dominant), categorize(aqi).
- clean.py: load CSV, enforce schema/types, parse dates, sort, keep raw untouched, write data/processed/aqi_14day.csv.
- validate.py: check exactly 14 consecutive days (report gaps), duplicates, negative or implausible values, units, and the rule aqi_reported >= aqi_from_pm (flag violations). Output a data-quality report (dict + markdown).
- stats.py: mean, max+date, min+date, median, std, category counts for all six categories (zeros included), dominant-pollutant counts, NAAQS and WHO exceedance days, PM2.5/PM10 ratio.
- health.py: map category -> health advice text from config.
- alerts.py: AlertEngine with levels, stale-data guard, hysteresis; method replay(df) returning an alert log DataFrame and summary (alerts raised, flip-flops avoided).
- charts.py: daily AQI line chart with category colour bands; category-count bar chart; PM2.5/PM10 chart with NAAQS and WHO lines; dominant pollutant chart. Export 300-dpi PNGs to outputs/figures/ with clear axis labels, titles, and source footnote.

STEP 4 – Tests (pytest)
- test_aqi.py: boundary values (30/31, 60/61, 90/91 for PM2.5; 50/51, 100/101, 250/251 for PM10), max-not-average rule, categories at 50/51, 100/101, 200/201.
- test_stats.py: hand-computed mean/max/min and category counts on a small fixture.
- test_validate.py: missing day, duplicate day, aqi_reported < aqi_from_pm flagged.
- test_alerts.py: stale data suppresses alert, hysteresis prevents flip-flop, upgrade is immediate.

STEP 5 – Streamlit app (app/streamlit_app.py)
Pages per PLAN.md section 11 (Overview, 14-Day Trend, Category Counts, Pollutants, Data Quality, Alert Simulator, Actions and Policy, Download). Cache data loading. Show station name, date range, source and access date on every page. Show DEMO banner when sample data is used.

STEP 6 – Report helpers
reports/build_figures.py regenerates all figures and a stats summary markdown (reports/summary.md) containing the numbers and sentences for the report: mean/max/min, category table, dominant-pollutant sentence in the template: "During the observation period, ___ was identified as the dominant pollutant on ___ of 14 days. Possible contributing sources include ___."

STEP 7 – Quality
Run pytest, fix failures, run a linter (ruff), make sure `streamlit run app/streamlit_app.py` works from a clean clone with the README steps, and print a final checklist of what is done and what the user must still do manually (download real CPCB data, fill station/access date, verify breakpoints).

Start with STEP 1 now.
````

---

# 18. Final submission checklist

- [ ] Real data from one CPCB Bengaluru station, 14 consecutive days
- [ ] Station name, access date and source under every table and figure
- [ ] Excel formulas and Python results match
- [ ] Both required charts with labelled axes and titles
- [ ] Category table includes all six categories (zeros shown)
- [ ] Dominant pollutant counted from data, not assumed
- [ ] Limitations paragraph included
- [ ] Alert backtest screenshot and log
- [ ] 4 measures linked to your findings, NCAP and SDG 11 cited from official pages
- [ ] Demo data removed or clearly labelled
- [ ] Tests pass, README works, code link or appendix included
