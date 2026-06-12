"""
etl_pipeline.py — Day 2 ETL Pipeline
Bluestock Mutual Fund Capstone

Steps:
  1. Clean all 10 source CSVs → data/processed/
  2. Build merged investor_transactions and scheme_performance tables
  3. Load star-schema SQLite DB via SQLAlchemy
  4. Verify row counts match source

Run:
    python scripts/etl_pipeline.py
"""

import logging
import sys
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent.parent
RAW       = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
DB_DIR    = BASE / "data" / "db"
PROCESSED.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH   = DB_DIR / "bluestock_mf.db"
DB_URL    = f"sqlite:///{DB_PATH}"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE / "data" / "etl_pipeline.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CLEANING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def clean_nav_history() -> pd.DataFrame:
    """
    Source: data/processed/nav_history_clean.csv (from Day 1)
    - Parse nav_date to datetime
    - Sort by amfi_code + nav_date
    - Reindex to full business-day calendar, forward-fill gaps (holidays/weekends)
    - Remove duplicates on (amfi_code, nav_date)
    - Validate NAV > 0
    """
    src = PROCESSED / "nav_history_clean.csv"
    if not src.exists():
        # Fall back: rebuild from sip/lumpsum nav columns isn't ideal;
        # generate a fresh nav series from fund_master codes
        log.warning("nav_history_clean.csv not found in processed — regenerating")
        return _regenerate_nav_history()

    df = pd.read_csv(src, parse_dates=["nav_date"])
    log.info("nav_history raw load: %s", df.shape)

    # 1. Parse & sort
    df["nav_date"] = pd.to_datetime(df["nav_date"], errors="coerce")
    df.dropna(subset=["nav_date"], inplace=True)
    df.sort_values(["amfi_code", "nav_date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 2. Remove duplicates
    before = len(df)
    df.drop_duplicates(subset=["amfi_code", "nav_date"], keep="last", inplace=True)
    dupes = before - len(df)
    if dupes:
        log.warning("nav_history: removed %d duplicate rows", dupes)

    # 3. Validate NAV > 0
    invalid = (df["nav"] <= 0) | df["nav"].isna()
    if invalid.any():
        log.warning("nav_history: %d invalid NAV rows (≤0 or NaN) — dropping", invalid.sum())
        df = df[~invalid].copy()

    # 4. Forward-fill across full business-day calendar per scheme
    full_bdays = pd.bdate_range(df["nav_date"].min(), df["nav_date"].max())
    filled_parts = []
    for code, grp in df.groupby("amfi_code"):
        grp = grp.set_index("nav_date").reindex(full_bdays)
        grp["amfi_code"] = code
        grp["nav"] = grp["nav"].ffill()
        grp.index.name = "nav_date"
        filled_parts.append(grp.reset_index())
    df = pd.concat(filled_parts, ignore_index=True)
    df["nav_date"] = pd.to_datetime(df["nav_date"])
    df.dropna(subset=["nav"], inplace=True)

    log.info("nav_history cleaned: %s (after ffill)", df.shape)
    anomalies = []
    if (df["nav"] <= 0).any():
        anomalies.append(f"⚠ {(df['nav']<=0).sum()} non-positive NAVs remain")
    _report_anomalies("nav_history", anomalies)
    return df[["amfi_code", "nav_date", "nav"]]


def _regenerate_nav_history() -> pd.DataFrame:
    """Recreate nav_history from the generator script's logic when processed file missing."""
    rng = np.random.default_rng(42)
    fm = pd.read_csv(RAW / "fund_master.csv")
    dates = pd.bdate_range("2019-04-01", "2024-03-31")
    rows = []
    for code in fm["amfi_code"]:
        nav = rng.uniform(30, 200)
        for d in dates:
            nav = max(nav * (1 + rng.normal(0.0004, 0.012)), 0.5)
            rows.append((code, d.date(), round(nav, 4)))
    df = pd.DataFrame(rows, columns=["amfi_code", "nav_date", "nav"])
    df["nav_date"] = pd.to_datetime(df["nav_date"])
    return df


def clean_fund_master() -> pd.DataFrame:
    """
    - Parse launch_date to datetime
    - Validate expense_ratio 0.1–2.5%
    - Standardise risk_grade enum
    - Strip whitespace from text columns
    """
    df = pd.read_csv(RAW / "fund_master.csv", parse_dates=["launch_date"])
    log.info("01_fund_master raw load: %s", df.shape)

    anomalies = []
    # Whitespace
    for col in ["scheme_name", "fund_house", "category", "sub_category", "risk_grade"]:
        df[col] = df[col].str.strip()

    # Expense ratio range check
    out_of_range = df[(df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)]
    if not out_of_range.empty:
        anomalies.append(f"⚠ {len(out_of_range)} schemes with expense_ratio outside 0.1–2.5%: {out_of_range['amfi_code'].tolist()}")
        df.loc[df["expense_ratio_pct"] < 0.1, "expense_ratio_pct"] = 0.1
        df.loc[df["expense_ratio_pct"] > 2.5, "expense_ratio_pct"] = 2.5

    # Risk grade standardisation
    valid_grades = {"Low", "Low to Moderate", "Moderate", "Moderately High", "High", "Very High"}
    bad_grades = df[~df["risk_grade"].isin(valid_grades)]
    if not bad_grades.empty:
        anomalies.append(f"⚠ {len(bad_grades)} unknown risk_grade values")

    # AUM must be positive
    neg_aum = (df["aum_cr"] < 0).sum()
    if neg_aum:
        anomalies.append(f"⚠ {neg_aum} negative AUM values — setting to NaN")
        df.loc[df["aum_cr"] < 0, "aum_cr"] = np.nan

    _report_anomalies("fund_master", anomalies)
    log.info("fund_master cleaned: %s", df.shape)
    return df


def clean_investor_transactions() -> pd.DataFrame:
    """
    Merge sip_transactions + lumpsum_transactions into unified investor_transactions.
    - Add transaction_type column: SIP / Lumpsum
    - Standardise transaction_date to datetime
    - Validate amount > 0
    - Validate units_allotted > 0
    - Normalise column name: sip_amount / amount → amount
    - Assign synthetic redemption rows (~5% of lumpsum) for realism
    """
    sip   = pd.read_csv(RAW / "sip_transactions.csv",     parse_dates=["transaction_date"])
    lump  = pd.read_csv(RAW / "lumpsum_transactions.csv", parse_dates=["transaction_date"])
    log.info("sip raw: %s  lumpsum raw: %s", sip.shape, lump.shape)

    sip  = sip.rename(columns={"sip_amount": "amount"})
    sip["transaction_type"]  = "SIP"
    lump["transaction_type"] = "Lumpsum"

    # Build small redemption slice (~5% of lumpsum rows)
    rng = np.random.default_rng(7)
    red = lump.sample(frac=0.05, random_state=7).copy()
    red["transaction_type"] = "Redemption"
    # Redemption amounts are negative by convention
    red["amount"]          = -red["amount"].abs()
    red["units_allotted"]  = -red["units_allotted"].abs()
    red["transaction_date"] = red["transaction_date"] + pd.to_timedelta(
        rng.integers(30, 365, len(red)), unit="D"
    )

    df = pd.concat([sip, lump, red], ignore_index=True)

    anomalies = []
    # Date parsing
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    bad_dates = df["transaction_date"].isna().sum()
    if bad_dates:
        anomalies.append(f"⚠ {bad_dates} unparseable transaction_date rows — dropped")
        df.dropna(subset=["transaction_date"], inplace=True)

    # Amount validation (SIP/Lumpsum must be > 0; Redemptions are negative)
    non_redemption = df[df["transaction_type"] != "Redemption"]
    invalid_amt = (non_redemption["amount"] <= 0).sum()
    if invalid_amt:
        anomalies.append(f"⚠ {invalid_amt} SIP/Lumpsum rows with amount ≤ 0 — dropped")
        df = df[~((df["transaction_type"] != "Redemption") & (df["amount"] <= 0))].copy()

    # transaction_type enum
    valid_types = {"SIP", "Lumpsum", "Redemption"}
    bad_types = (~df["transaction_type"].isin(valid_types)).sum()
    if bad_types:
        anomalies.append(f"⚠ {bad_types} unknown transaction_type values — set to 'Unknown'")
        df.loc[~df["transaction_type"].isin(valid_types), "transaction_type"] = "Unknown"

    # Units allotted (non-redemption: must be positive)
    bad_units = ((df["transaction_type"] != "Redemption") & (df["units_allotted"] <= 0)).sum()
    if bad_units:
        anomalies.append(f"⚠ {bad_units} rows with units_allotted ≤ 0 for SIP/Lumpsum")

    # Add transaction_id
    df.insert(0, "txn_id", range(1, len(df) + 1))

    # Sort
    df.sort_values(["investor_id", "transaction_date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    _report_anomalies("investor_transactions", anomalies)
    log.info("investor_transactions merged & cleaned: %s", df.shape)
    return df


def clean_scheme_performance() -> pd.DataFrame:
    """
    Merge returns_summary + risk_metrics into scheme_performance.
    - Validate all return/metric columns are numeric
    - Flag anomalies: return_1y > 100%, sharpe < -3, beta > 2
    - Validate expense_ratio from fund_master join
    - Add is_anomaly flag column
    """
    ret  = pd.read_csv(RAW / "returns_summary.csv")
    risk = pd.read_csv(RAW / "risk_metrics.csv")
    fm   = pd.read_csv(RAW / "fund_master.csv")[["amfi_code", "expense_ratio_pct", "scheme_name", "fund_house"]]
    log.info("returns_summary: %s  risk_metrics: %s", ret.shape, risk.shape)

    df = ret.merge(risk, on="amfi_code", how="outer")
    df = df.merge(fm,   on="amfi_code", how="left")

    anomalies = []
    numeric_cols = ["return_1y_pct", "return_3y_cagr_pct", "return_5y_cagr_pct",
                    "sharpe_ratio", "annualised_volatility_pct",
                    "var_95_daily_pct", "max_drawdown_pct", "beta"]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            non_numeric = df[col].isna().sum()
            if non_numeric:
                anomalies.append(f"⚠ {col}: {non_numeric} non-numeric values → coerced to NaN")

    # Anomaly flags
    df["is_anomaly"] = False
    if "return_1y_pct" in df.columns:
        extreme_ret = df["return_1y_pct"].abs() > 100
        df.loc[extreme_ret, "is_anomaly"] = True
        if extreme_ret.any():
            anomalies.append(f"⚠ {extreme_ret.sum()} schemes with |1Y return| > 100%")

    if "sharpe_ratio" in df.columns:
        extreme_sharpe = df["sharpe_ratio"].abs() > 3
        df.loc[extreme_sharpe, "is_anomaly"] = True
        if extreme_sharpe.any():
            anomalies.append(f"⚠ {extreme_sharpe.sum()} schemes with |Sharpe| > 3")

    if "beta" in df.columns:
        extreme_beta = df["beta"].abs() > 2
        df.loc[extreme_beta, "is_anomaly"] = True
        if extreme_beta.any():
            anomalies.append(f"⚠ {extreme_beta.sum()} schemes with |beta| > 2")

    # Expense ratio range check
    if "expense_ratio_pct" in df.columns:
        bad_exp = df[(df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)]
        if not bad_exp.empty:
            anomalies.append(f"⚠ {len(bad_exp)} schemes with expense_ratio outside 0.1–2.5%: {bad_exp['amfi_code'].tolist()}")

    _report_anomalies("scheme_performance", anomalies)
    log.info("scheme_performance merged & cleaned: %s", df.shape)
    return df


def clean_investor_profiles() -> pd.DataFrame:
    df = pd.read_csv(RAW / "investor_profiles.csv", parse_dates=["registration_date"])
    anomalies = []

    # KYC enum
    valid_kyc = {"Verified", "Pending", "Rejected", "Expired"}
    bad_kyc = (~df["kyc_status"].isin(valid_kyc)).sum()
    if bad_kyc:
        anomalies.append(f"⚠ {bad_kyc} unknown kyc_status values")

    # Risk profile enum
    valid_risk = {"Conservative", "Moderate", "Aggressive"}
    bad_risk = (~df["risk_profile"].isin(valid_risk)).sum()
    if bad_risk:
        anomalies.append(f"⚠ {bad_risk} unknown risk_profile values")

    # Age sanity
    bad_age = ((df["age"] < 18) | (df["age"] > 100)).sum()
    if bad_age:
        anomalies.append(f"⚠ {bad_age} investors with implausible age")

    df["city"] = df["city"].str.strip().str.title()
    _report_anomalies("investor_profiles", anomalies)
    log.info("investor_profiles cleaned: %s", df.shape)
    return df


def clean_portfolio_holdings() -> pd.DataFrame:
    df = pd.read_csv(RAW / "portfolio_holdings.csv")
    anomalies = []

    # Weight should be 0–100
    bad_wt = ((df["weight_pct"] < 0) | (df["weight_pct"] > 100)).sum()
    if bad_wt:
        anomalies.append(f"⚠ {bad_wt} holdings with weight_pct outside 0–100")

    # Per-fund weights should sum to ~100%
    fund_totals = df.groupby("amfi_code")["weight_pct"].sum()
    bad_totals  = fund_totals[(fund_totals < 95) | (fund_totals > 105)]
    if not bad_totals.empty:
        anomalies.append(f"⚠ {len(bad_totals)} funds with portfolio weights not summing to ~100%")

    df["stock_symbol"] = df["stock_symbol"].str.strip().str.upper()
    _report_anomalies("portfolio_holdings", anomalies)
    log.info("portfolio_holdings cleaned: %s", df.shape)
    return df


def clean_benchmark() -> pd.DataFrame:
    df = pd.read_csv(RAW / "benchmark_nifty100.csv", parse_dates=["date"])
    df.sort_values("date", inplace=True)
    df.drop_duplicates(subset=["date"], keep="last", inplace=True)
    anomalies = []
    bad = (df["nifty100_tri"] <= 0).sum()
    if bad:
        anomalies.append(f"⚠ {bad} non-positive benchmark values")
    _report_anomalies("benchmark_nifty100", anomalies)
    log.info("benchmark_nifty100 cleaned: %s", df.shape)
    return df


def clean_dividend_history() -> pd.DataFrame:
    df = pd.read_csv(RAW / "dividend_history.csv", parse_dates=["dividend_date"])
    anomalies = []
    neg_div = (df["dividend_per_unit"] < 0).sum()
    if neg_div:
        anomalies.append(f"⚠ {neg_div} negative dividend_per_unit rows")
    valid_types = {"Per Unit", "Percentage"}
    bad_types = (~df["dividend_type"].isin(valid_types)).sum()
    if bad_types:
        anomalies.append(f"⚠ {bad_types} unknown dividend_type values")
    _report_anomalies("dividend_history", anomalies)
    log.info("dividend_history cleaned: %s", df.shape)
    return df


def _report_anomalies(name: str, anomalies: list) -> None:
    if anomalies:
        for a in anomalies:
            log.warning("[%s] %s", name, a)
    else:
        log.info("[%s] ✓ No anomalies detected", name)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — DIM DATE TABLE
# ═══════════════════════════════════════════════════════════════════════════════

def build_dim_date(start: str = "2019-01-01", end: str = "2025-12-31") -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_id"]      = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["year"]         = df["full_date"].dt.year
    df["quarter"]      = df["full_date"].dt.quarter
    df["month"]        = df["full_date"].dt.month
    df["month_name"]   = df["full_date"].dt.strftime("%B")
    df["week"]         = df["full_date"].dt.isocalendar().week.astype(int)
    df["day_of_week"]  = df["full_date"].dt.dayofweek   # 0=Mon
    df["day_name"]     = df["full_date"].dt.strftime("%A")
    df["is_weekday"]   = (df["day_of_week"] < 5).astype(int)
    df["quarter_label"]= "Q" + df["quarter"].astype(str) + "-" + df["year"].astype(str)
    df["fy_year"]      = df["year"].where(df["month"] < 4, df["year"] + 1)  # Indian FY (Apr–Mar)
    df["fy_label"]     = "FY" + (df["fy_year"] - 1).astype(str).str[-2:] + \
                         "-" + df["fy_year"].astype(str).str[-2:]
    return df[["date_id","full_date","year","quarter","quarter_label",
               "month","month_name","week","day_of_week","day_name",
               "is_weekday","fy_year","fy_label"]]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — SQLite LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def load_to_sqlite(tables: dict[str, pd.DataFrame]) -> None:
    """
    Load all DataFrames into SQLite via SQLAlchemy.
    Uses if_exists='replace' so re-runs are idempotent.
    Verifies row counts after each load.
    """
    engine = create_engine(DB_URL, echo=False)

    # Convert date/datetime columns to ISO strings for SQLite compatibility
    def _prep(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.columns:
            if hasattr(df[col], "dt") and pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime("%Y-%m-%d")
        return df

    log.info("─" * 60)
    log.info("Loading tables into SQLite: %s", DB_PATH)
    log.info("─" * 60)

    row_counts = {}
    for table_name, df in tables.items():
        df_out = _prep(df)
        df_out.to_sql(table_name, con=engine, if_exists="replace", index=False,
                      chunksize=10_000)
        # Verify
        with engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        match = "✓" if count == len(df) else "✗ MISMATCH"
        log.info("  %-30s  src=%6d  db=%6d  %s",
                 table_name, len(df), count, match)
        row_counts[table_name] = {"source": len(df), "db": count}

    log.info("─" * 60)
    log.info("All tables loaded. DB size: %.1f MB",
             DB_PATH.stat().st_size / 1_048_576)
    return row_counts


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — SAVE PROCESSED CSVs
# ═══════════════════════════════════════════════════════════════════════════════

def save_processed(name: str, df: pd.DataFrame) -> None:
    out = PROCESSED / f"{name}_clean.csv"
    df.to_csv(out, index=False)
    log.info("  Saved processed → %s  (%d rows)", out.name, len(df))


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    log.info("=" * 60)
    log.info("Bluestock MF Capstone — Day 2 ETL Pipeline")
    log.info("=" * 60)

    # ── Clean ─────────────────────────────────────────────────────────────────
    log.info("\n[1/3] Cleaning datasets …")

    nav_history         = clean_nav_history()
    fund_master         = clean_fund_master()
    investor_txns       = clean_investor_transactions()
    scheme_perf         = clean_scheme_performance()
    investor_profiles   = clean_investor_profiles()
    portfolio_holdings  = clean_portfolio_holdings()
    benchmark           = clean_benchmark()
    dividend_history    = clean_dividend_history()
    dim_date            = build_dim_date()

    # Save all processed CSVs
    log.info("\n[2/3] Saving processed CSVs …")
    save_processed("nav_history",        nav_history)
    save_processed("fund_master",        fund_master)
    save_processed("investor_transactions", investor_txns)
    save_processed("scheme_performance", scheme_perf)
    save_processed("investor_profiles",  investor_profiles)
    save_processed("portfolio_holdings", portfolio_holdings)
    save_processed("benchmark_nifty100", benchmark)
    save_processed("dividend_history",   dividend_history)
    save_processed("dim_date",           dim_date)

    # ── Load SQLite ───────────────────────────────────────────────────────────
    log.info("\n[3/3] Loading SQLite star schema …")

    # Prepare fact_nav with date_id FK
    fact_nav = nav_history.copy()
    fact_nav["nav_date_str"] = pd.to_datetime(fact_nav["nav_date"]).dt.strftime("%Y-%m-%d")
    fact_nav["date_id"] = pd.to_datetime(fact_nav["nav_date"]).dt.strftime("%Y%m%d").astype(int)

    # Prepare fact_transactions with date_id FK
    fact_txn = investor_txns.copy()
    fact_txn["date_id"] = pd.to_datetime(fact_txn["transaction_date"]).dt.strftime("%Y%m%d").astype(int)

    # dim_fund: deduplicate fund_master as dimension
    dim_fund = fund_master.copy()

    tables = {
        # Dimensions
        "dim_fund":         dim_fund,
        "dim_date":         dim_date,
        "dim_investor":     investor_profiles,
        # Facts
        "fact_nav":         fact_nav[["amfi_code", "date_id", "nav_date_str", "nav"]].rename(columns={"nav_date_str": "nav_date"}),
        "fact_transactions": fact_txn,
        "fact_performance": scheme_perf,
        "fact_portfolio_holdings": portfolio_holdings,
        "fact_dividends":   dividend_history,
        "fact_benchmark":   benchmark,
    }

    row_counts = load_to_sqlite(tables)

    # ── Summary ───────────────────────────────────────────────────────────────
    log.info("\n" + "=" * 60)
    log.info("Day 2 ETL Complete")
    log.info("  Processed CSVs → data/processed/")
    log.info("  SQLite DB      → %s", DB_PATH)
    total_rows = sum(v["db"] for v in row_counts.values())
    log.info("  Total rows     → %s", f"{total_rows:,}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
