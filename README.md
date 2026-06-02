# Bluestock Mutual Fund Analytics Capstone

A full-stack data engineering and analytics project covering 20 mutual fund schemes across 5 years of NAV history. Includes ETL pipelines, SQLite database, EDA, performance analytics, and an interactive dashboard.

## Project Structure

```
bluestock_mf_capstone/
├── data/
│   ├── raw/           ← original CSV downloads + live API JSON
│   ├── processed/     ← cleaned, validated CSVs
│   └── db/            ← bluestock_mf.db (NOT committed; see schema.sql)
├── notebooks/
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_eda_analysis.ipynb
│   ├── 04_performance_analytics.ipynb
│   └── 05_advanced_analytics.ipynb
├── scripts/
│   ├── data_ingestion.py      ← D1 ETL pipeline
│   ├── live_nav_fetch.py      ← D1 live NAV from mfapi.in
│   ├── etl_pipeline.py        ← D2 SQLite loader
│   ├── compute_metrics.py     ← D4 Sharpe / Beta / VaR
│   └── recommender.py         ← D6 fund recommender
├── sql/
│   ├── schema.sql             ← DB schema (committed)
│   └── queries.sql            ← analytical queries
├── dashboard/                 ← Power BI / Streamlit artifacts
├── reports/                   ← Final report PDF + PPTX
└── requirements.txt
```

## Quick Start

```bash
git clone 
cd bluestock_mf_capstone
pip install -r requirements.txt

# Day 1 — Data Ingestion
python scripts/data_ingestion.py

# Fetch live NAV (requires internet)
python scripts/live_nav_fetch.py

# Full ETL + SQLite load
python scripts/etl_pipeline.py
```

## Data Sources

| Source | Description |
|--------|-------------|
| [mfapi.in](https://api.mfapi.in) | Live NAV for all AMFI-registered schemes |
| AMFI / Value Research | Fund master, NAV history, portfolio holdings |

## Key Schemes Tracked

| AMFI Code | Scheme |
|-----------|--------|
| 125497 | HDFC Top 100 Direct Growth |
| 119551 | SBI Bluechip Direct Growth |
| 120503 | ICICI Pru Bluechip Direct Growth |
| 118632 | Nippon India Large Cap Direct Growth |
| 119092 | Axis Bluechip Direct Growth |
| 120841 | Kotak Bluechip Direct Growth |

## Deliverables

| ID | Deliverable | Format | Weight |
|----|-------------|--------|--------|
| D1 | ETL pipeline | `.py` | 15% |
| D2 | SQLite database | `.db` | 10% |
| D3 | EDA notebook | `.ipynb` | 15% |
| D4 | Performance metrics | `.ipynb` + CSVs | 15% |
| D5 | Interactive dashboard | `.pbix` / `.twbx` | 20% |
| D6 | Advanced analytics | `.ipynb` | 10% |
| D7 | Final report + slides | `.pdf` + `.pptx` | 15% |

## Important Notes

- ⚠️ NAV data uses **trading days only** — always `ffill()` after reindexing
- ⚠️ CAGR is annualised using **252 trading days**, not calendar days
- ⚠️ AUM is in **₹ Crore** (column: `aum_cr`)
- ⚠️ `.db` files are **not committed** — use `sql/schema.sql` to recreate

## License

MIT
