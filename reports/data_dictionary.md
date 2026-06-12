# Data Dictionary — Bluestock Mutual Fund Capstone

**Project:** Bluestock MF Analytics Capstone  
**Database:** `bluestock_mf.db` (SQLite)  
**Schema version:** 2.0 (Day 2)  
**Last updated:** 2024-04-01  
**Owner:** Bluestock Analytics Team

---

## Overview

The database follows a **star schema** with 3 dimension tables and 6 fact tables,
covering 20 AMFI-registered mutual fund schemes across 5 financial years (FY 2019–20 to FY 2023–24).

### Entity Relationship Summary

```
dim_investor ──┐
dim_date ──────┼──► fact_transactions
dim_fund ──────┘
               ├──► fact_nav
               ├──► fact_performance
               ├──► fact_portfolio_holdings
               ├──► fact_dividends
               └──► fact_benchmark  (no FK — standalone benchmark)
```

---

## Dimension Tables

### `dim_fund`

**Business definition:** Master register of AMFI-approved mutual fund schemes. One row per scheme. Updated when SEBI approves new NFOs or scheme mergers.

**Source:** AMFI scheme master + Value Research fund attributes  
**Row count:** 20  
**Primary key:** `amfi_code`

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `amfi_code` | INTEGER | No | `125497` | 6-digit unique scheme identifier assigned sequentially by AMFI. Lower codes = older registrations. Used across all AMFI data feeds. |
| `scheme_name` | TEXT | No | `HDFC Top 100 Fund - Direct Plan - Growth` | Full SEBI-registered scheme name including plan (Direct/Regular) and option (Growth/IDCW). |
| `fund_house` | TEXT | No | `HDFC Mutual Fund` | Asset Management Company (AMC) operating the scheme. Regulated by SEBI under the SEBI (MF) Regulations 1996. |
| `category` | TEXT | No | `Equity` | SEBI macro-category: `Equity`, `Debt`, or `Hybrid`. Determines applicable regulation and investor risk suitability. |
| `sub_category` | TEXT | No | `Large Cap` | SEBI sub-classification within category. E.g. Large Cap funds must invest ≥80% in top-100 stocks by market cap. |
| `risk_grade` | TEXT | No | `Moderately High` | SEBI Risk-o-Meter label (6-tier scale). Mandatory disclosure on all scheme documents. Values: `Low`, `Low to Moderate`, `Moderate`, `Moderately High`, `High`, `Very High`. |
| `aum_cr` | REAL | Yes | `4917.0` | Assets Under Management in **₹ Crore** (scheme-level, not AMC total). 1 Crore = 10 million INR. Used for AUM-weighted calculations. |
| `expense_ratio_pct` | REAL | Yes | `0.63` | Total Expense Ratio as % per annum, capped by SEBI at 2.25% (equity) and 2.00% (debt) for regular plans. Direct plans are lower by ~0.5–1%. |
| `launch_date` | TEXT | Yes | `2015-10-08` | Date the scheme was first offered to investors (NFO allotment date). ISO 8601 format YYYY-MM-DD. |
| `benchmark` | TEXT | Yes | `NIFTY 100 TRI` | Primary performance benchmark index. Large-cap equity funds benchmark against NIFTY 100 TRI or BSE 100 TRI. TRI = Total Return Index (includes dividends). |

**Business rules:**
- `expense_ratio_pct` must be between 0.10% and 2.50% (SEBI caps, with tolerance for legacy schemes)
- `aum_cr` is refreshed monthly from AMFI AUM disclosure
- Direct plans always have lower `expense_ratio_pct` than the corresponding Regular plan of the same scheme

---

### `dim_date`

**Business definition:** Standard calendar dimension enabling time-based slicing, financial year grouping, and BI tool calendar hierarchies.

**Source:** Generated (pandas `date_range`)  
**Row count:** 2,557 (2019-01-01 to 2025-12-31)  
**Primary key:** `date_id`

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `date_id` | INTEGER | No | `20240401` | Surrogate key in YYYYMMDD format. Integer for fast joins and range predicates. |
| `full_date` | TEXT | No | `2024-04-01` | ISO 8601 date string. Unique — use for human-readable display. |
| `year` | INTEGER | No | `2024` | Calendar year (Gregorian). |
| `quarter` | INTEGER | No | `1` | Calendar quarter (1–4). Q1 = Jan–Mar (note: differs from Indian FY). |
| `quarter_label` | TEXT | No | `Q1-2024` | Formatted quarter for reports and chart axes. |
| `month` | INTEGER | No | `4` | Calendar month number (1–12). |
| `month_name` | TEXT | No | `April` | Full month name for display. |
| `week` | INTEGER | No | `14` | ISO 8601 week number (1–53). |
| `day_of_week` | INTEGER | No | `0` | Day of week: 0 = Monday, 6 = Sunday (Python convention). |
| `day_name` | TEXT | No | `Monday` | Full weekday name for display. |
| `is_weekday` | INTEGER | No | `1` | 1 = Mon–Fri trading day candidate; 0 = weekend. Does NOT account for NSE holidays. |
| `fy_year` | INTEGER | No | `2025` | **Indian financial year end** (Apr–Mar). FY 2024–25 has fy_year = 2025. |
| `fy_label` | TEXT | No | `FY24-25` | Short financial year label used in AMFI reports and SEBI filings. |

---

### `dim_investor`

**Business definition:** KYC-verified investor master. One row per unique investor ID registered with the AMC.

**Source:** Investor onboarding records  
**Row count:** 200  
**Primary key:** `investor_id`

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `investor_id` | TEXT | No | `INV0001` | Internal investor reference code. Maps to PAN in production but anonymised here for data privacy. |
| `age` | INTEGER | Yes | `35` | Investor age in years at registration. SEBI mandates minimum age 18 for direct investment. |
| `city` | TEXT | Yes | `Hyderabad` | Investor's city of residence as declared in KYC. Used for geographic distribution analysis. |
| `risk_profile` | TEXT | Yes | `Moderate` | Self-declared risk appetite from KYC questionnaire. Values: `Conservative`, `Moderate`, `Aggressive`. Used for suitability checks against scheme risk grade. |
| `annual_income_lakh` | REAL | Yes | `12.5` | Self-declared annual income in **₹ Lakh** (1 Lakh = 100,000 INR). Used for investment limit compliance (SIP caps for certain categories). |
| `kyc_status` | TEXT | Yes | `Verified` | KYC completion status per CERSAI/KRA records. Values: `Verified`, `Pending`, `Rejected`, `Expired`. Only `Verified` investors may transact. |
| `registration_date` | TEXT | Yes | `2020-06-15` | Date investor was onboarded to the AMC platform. ISO 8601 YYYY-MM-DD. |

---

## Fact Tables

### `fact_nav`

**Business definition:** Daily Net Asset Value (NAV) per scheme. NAV = (total assets - liabilities) / units outstanding. Forward-filled for non-trading days (weekends, NSE holidays) using the previous business day's NAV per SEBI practice.

**Source:** mfapi.in live API + historical AMFI NAV data  
**Row count:** 26,100 (20 schemes × ~1,305 business days)  
**Grain:** One row per (scheme, trading date)  
**Primary key:** `nav_id` (auto-increment)  
**Foreign keys:** `amfi_code → dim_fund`, `date_id → dim_date`

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `nav_id` | INTEGER | No | `1` | Auto-increment surrogate key. |
| `amfi_code` | INTEGER | No | `125497` | FK to `dim_fund`. Identifies the scheme. |
| `date_id` | INTEGER | No | `20240401` | FK to `dim_date`. Join key for time-based analysis. |
| `nav_date` | TEXT | No | `2024-04-01` | Denormalised date string for readability in direct queries. |
| `nav` | REAL | No | `912.4823` | NAV in **₹ per unit**. Always > 0. Used as the base for all return calculations. CAGR must use 252 trading days, not calendar days. |

**Business rules:**
- `nav` must be > 0 at all times
- Forward-fill applied: if NAV for date D is missing, carry forward NAV from D-1
- Returns calculated as: `(nav_t / nav_t-n)^(252/n_days) - 1` (annualised)
- Never use calendar days for annualisation — always 252 trading-day convention

---

### `fact_transactions`

**Business definition:** Unified ledger of all investor transactions. Combines SIP instalments, lump-sum purchases, and redemptions. This is the primary fact table for AUM flow analysis and cohort studies.

**Source:** Merged from `sip_transactions.csv` + `lumpsum_transactions.csv`  
**Row count:** 6,466 (5,941 SIP + 500 Lumpsum + ~25 Redemption)  
**Grain:** One row per transaction event  
**Primary key:** `txn_id`  
**Foreign keys:** `investor_id → dim_investor`, `amfi_code → dim_fund`, `date_id → dim_date`

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `txn_id` | INTEGER | No | `1001` | Sequential transaction identifier. |
| `investor_id` | TEXT | No | `INV0042` | FK to `dim_investor`. |
| `amfi_code` | INTEGER | No | `119551` | FK to `dim_fund`. Target scheme of the transaction. |
| `date_id` | INTEGER | No | `20220315` | FK to `dim_date`. |
| `transaction_date` | TEXT | No | `2022-03-15` | Date of transaction settlement (T+1 for equity, same-day for liquid). |
| `transaction_type` | TEXT | No | `SIP` | Transaction classification. Values: `SIP` (Systematic Investment Plan instalment), `Lumpsum` (one-time purchase), `Redemption` (withdrawal). |
| `amount` | REAL | No | `5000.0` | Transaction amount in **₹**. Positive for purchases (SIP/Lumpsum); **negative for Redemptions** (cash outflow from scheme). |
| `nav_at_purchase` | REAL | No | `312.45` | Applicable NAV on transaction date. Used to compute `units_allotted`. |
| `units_allotted` | REAL | No | `15.9972` | Units credited or debited: `amount / nav_at_purchase`. Negative for Redemptions. |

**Business rules:**
- `amount > 0` for SIP and Lumpsum; `amount < 0` for Redemptions
- `units_allotted = amount / nav_at_purchase` (enforced at ingestion)
- SEBI minimum SIP: ₹100 per instalment
- Only investors with `kyc_status = 'Verified'` may transact (validated at application layer)

---

### `fact_performance`

**Business definition:** Scheme-level return and risk metrics snapshot. Refreshed monthly. Used for fund comparison tables, regulator SEBI disclosures, and the recommender engine.

**Source:** Merged from `returns_summary.csv` + `risk_metrics.csv` + `fund_master.csv`  
**Row count:** 20 (one per scheme)  
**Grain:** Latest performance snapshot per scheme  
**Primary key:** `amfi_code`

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `amfi_code` | INTEGER | No | `125497` | PK + FK to `dim_fund`. |
| `scheme_name` | TEXT | Yes | — | Denormalised for standalone queries. |
| `fund_house` | TEXT | Yes | — | Denormalised AMC name. |
| `return_1y_pct` | REAL | Yes | `14.23` | Trailing 12-month return %. Point-to-point: `(nav_today / nav_1yr_ago - 1) × 100`. |
| `return_3y_cagr_pct` | REAL | Yes | `11.87` | 3-year Compound Annual Growth Rate. Formula: `(nav_t / nav_t-3y)^(252/756) - 1`. NULL for schemes < 3 years old. |
| `return_5y_cagr_pct` | REAL | Yes | `9.42` | 5-year CAGR. NULL for schemes < 5 years old. |
| `sharpe_ratio` | REAL | Yes | `0.8731` | Risk-adjusted return: `(annualised_return - Rf) / annualised_std`. Rf = 6% p.a. (10-yr G-sec yield proxy). Higher is better. |
| `annualised_volatility_pct` | REAL | Yes | `18.45` | Annualised standard deviation of daily returns: `daily_std × √252 × 100`. Measures total risk. |
| `var_95_daily_pct` | REAL | Yes | `-1.92` | Historical 5th-percentile daily return (Value at Risk at 95% confidence). Negative = potential one-day loss. |
| `max_drawdown_pct` | REAL | Yes | `-31.2` | Maximum peak-to-trough decline over the observation period. Negative value. Deeper drawdown = higher downside risk. |
| `beta` | REAL | Yes | `0.92` | Covariance of fund daily returns with NIFTY 100 TRI / variance of benchmark. Beta = 1 → moves with market; < 1 → defensive; > 1 → aggressive. |
| `expense_ratio_pct` | REAL | Yes | `0.63` | Denormalised from `dim_fund`. |
| `is_anomaly` | INTEGER | No | `0` | Flag: 1 if any metric exceeds anomaly threshold (|1Y return| > 100%, |Sharpe| > 3, |beta| > 2). Exclude anomalous rows from ranking queries. |

---

### `fact_portfolio_holdings`

**Business definition:** Stock-level portfolio composition of each fund at the latest available disclosure date. SEBI mandates monthly portfolio disclosure by the 10th of the following month.

**Source:** `portfolio_holdings.csv`  
**Row count:** 174  
**Grain:** One row per (fund, stock)  
**Primary key:** `holding_id` (auto-increment)

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `holding_id` | INTEGER | No | `1` | Auto-increment PK. |
| `amfi_code` | INTEGER | No | `125497` | FK to `dim_fund`. |
| `stock_symbol` | TEXT | No | `RELIANCE` | NSE ticker symbol in uppercase. |
| `weight_pct` | REAL | No | `8.42` | Stock's weight as % of total portfolio AUM. All weights per fund sum to ~100%. |
| `market_value_cr` | REAL | No | `412.5` | Market value of holding in **₹ Crore** at disclosure date. |

---

### `fact_dividends`

**Business definition:** Per-unit dividend declarations under the IDCW (Income Distribution cum Capital Withdrawal) option. Post-2021 SEBI mandate, "dividend" option is renamed to IDCW.

**Source:** `dividend_history.csv`  
**Row count:** 160  
**Grain:** One row per (scheme, declaration date)

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `dividend_id` | INTEGER | No | `1` | Auto-increment PK. |
| `amfi_code` | INTEGER | No | `125497` | FK to `dim_fund`. |
| `dividend_date` | TEXT | No | `2023-06-15` | Record date of dividend declaration (YYYY-MM-DD). |
| `dividend_per_unit` | REAL | No | `2.50` | Amount declared per unit in **₹**. Reduces NAV by this amount on ex-dividend date. |
| `dividend_type` | TEXT | Yes | `Per Unit` | `Per Unit` (fixed ₹ per unit) or `Percentage` (% of face value, used by some debt funds). |

---

### `fact_benchmark`

**Business definition:** Daily values of the NIFTY 100 Total Return Index — the primary benchmark for all large-cap and flexi-cap funds in this dataset. TRI includes dividend reinvestment, making it a fair comparison against Growth option NAVs.

**Source:** `benchmark_nifty100.csv`  
**Row count:** 1,305  
**Grain:** One row per trading day

| Column | SQL Type | Nullable | Example | Business Definition |
|--------|----------|----------|---------|---------------------|
| `benchmark_id` | INTEGER | No | `1` | Auto-increment PK. |
| `date` | TEXT | No | `2024-04-01` | Trading date (YYYY-MM-DD). |
| `nifty100_tri` | REAL | No | `24312.87` | NIFTY 100 Total Return Index value. Base = 1,000 as of Jan 1, 1996. Used to compute beta and alpha vs benchmark. |

---

## Processed CSV Files (`data/processed/`)

| File | Source Tables | Rows | Description |
|------|--------------|------|-------------|
| `nav_history_clean.csv` | `fact_nav` | 26,100 | Sorted, deduped, forward-filled NAV |
| `fund_master_clean.csv` | `dim_fund` | 20 | Validated fund attributes |
| `investor_transactions_clean.csv` | `fact_transactions` | 6,466 | Merged SIP + Lumpsum + Redemption |
| `scheme_performance_clean.csv` | `fact_performance` | 20 | Returns + risk + anomaly flag |
| `investor_profiles_clean.csv` | `dim_investor` | 200 | Validated KYC and demographics |
| `portfolio_holdings_clean.csv` | `fact_portfolio_holdings` | 174 | Validated holdings weights |
| `benchmark_nifty100_clean.csv` | `fact_benchmark` | 1,305 | Deduped benchmark index values |
| `dividend_history_clean.csv` | `fact_dividends` | 160 | Validated dividend declarations |
| `dim_date_clean.csv` | `dim_date` | 2,557 | Full calendar dimension 2019–2025 |

---

## Key Business Rules & Conventions

| Rule | Detail |
|------|--------|
| **Currency** | All monetary values in **₹ (Indian Rupee)**. AUM in Crore (Cr), individual amounts in absolute ₹. |
| **Annualisation** | Always use **252 trading days** per year, never 365 calendar days, for CAGR and volatility. |
| **Forward-fill** | Missing NAV on weekends/holidays → carry forward last known NAV (`ffill()` after `reindex` to business-day calendar). |
| **Risk-free rate** | Sharpe ratio uses **6% p.a.** as proxy for 10-year Indian G-sec yield. Convert to daily: `(1.06)^(1/252) - 1`. |
| **Redemption sign** | `amount` and `units_allotted` are **negative** for Redemptions. |
| **Anomaly threshold** | |1Y return| > 100%, |Sharpe| > 3, or |beta| > 2 → `is_anomaly = 1`. Exclude from ranking queries. |
| **SEBI expense cap** | Direct plans: equity ≤ 1.05%, debt ≤ 0.80% (post-October 2023 SEBI circular). |
| **KYC gate** | Only `kyc_status = 'Verified'` investors are eligible to transact (enforced at app layer, not DB). |
| **AUM units** | `aum_cr` is scheme-level AUM in **₹ Crore**. Never confuse with total AMC AUM (sum of all schemes). |

---

## Glossary

| Term | Definition |
|------|-----------|
| **AMFI** | Association of Mutual Funds in India — industry body, maintains scheme master and publishes daily NAV |
| **AMC** | Asset Management Company — the fund manager entity (e.g. HDFC AMC) |
| **NAV** | Net Asset Value — price per unit of a mutual fund scheme |
| **TRI** | Total Return Index — benchmark index variant that reinvests dividends |
| **SIP** | Systematic Investment Plan — recurring fixed-amount investment on a set date |
| **IDCW** | Income Distribution cum Capital Withdrawal — formerly called "Dividend" option |
| **CAGR** | Compound Annual Growth Rate — annualised return over multi-year periods |
| **Sharpe Ratio** | (Return − Risk-free rate) / Std Dev — risk-adjusted return metric |
| **Beta** | Sensitivity of fund returns relative to benchmark; 1.0 = moves in lockstep with market |
| **VaR** | Value at Risk — worst expected loss at a given confidence level over one period |
| **Max Drawdown** | Largest peak-to-trough decline in NAV over the observation window |
| **NFO** | New Fund Offer — initial subscription period when a new scheme is launched |
| **Direct Plan** | Scheme variant purchased directly from AMC, without distributor commission |
| **Growth Option** | All returns are reinvested back into the NAV; no periodic payouts |
