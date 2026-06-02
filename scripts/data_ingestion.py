"""
data_ingestion.py — Day 1 ETL Pipeline
Bluestock Mutual Fund Capstone Project

Loads all 10 CSV datasets, prints shape/dtypes/head,
notes anomalies, and persists processed copies.
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(BASE / "data" / "ingestion.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)

# ── Dataset catalogue ─────────────────────────────────────────────────────────
DATASETS = {
    "fund_master":          {"file": "fund_master.csv",          "date_cols": ["launch_date"]},
    "nav_history":          {"file": "nav_history.csv",          "date_cols": ["nav_date"]},
    "returns_summary":      {"file": "returns_summary.csv",      "date_cols": []},
    "portfolio_holdings":   {"file": "portfolio_holdings.csv",   "date_cols": []},
    "benchmark_nifty100":   {"file": "benchmark_nifty100.csv",   "date_cols": ["date"]},
    "sip_transactions":     {"file": "sip_transactions.csv",     "date_cols": ["transaction_date"]},
    "lumpsum_transactions": {"file": "lumpsum_transactions.csv", "date_cols": ["transaction_date"]},
    "investor_profiles":    {"file": "investor_profiles.csv",    "date_cols": ["registration_date"]},
    "dividend_history":     {"file": "dividend_history.csv",     "date_cols": ["dividend_date"]},
    "risk_metrics":         {"file": "risk_metrics.csv",         "date_cols": []},
}

ANOMALY_NOTES: dict[str, list[str]] = {}


def load_csv(name: str, cfg: dict) -> pd.DataFrame:
    """Load a CSV with optional date parsing; return DataFrame."""
    path = RAW / cfg["file"]
    if not path.exists():
        raise FileNotFoundError(f"Missing raw file: {path}")

    df = pd.read_csv(path, parse_dates=cfg["date_cols"])
    log.info("Loaded %-25s → %s", cfg["file"], df.shape)
    return df


def inspect_dataset(name: str, df: pd.DataFrame) -> list[str]:
    """Print shape, dtypes, head; return list of anomaly notes."""
    sep = "─" * 70
    print(f"\n{'═'*70}")
    print(f"  DATASET: {name.upper()}")
    print(f"{'═'*70}")

    print(f"\n▸ Shape:  {df.shape[0]:,} rows × {df.shape[1]} columns")

    print("\n▸ dtypes:")
    print(df.dtypes.to_string())

    print("\n▸ head(3):")
    print(df.head(3).to_string(index=False))

    print(f"\n▸ Null counts:")
    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if nulls.empty:
        print("  No nulls detected.")
    else:
        print(nulls.to_string())

    # Anomaly checks
    anomalies = []

    # Generic: duplicates
    dup_count = df.duplicated().sum()
    if dup_count:
        anomalies.append(f"⚠ {dup_count} fully-duplicate rows")

    # Dataset-specific checks
    if name == "nav_history":
        neg_nav = (df["nav"] <= 0).sum()
        if neg_nav:
            anomalies.append(f"⚠ {neg_nav} non-positive NAV values")
        # Check for weekends (bdate_range should have none, but verify)
        df["nav_date"] = pd.to_datetime(df["nav_date"])
        weekend_navs = df[df["nav_date"].dt.dayofweek >= 5]
        if not weekend_navs.empty:
            anomalies.append(f"⚠ {len(weekend_navs)} NAV records on weekends")

    if name == "fund_master":
        if df["expense_ratio_pct"].max() > 2.5:
            anomalies.append("⚠ Expense ratio > 2.5% (SEBI cap breach?)")
        if df["aum_cr"].min() < 0:
            anomalies.append("⚠ Negative AUM values detected")

    if name == "sip_transactions":
        if (df["sip_amount"] < 100).any():
            anomalies.append("⚠ SIP amount < ₹100 (below SEBI minimum)")
        if (df["units_allotted"] <= 0).any():
            anomalies.append("⚠ Zero/negative units allotted in SIP")

    if name == "returns_summary":
        if df["return_1y_pct"].abs().max() > 200:
            anomalies.append("⚠ 1Y return > 200% — possible outlier")
        null_3y = df["return_3y_cagr_pct"].isnull().sum()
        if null_3y:
            anomalies.append(f"ℹ {null_3y} schemes lack 3Y history (expected for new funds)")

    if name == "risk_metrics":
        high_beta = (df["beta"].abs() > 2).sum()
        if high_beta:
            anomalies.append(f"⚠ {high_beta} schemes with |beta| > 2")

    if anomalies:
        print("\n▸ Anomalies:")
        for a in anomalies:
            print(f"  {a}")
    else:
        print("\n▸ Anomalies: None detected ✓")

    print(sep)
    return anomalies


def validate_amfi_codes(fund_master: pd.DataFrame, nav_history: pd.DataFrame) -> str:
    """Cross-validate AMFI codes between fund_master and nav_history."""
    fm_codes = set(fund_master["amfi_code"].unique())
    nav_codes = set(nav_history["amfi_code"].unique())

    missing_in_nav = fm_codes - nav_codes
    extra_in_nav   = nav_codes - fm_codes

    lines = [
        "\n" + "═"*70,
        "  DATA QUALITY SUMMARY — AMFI CODE VALIDATION",
        "═"*70,
        f"  Schemes in fund_master  : {len(fm_codes)}",
        f"  Schemes in nav_history  : {len(nav_codes)}",
        f"  Full match              : {fm_codes == nav_codes}",
    ]
    if missing_in_nav:
        lines.append(f"  ⚠ Codes in master NOT in NAV history  : {missing_in_nav}")
    if extra_in_nav:
        lines.append(f"  ⚠ Codes in NAV history NOT in master  : {extra_in_nav}")
    if not missing_in_nav and not extra_in_nav:
        lines.append("  ✅ All AMFI codes validated — perfect 1-to-1 match")
    lines.append("═"*70)
    summary = "\n".join(lines)
    print(summary)
    return summary


def explore_fund_master(df: pd.DataFrame) -> None:
    """Print unique fund houses, categories, sub-cats, risk grades."""
    print("\n" + "═"*70)
    print("  FUND MASTER EXPLORATION")
    print("═"*70)
    print(f"\n▸ Unique Fund Houses ({df['fund_house'].nunique()}):")
    for fh in sorted(df["fund_house"].unique()):
        print(f"    • {fh}")

    print(f"\n▸ Categories ({df['category'].nunique()}):")
    print(df["category"].value_counts().to_string())

    print(f"\n▸ Sub-Categories ({df['sub_category'].nunique()}):")
    print(df["sub_category"].value_counts().to_string())

    print(f"\n▸ Risk Grades ({df['risk_grade'].nunique()}):")
    print(df["risk_grade"].value_counts().to_string())

    print("\n▸ AMFI Code Structure (sample):")
    for _, row in df.head(5).iterrows():
        print(f"    {row['amfi_code']}  →  {row['scheme_name'][:55]}")

    print("\n  AMFI codes are 6-digit numeric identifiers assigned sequentially")
    print("  by AMFI. Lower codes = older registrations.")
    print("═"*70)


def save_processed(name: str, df: pd.DataFrame) -> None:
    out = PROCESSED / f"{name}_clean.csv"
    df.to_csv(out, index=False)
    log.info("Saved processed → %s", out.name)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    log.info("=" * 60)
    log.info("Bluestock MF Capstone — Day 1 Data Ingestion")
    log.info("=" * 60)

    dataframes: dict[str, pd.DataFrame] = {}
    all_anomalies: dict[str, list] = {}

    # Load and inspect each dataset
    for name, cfg in DATASETS.items():
        try:
            df = load_csv(name, cfg)
            anomalies = inspect_dataset(name, df)
            all_anomalies[name] = anomalies
            dataframes[name] = df
            save_processed(name, df)
        except FileNotFoundError as exc:
            log.error("SKIP %s — %s", name, exc)

    # Fund master deep-dive
    if "fund_master" in dataframes:
        explore_fund_master(dataframes["fund_master"])

    # AMFI code cross-validation
    if "fund_master" in dataframes and "nav_history" in dataframes:
        validate_amfi_codes(dataframes["fund_master"], dataframes["nav_history"])

    # Final anomaly report
    print("\n" + "═"*70)
    print("  ANOMALY SUMMARY ACROSS ALL DATASETS")
    print("═"*70)
    total = 0
    for name, anomalies in all_anomalies.items():
        if anomalies:
            print(f"  {name}:")
            for a in anomalies:
                print(f"    {a}")
                total += 1
    if total == 0:
        print("  ✅ No anomalies detected across all 10 datasets.")
    print("═"*70)
    log.info("Data ingestion complete. %d datasets loaded.", len(dataframes))


if __name__ == "__main__":
    main()
