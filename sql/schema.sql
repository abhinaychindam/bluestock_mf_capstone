-- database: ../data/db/bluestock_mf.db
-- =============================================================================
-- schema.sql — Bluestock MF Capstone Star Schema
-- Database: SQLite (bluestock_mf.db)
-- Last updated: 2024-04-01
--
-- Star schema overview
--   Dimensions : dim_fund, dim_date, dim_investor
--   Facts       : fact_nav, fact_transactions, fact_performance,
--                 fact_portfolio_holdings, fact_dividends, fact_benchmark
-- =============================================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode  = WAL;     -- better concurrent read performance


-- =============================================================================
-- DIMENSION: dim_fund
-- One row per AMFI-registered mutual fund scheme.
-- Grain: scheme (amfi_code)
-- =============================================================================
CREATE TABLE IF NOT EXISTS dim_fund (
    amfi_code           INTEGER     PRIMARY KEY,        -- 6-digit AMFI scheme code
    scheme_name         TEXT        NOT NULL,           -- Full SEBI-registered scheme name
    fund_house          TEXT        NOT NULL,           -- AMC / Asset Management Company
    category            TEXT        NOT NULL,           -- SEBI category: Equity / Debt / Hybrid
    sub_category        TEXT        NOT NULL,           -- Sub-category: Large Cap, Liquid, etc.
    risk_grade          TEXT        NOT NULL            -- SEBI risk-o-meter: Low → Very High
                        CHECK (risk_grade IN (
                            'Low','Low to Moderate','Moderate',
                            'Moderately High','High','Very High'
                        )),
    aum_cr              REAL,                           -- AUM in ₹ Crore (scheme-level)
    expense_ratio_pct   REAL                            -- Annual expense ratio in %
                        CHECK (expense_ratio_pct BETWEEN 0.1 AND 2.5),
    launch_date         TEXT,                           -- Scheme launch date (YYYY-MM-DD)
    benchmark           TEXT                            -- Primary benchmark index
);

CREATE INDEX IF NOT EXISTS idx_fund_house ON dim_fund (fund_house);
CREATE INDEX IF NOT EXISTS idx_fund_category ON dim_fund (category, sub_category);


-- =============================================================================
-- DIMENSION: dim_date
-- Calendar dimension for date-based slicing and BI tools.
-- Grain: calendar day
-- =============================================================================
CREATE TABLE IF NOT EXISTS dim_date (
    date_id             INTEGER     PRIMARY KEY,        -- YYYYMMDD integer key
    full_date           TEXT        NOT NULL UNIQUE,    -- ISO date string YYYY-MM-DD
    year                INTEGER     NOT NULL,
    quarter             INTEGER     NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    quarter_label       TEXT        NOT NULL,           -- e.g. "Q1-2024"
    month               INTEGER     NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name          TEXT        NOT NULL,           -- e.g. "April"
    week                INTEGER     NOT NULL,           -- ISO week number
    day_of_week         INTEGER     NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    day_name            TEXT        NOT NULL,           -- e.g. "Monday"
    is_weekday          INTEGER     NOT NULL CHECK (is_weekday IN (0,1)),
    fy_year             INTEGER     NOT NULL,           -- Indian financial year (Apr–Mar)
    fy_label            TEXT        NOT NULL            -- e.g. "FY23-24"
);

CREATE INDEX IF NOT EXISTS idx_date_year_month ON dim_date (year, month);
CREATE INDEX IF NOT EXISTS idx_date_fy ON dim_date (fy_label);


-- =============================================================================
-- DIMENSION: dim_investor
-- Investor master — KYC, demographics, risk profile.
-- Grain: investor
-- =============================================================================
CREATE TABLE IF NOT EXISTS dim_investor (
    investor_id         TEXT        PRIMARY KEY,        -- e.g. INV0001
    age                 INTEGER     CHECK (age BETWEEN 18 AND 100),
    city                TEXT,
    risk_profile        TEXT        CHECK (risk_profile IN ('Conservative','Moderate','Aggressive')),
    annual_income_lakh  REAL        CHECK (annual_income_lakh > 0),
    kyc_status          TEXT        CHECK (kyc_status IN ('Verified','Pending','Rejected','Expired')),
    registration_date   TEXT                            -- YYYY-MM-DD
);

CREATE INDEX IF NOT EXISTS idx_investor_city ON dim_investor (city);
CREATE INDEX IF NOT EXISTS idx_investor_kyc  ON dim_investor (kyc_status);


-- =============================================================================
-- FACT: fact_nav
-- Daily NAV per scheme. Forward-filled for trading holidays.
-- Grain: one row per (amfi_code, trading date)
-- =============================================================================
CREATE TABLE IF NOT EXISTS fact_nav (
    nav_id              INTEGER     PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER     NOT NULL REFERENCES dim_fund (amfi_code),
    date_id             INTEGER     NOT NULL REFERENCES dim_date (date_id),
    nav_date            TEXT        NOT NULL,           -- YYYY-MM-DD (denormalised for readability)
    nav                 REAL        NOT NULL CHECK (nav > 0),
    UNIQUE (amfi_code, date_id)
);

CREATE INDEX IF NOT EXISTS idx_nav_amfi_date ON fact_nav (amfi_code, nav_date);
CREATE INDEX IF NOT EXISTS idx_nav_date       ON fact_nav (nav_date);


-- =============================================================================
-- FACT: fact_transactions
-- Unified SIP + Lumpsum + Redemption ledger.
-- Grain: one row per transaction
-- =============================================================================
CREATE TABLE IF NOT EXISTS fact_transactions (
    txn_id              INTEGER     PRIMARY KEY,
    investor_id         TEXT        NOT NULL REFERENCES dim_investor (investor_id),
    amfi_code           INTEGER     NOT NULL REFERENCES dim_fund (amfi_code),
    date_id             INTEGER     NOT NULL REFERENCES dim_date (date_id),
    transaction_date    TEXT        NOT NULL,           -- YYYY-MM-DD
    transaction_type    TEXT        NOT NULL
                        CHECK (transaction_type IN ('SIP','Lumpsum','Redemption','Unknown')),
    amount              REAL        NOT NULL,           -- ₹; negative for Redemptions
    nav_at_purchase     REAL        NOT NULL CHECK (nav_at_purchase > 0),
    units_allotted      REAL        NOT NULL            -- negative for Redemptions
);

CREATE INDEX IF NOT EXISTS idx_txn_investor   ON fact_transactions (investor_id);
CREATE INDEX IF NOT EXISTS idx_txn_amfi       ON fact_transactions (amfi_code);
CREATE INDEX IF NOT EXISTS idx_txn_date       ON fact_transactions (transaction_date);
CREATE INDEX IF NOT EXISTS idx_txn_type       ON fact_transactions (transaction_type);


-- =============================================================================
-- FACT: fact_performance
-- Scheme-level return and risk metrics. Refreshed monthly.
-- Grain: one row per scheme (latest snapshot)
-- =============================================================================
CREATE TABLE IF NOT EXISTS fact_performance (
    amfi_code               INTEGER PRIMARY KEY REFERENCES dim_fund (amfi_code),
    scheme_name             TEXT,
    fund_house              TEXT,
    return_1y_pct           REAL,   -- 1-year trailing return %
    return_3y_cagr_pct      REAL,   -- 3-year CAGR %
    return_5y_cagr_pct      REAL,   -- 5-year CAGR %
    sharpe_ratio            REAL,   -- Annualised Sharpe (Rf=6% p.a.)
    annualised_volatility_pct REAL, -- Annualised std-dev of daily returns %
    var_95_daily_pct        REAL,   -- 5th percentile daily return (Value at Risk)
    max_drawdown_pct        REAL,   -- Maximum peak-to-trough drawdown %
    beta                    REAL,   -- Beta vs NIFTY 100 TRI
    expense_ratio_pct       REAL,
    is_anomaly              INTEGER CHECK (is_anomaly IN (0,1))
);


-- =============================================================================
-- FACT: fact_portfolio_holdings
-- Fund-level stock holdings. Point-in-time (latest available).
-- Grain: one row per (amfi_code, stock_symbol)
-- =============================================================================
CREATE TABLE IF NOT EXISTS fact_portfolio_holdings (
    holding_id          INTEGER     PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER     NOT NULL REFERENCES dim_fund (amfi_code),
    stock_symbol        TEXT        NOT NULL,
    weight_pct          REAL        NOT NULL CHECK (weight_pct >= 0),
    market_value_cr     REAL        NOT NULL CHECK (market_value_cr >= 0),
    UNIQUE (amfi_code, stock_symbol)
);

CREATE INDEX IF NOT EXISTS idx_holdings_amfi   ON fact_portfolio_holdings (amfi_code);
CREATE INDEX IF NOT EXISTS idx_holdings_stock  ON fact_portfolio_holdings (stock_symbol);


-- =============================================================================
-- FACT: fact_dividends
-- Per-unit dividend declarations by scheme.
-- Grain: one row per (amfi_code, dividend_date)
-- =============================================================================
CREATE TABLE IF NOT EXISTS fact_dividends (
    dividend_id         INTEGER     PRIMARY KEY AUTOINCREMENT,
    amfi_code           INTEGER     NOT NULL REFERENCES dim_fund (amfi_code),
    dividend_date       TEXT        NOT NULL,           -- YYYY-MM-DD
    dividend_per_unit   REAL        NOT NULL CHECK (dividend_per_unit >= 0),
    dividend_type       TEXT        CHECK (dividend_type IN ('Per Unit','Percentage')),
    UNIQUE (amfi_code, dividend_date)
);


-- =============================================================================
-- FACT: fact_benchmark
-- NIFTY 100 Total Return Index daily values.
-- Grain: one calendar day
-- =============================================================================
CREATE TABLE IF NOT EXISTS fact_benchmark (
    benchmark_id        INTEGER     PRIMARY KEY AUTOINCREMENT,
    date                TEXT        NOT NULL UNIQUE,    -- YYYY-MM-DD
    nifty100_tri        REAL        NOT NULL CHECK (nifty100_tri > 0)
);

CREATE INDEX IF NOT EXISTS idx_benchmark_date ON fact_benchmark (date);
