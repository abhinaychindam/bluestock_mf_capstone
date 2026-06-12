-- database: ../data/db/bluestock_mf.db
-- =============================================================================
-- queries.sql — Bluestock MF Capstone Analytical SQL Queries
-- Database: SQLite (bluestock_mf.db)
--
-- Q01  Top 5 funds by AUM
-- Q02  Average NAV per month (per scheme)
-- Q03  SIP YoY growth by fund
-- Q04  Transaction volume by city (investor state)
-- Q05  Funds with expense_ratio < 1%
-- Q06  Best and worst performing schemes by 3-year CAGR
-- Q07  Top 5 most-held stocks across all fund portfolios
-- Q08  Monthly SIP investment trend (absolute ₹ deployed)
-- Q09  Investor cohort analysis — assets by risk profile
-- Q10  Risk-adjusted ranking (Sharpe / Volatility composite)
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- Q01 · Top 5 Funds by AUM (₹ Crore)
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Identify the dominant schemes by assets under management.
-- Large AUM funds attract institutional flows and are proxy for investor trust.
SELECT
    f.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.category,
    f.aum_cr,
    ROUND(f.aum_cr * 100.0 / SUM(f.aum_cr) OVER (), 2)  AS aum_share_pct
FROM   dim_fund f
ORDER  BY f.aum_cr DESC
LIMIT  5;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q02 · Average NAV per Calendar Month (per Scheme)
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Monthly smoothed NAV helps strip intra-month volatility for
-- long-term trend analysis and magazine-style performance tables.
SELECT
    n.amfi_code,
    f.scheme_name,
    d.year,
    d.month,
    d.month_name,
    ROUND(AVG(n.nav), 4)   AS avg_monthly_nav,
    ROUND(MIN(n.nav), 4)   AS min_nav,
    ROUND(MAX(n.nav), 4)   AS max_nav,
    COUNT(*)               AS trading_days
FROM   fact_nav      n
JOIN   dim_date      d  ON n.date_id   = d.date_id
JOIN   dim_fund      f  ON n.amfi_code = f.amfi_code
GROUP  BY n.amfi_code, d.year, d.month
ORDER  BY n.amfi_code, d.year, d.month;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q03 · SIP YoY Growth by Fund
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Measures how SIP inflows into each scheme have grown year-over-year,
-- a key indicator of retail investor sentiment and fund marketing effectiveness.
WITH sip_annual AS (
    SELECT
        t.amfi_code,
        d.year,
        SUM(t.amount)    AS total_sip_inflow,
        COUNT(*)         AS sip_count
    FROM   fact_transactions t
    JOIN   dim_date          d ON t.date_id = d.date_id
    WHERE  t.transaction_type = 'SIP'
    GROUP  BY t.amfi_code, d.year
)
SELECT
    sa.amfi_code,
    f.scheme_name,
    sa.year,
    ROUND(sa.total_sip_inflow, 2)       AS total_sip_inflow,
    sa.sip_count,
    LAG(sa.total_sip_inflow) OVER w     AS prev_year_inflow,
    ROUND(
        (sa.total_sip_inflow - LAG(sa.total_sip_inflow) OVER w)
        * 100.0 / NULLIF(LAG(sa.total_sip_inflow) OVER w, 0)
    , 2)                                AS yoy_growth_pct
FROM   sip_annual sa
JOIN   dim_fund   f  ON sa.amfi_code = f.amfi_code
WINDOW w AS (PARTITION BY sa.amfi_code ORDER BY sa.year)
ORDER  BY sa.amfi_code, sa.year;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q04 · Transaction Volume by Investor City
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Geographic distribution of AUM flows reveals regional hotspots
-- for distributor focus and regulatory compliance reporting.
SELECT
    i.city,
    t.transaction_type,
    COUNT(*)                                    AS txn_count,
    ROUND(SUM(ABS(t.amount)), 2)                AS total_amount,
    ROUND(AVG(ABS(t.amount)), 2)                AS avg_ticket_size,
    COUNT(DISTINCT t.investor_id)               AS unique_investors
FROM   fact_transactions t
JOIN   dim_investor      i ON t.investor_id = i.investor_id
GROUP  BY i.city, t.transaction_type
ORDER  BY total_amount DESC;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q05 · Funds with Expense Ratio < 1%
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Low-cost funds (direct plans) are a key investor selection criterion;
-- SEBI caps and distributor commission analysis depend on this field.
SELECT
    f.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.category,
    f.sub_category,
    f.expense_ratio_pct,
    f.aum_cr,
    RANK() OVER (PARTITION BY f.category ORDER BY f.expense_ratio_pct ASC) AS cost_rank_in_category
FROM   dim_fund f
WHERE  f.expense_ratio_pct < 1.0
ORDER  BY f.expense_ratio_pct ASC;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q06 · Best and Worst Schemes by 3-Year CAGR
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Primary return benchmark for fund selection. Annualised over 3 years
-- to smooth out short-term market cycles.
SELECT
    p.amfi_code,
    f.scheme_name,
    f.fund_house,
    f.sub_category,
    ROUND(p.return_3y_cagr_pct, 2)             AS return_3y_cagr_pct,
    ROUND(p.return_1y_pct,       2)             AS return_1y_pct,
    ROUND(p.sharpe_ratio,        4)             AS sharpe_ratio,
    RANK() OVER (ORDER BY p.return_3y_cagr_pct DESC) AS overall_rank
FROM   fact_performance p
JOIN   dim_fund         f ON p.amfi_code = f.amfi_code
WHERE  p.return_3y_cagr_pct IS NOT NULL
   AND p.is_anomaly = 0
ORDER  BY p.return_3y_cagr_pct DESC;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q07 · Top 10 Most-Held Stocks Across Fund Portfolios
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Identifies systemic concentration risk — if many funds hold the same
-- stocks, a shock to those names ripples across the entire MF universe.
SELECT
    h.stock_symbol,
    COUNT(DISTINCT h.amfi_code)          AS funds_holding,
    ROUND(AVG(h.weight_pct), 2)          AS avg_weight_pct,
    ROUND(SUM(h.market_value_cr), 2)     AS total_mf_exposure_cr,
    GROUP_CONCAT(f.fund_house, ' | ')    AS held_by_fund_houses
FROM   fact_portfolio_holdings h
JOIN   dim_fund                f ON h.amfi_code = f.amfi_code
GROUP  BY h.stock_symbol
ORDER  BY funds_holding DESC, total_mf_exposure_cr DESC
LIMIT  10;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q08 · Monthly SIP Investment Trend (Absolute ₹ Deployed)
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Tracks the monthly SIP pulse of the fund house — equivalent to
-- AMFI's monthly SIP contribution data used in industry press releases.
SELECT
    d.year,
    d.month,
    d.month_name,
    d.fy_label,
    ROUND(SUM(t.amount), 2)          AS total_sip_deployed,
    COUNT(*)                         AS sip_instalments,
    COUNT(DISTINCT t.investor_id)    AS active_sip_investors,
    ROUND(AVG(t.amount), 2)          AS avg_sip_amount
FROM   fact_transactions t
JOIN   dim_date          d ON t.date_id = d.date_id
WHERE  t.transaction_type = 'SIP'
GROUP  BY d.year, d.month
ORDER  BY d.year, d.month;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q09 · Investor Cohort — Invested Capital by Risk Profile
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Validates that fund allocations match stated risk profiles.
-- Regulators and compliance teams use this to flag mis-selling.
SELECT
    i.risk_profile,
    i.kyc_status,
    COUNT(DISTINCT t.investor_id)            AS investors,
    ROUND(SUM(CASE WHEN t.transaction_type IN ('SIP','Lumpsum')
                   THEN t.amount ELSE 0 END), 2)  AS gross_invested,
    ROUND(SUM(CASE WHEN t.transaction_type = 'Redemption'
                   THEN ABS(t.amount) ELSE 0 END), 2) AS total_redeemed,
    ROUND(SUM(CASE WHEN t.transaction_type IN ('SIP','Lumpsum')
                   THEN t.amount ELSE 0 END)
          - SUM(CASE WHEN t.transaction_type = 'Redemption'
                     THEN ABS(t.amount) ELSE 0 END), 2) AS net_aum_proxy
FROM   fact_transactions t
JOIN   dim_investor      i ON t.investor_id = i.investor_id
GROUP  BY i.risk_profile, i.kyc_status
ORDER  BY i.risk_profile, i.kyc_status;


-- ─────────────────────────────────────────────────────────────────────────────
-- Q10 · Risk-Adjusted Ranking (Composite Score)
-- ─────────────────────────────────────────────────────────────────────────────
-- Business: Combines Sharpe ratio, 3Y CAGR, max drawdown and beta into a
-- single composite rank for fund selection tables and recommendation engines.
-- Score = 0.4*sharpe_rank + 0.3*cagr_rank + 0.2*drawdown_rank + 0.1*beta_rank
-- (All ranks: 1 = best; lower rank number = better performance)
WITH base AS (
    SELECT
        p.amfi_code,
        f.scheme_name,
        f.sub_category,
        p.sharpe_ratio,
        p.return_3y_cagr_pct,
        p.max_drawdown_pct,
        p.beta,
        p.annualised_volatility_pct,
        RANK() OVER (ORDER BY p.sharpe_ratio           DESC) AS sharpe_rank,
        RANK() OVER (ORDER BY p.return_3y_cagr_pct     DESC) AS cagr_rank,
        RANK() OVER (ORDER BY p.max_drawdown_pct        DESC) AS drawdown_rank,  -- less negative = better
        RANK() OVER (ORDER BY ABS(p.beta - 1.0)         ASC)  AS beta_rank       -- closer to 1 = lower active risk
    FROM   fact_performance p
    JOIN   dim_fund         f ON p.amfi_code = f.amfi_code
    WHERE  p.is_anomaly = 0
      AND  p.return_3y_cagr_pct IS NOT NULL
)
SELECT
    amfi_code,
    scheme_name,
    sub_category,
    ROUND(sharpe_ratio,            4)  AS sharpe_ratio,
    ROUND(return_3y_cagr_pct,      2)  AS return_3y_cagr_pct,
    ROUND(max_drawdown_pct,        2)  AS max_drawdown_pct,
    ROUND(beta,                    4)  AS beta,
    ROUND(annualised_volatility_pct,2) AS volatility_pct,
    ROUND(0.4*sharpe_rank + 0.3*cagr_rank
          + 0.2*drawdown_rank + 0.1*beta_rank, 2) AS composite_score,
    RANK() OVER (
        ORDER BY 0.4*sharpe_rank + 0.3*cagr_rank
                 + 0.2*drawdown_rank + 0.1*beta_rank
    )                                  AS final_rank
FROM   base
ORDER  BY final_rank;
