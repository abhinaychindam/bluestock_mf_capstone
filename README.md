# Bluestock Mutual Fund Analytics Capstone

A full-stack data engineering and analytics project covering 20 mutual fund schemes across 5 years of NAV history. Includes ETL pipelines, SQLite database, EDA, performance analytics, and an interactive dashboard.

# #Overview

The Bluestock Mutual Fund Analytics Platform is a fintech-focused data analytics project designed to automate the collection, processing, analysis, and visualization of mutual fund data. The system follows an end-to-end data engineering and analytics workflow, transforming raw mutual fund datasets into actionable investment insights.

The project demonstrates real-world financial analytics concepts including ETL pipelines, risk analysis, performance measurement, predictive modeling, portfolio analytics, and business intelligence dashboarding.

# Project Objectives:

Build an automated ETL pipeline for mutual fund datasets.
Clean and standardize financial data from multiple sources.
Store processed data in a structured database.
Generate key mutual fund performance metrics.
Perform risk and return analysis.
Develop predictive models for NAV forecasting.
Create interactive Power BI dashboards.
Deliver actionable insights for investors and fund managers.


**Key Features**
# Data Engineering
    Automated data ingestion pipeline
    Data cleaning and validation
    Schema standardization
    Database integration
    Incremental updates
# Financial Analytics
    CAGR Calculation
    Annualized Returns
    Volatility Analysis
    Sharpe Ratio
    Sortino Ratio
    Maximum Drawdown
    Rolling Returns
    Risk-Adjusted Performance Metrics
# Advanced Analytics
    Historical VaR (Value at Risk)
    Conditional VaR (CVaR)
    Rolling Sharpe Analysis
    Fund Ranking Engine
    Category Performance Comparison
    SIP Performance Analysis
# Machine Learning
    NAV Forecasting
    Time Series Analysis
    Trend Detection
    Future Return Prediction
# Business Intelligence
    Interactive Power BI Dashboard
    Fund Performance Monitoring
    Risk Monitoring Dashboard
    Portfolio Insights
    Investor Reporting

**Project Architecture**

Raw Data Sources
↓
Data Ingestion
↓
Data Cleaning & Validation
↓
Feature Engineering
↓
Database Storage
↓
Analytics Engine
↓
Machine Learning Models
↓
Power BI Dashboard
↓
Investor Insights

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


**Dataset Description**

# Fund Master Data

Contains metadata for mutual funds including:

Scheme Name
AMC Name
Category
Fund House
Launch Date
NAV History

Contains historical Net Asset Values:

Date
Scheme Code
NAV
Daily Return
AUM Data

Tracks Assets Under Management:

Fund House
AUM Value
Reporting Period
SIP Inflow Data

Monthly SIP contribution statistics.

Category Inflow Data

Investment flow across fund categories.

# Technology Stack
Programming
Python 3.11+

Data Processing
Pandas
NumPy

Visualization
Matplotlib
Seaborn
Power BI

Machine Learning
Scikit-Learn
Statsmodels

Database
SQLite

Development
Jupyter Notebook
VS Code
Git


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

## Execution
python run_pipeline.py
streamlit run app.py
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



** Financial Metrics Computed**

# Return Metrics
Daily Return
Monthly Return
Annual Return
CAGR

# Risk Metrics
Volatility
Maximum Drawdown
Value at Risk (VaR)
Conditional VaR (CVaR)

# Risk Adjusted Metrics
Sharpe Ratio
Sortino Ratio
Calmar Ratio

**Dashboard KPIs**

# The Power BI dashboard tracks:

Total Mutual Funds
Average NAV
Total AUM
Best Performing Fund
Worst Performing Fund
SIP Trends
Category-wise Performance
Fund House Comparison
Risk Distribution

# Future Enhancements

Real-time NAV Integration
Portfolio Optimization
Monte Carlo Simulation
Markowitz Efficient Frontier
Automated Email Reporting
Streamlit Web Application
Investor Recommendation Engine
AI-powered Fund Ranking System

# Business Impact

This project demonstrates how financial institutions can leverage data analytics and machine learning to:

Improve investment decision-making
Monitor fund performance
Assess investment risk
Generate investor insights
Automate reporting workflows

## License
**Author**
@abhinaychindam

Bluestock Fintech Mutual Fund Analytics Capstone Project

Developed as an end-to-end financial data engineering, analytics, and visualization solution.