"""
compute_metrics.py — Performance Analytics Engine
Bluestock Mutual Fund Capstone — D4

Computes for all 40 schemes:
  1. Daily returns + distribution validation
  2. CAGR: 1yr, 3yr, full-period
  3. Sharpe Ratio  (Rf = 6.5% p.a.)
  4. Sortino Ratio (downside deviation only)
  5. Alpha & Beta  (OLS vs NIFTY 100)
  6. Maximum Drawdown + worst period
  7. Tracking Error vs NIFTY50 / NIFTY100
  8. Fund Scorecard (0–100 composite)

Outputs:
  data/processed/daily_returns.csv
  data/processed/fund_scorecard.csv
  data/processed/alpha_beta.csv
  data/processed/cagr_table.csv
  data/processed/risk_metrics_computed.csv
"""

import warnings
warnings.filterwarnings("ignore")
import logging, sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).resolve().parent.parent
RAW       = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(BASE / "data" / "performance_analytics.log", "w")],
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
RF_ANNUAL     = 0.065          # RBI repo rate proxy
RF_DAILY      = (1 + RF_ANNUAL) ** (1/252) - 1
TRADING_DAYS  = 252
BENCHMARK_PRIMARY = "NIFTY100"   # Beta/Alpha benchmark
BENCHMARK_SECONDARY = "NIFTY50"


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
def load_data():
    log.info("Loading raw datasets …")
    nav  = (pd.read_csv(RAW / "02_nav_history.csv", parse_dates=["date"])
              .rename(columns={"date": "date"}))
    fm   = pd.read_csv(RAW / "01_fund_master.csv")
    perf_path = RAW / "07_scheme_performance.csv"
    if not perf_path.exists():
        perf_path = PROCESSED / "07_scheme_performance_clean.csv"
    perf = pd.read_csv(perf_path)

    # Load all benchmark series available in raw data
    bm_dict = {}
    for bm_file in sorted(RAW.glob("benchmark_*.csv")):
        idx_name = bm_file.stem.replace("benchmark_", "").upper()
        df_bm = pd.read_csv(bm_file, parse_dates=["date"]).set_index("date")
        bm_dict[idx_name] = df_bm.iloc[:, 0].sort_index().rename(idx_name)
    if BENCHMARK_PRIMARY not in bm_dict:
        raise ValueError(f"Required benchmark '{BENCHMARK_PRIMARY}' not found in {RAW}")

    # Pivot NAV to wide format (date x scheme)
    nav_wide = nav.pivot_table(index="date", columns="amfi_code", values="nav").sort_index()
    nav_wide = nav_wide.ffill()                      # forward-fill any missing trading days
    log.info("  NAV pivot: %s  |  date range: %s -> %s",
             nav_wide.shape, nav_wide.index[0].date(), nav_wide.index[-1].date())

    # Benchmark series aligned to NAV dates
    for idx_name, series in bm_dict.items():
        bm_dict[idx_name] = series.reindex(nav_wide.index).ffill()

    return nav_wide, fm, bm_dict, perf


# ══════════════════════════════════════════════════════════════════════════════
# 1. DAILY RETURNS
# ══════════════════════════════════════════════════════════════════════════════
def compute_daily_returns(nav_wide: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing daily returns …")
    ret = nav_wide.pct_change().iloc[1:]          # drop first NaN row

    # Validation
    suspicious = (ret.abs() > 0.20).sum().sum()
    if suspicious:
        log.warning("  %d returns > |20%%| — may indicate NAV restatement or data issue", suspicious)

    log.info("  Daily returns shape: %s", ret.shape)
    log.info("  Cross-scheme mean daily return: %.4f%%  std: %.4f%%",
             ret.mean().mean() * 100, ret.std().mean() * 100)
    log.info("  Skewness range: %.3f – %.3f", ret.skew().min(), ret.skew().max())
    log.info("  Kurtosis range: %.2f - %.2f  (normal ~= 0)", ret.kurt().min(), ret.kurt().max())

    ret.index.name = "date"
    return ret


# ══════════════════════════════════════════════════════════════════════════════
# 2. CAGR
# ══════════════════════════════════════════════════════════════════════════════
def compute_cagr(nav_wide: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing CAGR …")
    latest = nav_wide.index[-1]

    def _cagr(start_date, label):
        # Find nearest available date on or after start_date
        valid = nav_wide.index[nav_wide.index >= start_date]
        if len(valid) == 0:
            return pd.Series(np.nan, index=nav_wide.columns, name=label)
        actual_start = valid[0]
        n_days = (latest - actual_start).days
        n_years = n_days / 365.25
        nav_start = nav_wide.loc[actual_start]
        nav_end   = nav_wide.loc[latest]
        cagr = (nav_end / nav_start) ** (1 / n_years) - 1
        log.info("  CAGR %s: start=%s  n_years=%.2f", label, actual_start.date(), n_years)
        return pd.Series(cagr * 100, name=label)

    cagr_1yr = _cagr(latest - pd.DateOffset(years=1),   "cagr_1yr_pct")
    cagr_3yr = _cagr(latest - pd.DateOffset(years=3),   "cagr_3yr_pct")
    cagr_full= _cagr(nav_wide.index[0],                  "cagr_full_pct")

    df = pd.concat([cagr_1yr, cagr_3yr, cagr_full], axis=1)
    df.index.name = "amfi_code"
    df = df.round(4)
    log.info("  CAGR table: %s", df.shape)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3. SHARPE RATIO
# ══════════════════════════════════════════════════════════════════════════════
def compute_sharpe(ret: pd.DataFrame) -> pd.Series:
    log.info("Computing Sharpe Ratio (Rf=%.1f%%) …", RF_ANNUAL * 100)
    excess  = ret - RF_DAILY
    sharpe  = (excess.mean() / ret.std()) * np.sqrt(TRADING_DAYS)
    sharpe.name = "sharpe_ratio"
    log.info("  Sharpe range: %.3f – %.3f", sharpe.min(), sharpe.max())
    return sharpe.round(4)


# ══════════════════════════════════════════════════════════════════════════════
# 4. SORTINO RATIO
# ══════════════════════════════════════════════════════════════════════════════
def compute_sortino(ret: pd.DataFrame) -> pd.Series:
    log.info("Computing Sortino Ratio …")
    excess = ret - RF_DAILY
    # Downside deviation: std of returns below zero
    downside = ret.copy()
    downside[downside > 0] = 0
    downside_std = downside.std() * np.sqrt(TRADING_DAYS)
    sortino = (excess.mean() * TRADING_DAYS) / downside_std
    sortino.name = "sortino_ratio"
    log.info("  Sortino range: %.3f – %.3f", sortino.min(), sortino.max())
    return sortino.round(4)


# ══════════════════════════════════════════════════════════════════════════════
# 5. ALPHA & BETA (OLS regression vs NIFTY100)
# ══════════════════════════════════════════════════════════════════════════════
def compute_alpha_beta(ret: pd.DataFrame, bm_dict: dict) -> pd.DataFrame:
    log.info("Computing Alpha & Beta (OLS vs %s) …", BENCHMARK_PRIMARY)
    bm_ret = bm_dict[BENCHMARK_PRIMARY].pct_change().reindex(ret.index).dropna()
    common = ret.index.intersection(bm_ret.index)
    bm_aligned = bm_ret.loc[common].values

    rows = []
    for code in ret.columns:
        fund_aligned = ret[code].loc[common].values
        # scipy OLS: y = fund, x = benchmark
        result = stats.linregress(x=bm_aligned, y=fund_aligned)
        alpha_daily   = result.intercept
        alpha_annual  = alpha_daily * TRADING_DAYS * 100   # annualised, in %
        beta          = result.slope
        r_squared     = result.rvalue ** 2
        te_vs_bm      = np.std(fund_aligned - bm_aligned) * np.sqrt(TRADING_DAYS) * 100

        rows.append({
            "amfi_code":          code,
            "alpha_annual_pct":   round(alpha_annual, 4),
            "beta":               round(beta, 4),
            "r_squared":          round(r_squared, 4),
            "tracking_error_pct": round(te_vs_bm, 4),
            "intercept_daily":    round(alpha_daily, 6),
        })

    df = pd.DataFrame(rows).set_index("amfi_code")
    log.info("  Alpha range: %.2f%% – %.2f%%  Beta range: %.3f – %.3f",
             df.alpha_annual_pct.min(), df.alpha_annual_pct.max(),
             df.beta.min(), df.beta.max())
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 6. MAXIMUM DRAWDOWN + WORST PERIOD
# ══════════════════════════════════════════════════════════════════════════════
def compute_max_drawdown(nav_wide: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing Maximum Drawdown …")
    rows = []
    for code in nav_wide.columns:
        series = nav_wide[code].dropna()
        # Rolling maximum (running peak)
        running_max = series.cummax()
        drawdown    = series / running_max - 1
        max_dd      = drawdown.min()
        trough_date = drawdown.idxmin()
        # Find the peak just before the trough
        peak_date   = running_max.loc[:trough_date].idxmax()
        # Recovery: first date after trough where NAV exceeds prior peak
        peak_nav    = running_max.loc[trough_date]
        recovery    = series.loc[trough_date:]
        recovered   = recovery[recovery >= peak_nav]
        recovery_date = recovered.index[0] if len(recovered) > 0 else pd.NaT
        dd_duration   = (trough_date - peak_date).days if pd.notna(peak_date) else np.nan
        rec_duration  = (recovery_date - trough_date).days if pd.notna(recovery_date) else np.nan

        rows.append({
            "amfi_code":           code,
            "max_drawdown_pct":    round(max_dd * 100, 4),
            "peak_date":           peak_date.date() if pd.notna(peak_date) else None,
            "trough_date":         trough_date.date(),
            "recovery_date":       recovery_date.date() if pd.notna(recovery_date) else "Not recovered",
            "drawdown_duration_days":  int(dd_duration) if pd.notna(dd_duration) else -1,
            "recovery_duration_days":  int(rec_duration) if pd.notna(rec_duration) else -1,
        })

    df = pd.DataFrame(rows).set_index("amfi_code")
    log.info("  Max DD range: %.1f%% – %.1f%%",
             df.max_drawdown_pct.min(), df.max_drawdown_pct.max())
    worst = df.nsmallest(3, "max_drawdown_pct")
    for idx, row in worst.iterrows():
        log.info("  Worst DD: code=%s  %.2f%%  peak=%s -> trough=%s",
                 idx, row.max_drawdown_pct, row.peak_date, row.trough_date)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 7. VOLATILITY & RISK SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
def compute_volatility(ret: pd.DataFrame) -> pd.DataFrame:
    log.info("Computing volatility metrics …")
    ann_vol   = ret.std() * np.sqrt(TRADING_DAYS) * 100
    ann_ret   = ret.mean() * TRADING_DAYS * 100
    var_95    = ret.quantile(0.05) * 100
    cvar_95   = ret[ret <= ret.quantile(0.05)].mean() * 100
    skew      = ret.skew()
    kurt      = ret.kurt()
    pos_days  = (ret > 0).sum()
    neg_days  = (ret < 0).sum()
    win_rate  = pos_days / (pos_days + neg_days) * 100

    df = pd.DataFrame({
        "ann_vol_pct":       ann_vol.round(4),
        "ann_return_pct":    ann_ret.round(4),
        "var_95_pct":        var_95.round(4),
        "cvar_95_pct":       cvar_95.round(4),
        "skewness":          skew.round(4),
        "excess_kurtosis":   kurt.round(4),
        "win_rate_pct":      win_rate.round(2),
        "positive_days":     pos_days,
        "negative_days":     neg_days,
    })
    df.index.name = "amfi_code"
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 8. TRACKING ERROR (vs both benchmarks)
# ══════════════════════════════════════════════════════════════════════════════
def compute_tracking_error(ret: pd.DataFrame, bm_dict: dict) -> pd.DataFrame:
    available = [name for name in [BENCHMARK_PRIMARY, BENCHMARK_SECONDARY] if name in bm_dict]
    log.info("Computing Tracking Error vs %s …", " & ".join(available))
    rows = {}
    for bm_name in available:
        bm_ret = bm_dict[bm_name].pct_change().reindex(ret.index).dropna()
        common = ret.index.intersection(bm_ret.index)
        te = (ret.loc[common].subtract(bm_ret.loc[common], axis=0)
                 .std() * np.sqrt(TRADING_DAYS) * 100)
        rows[f"te_vs_{bm_name.lower()}_pct"] = te.round(4)
    if not rows:
        raise ValueError("No benchmark series available for tracking error computation")
    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 9. FUND SCORECARD (0–100)
# ══════════════════════════════════════════════════════════════════════════════
def compute_scorecard(cagr: pd.DataFrame, sharpe: pd.Series,
                      alpha_beta: pd.DataFrame, dd: pd.DataFrame,
                      fm: pd.DataFrame) -> pd.DataFrame:
    """
    Composite score:
      30% × 3yr CAGR rank (higher = better)
      25% × Sharpe rank   (higher = better)
      20% × Alpha rank    (higher = better)
      15% × Expense ratio rank (lower expense = better → invert rank)
      10% × Max DD rank   (less negative = better → invert rank)
    """
    log.info("Building Fund Scorecard …")

    # Merge all signals
    expense = fm.set_index("amfi_code")["expense_ratio_pct"]
    df = pd.DataFrame({
        "cagr_3yr":   cagr["cagr_3yr_pct"],
        "sharpe":     sharpe,
        "alpha":      alpha_beta["alpha_annual_pct"],
        "expense":    expense,
        "max_dd":     dd["max_drawdown_pct"],
    }).dropna()

    n = len(df)

    def _rank_pct(series, ascending=False):
        """Return 0–100 percentile rank. ascending=False → higher value = higher score."""
        return series.rank(ascending=ascending, pct=True) * 100

    df["rank_cagr3yr"] = _rank_pct(df["cagr_3yr"],   ascending=False)
    df["rank_sharpe"]  = _rank_pct(df["sharpe"],      ascending=False)
    df["rank_alpha"]   = _rank_pct(df["alpha"],       ascending=False)
    df["rank_expense"] = _rank_pct(df["expense"],     ascending=True)   # invert: lower expense → higher rank
    df["rank_maxdd"]   = _rank_pct(df["max_dd"],      ascending=False)  # invert: less negative → higher rank

    df["composite_score"] = (
        0.30 * df["rank_cagr3yr"] +
        0.25 * df["rank_sharpe"]  +
        0.20 * df["rank_alpha"]   +
        0.15 * df["rank_expense"] +
        0.10 * df["rank_maxdd"]
    ).round(2)

    df["scorecard_rank"] = df["composite_score"].rank(ascending=False).astype(int)
    df = df.sort_values("composite_score", ascending=False)

    log.info("  Scorecard shape: %s", df.shape)
    log.info("  Top 5:")
    for idx, row in df.head(5).iterrows():
        name = fm[fm.amfi_code==idx]["scheme_name"].values
        label = name[0][:45] if len(name) else str(idx)
        log.info("    #%d [%.1f]  %s", row.scorecard_rank, row.composite_score, label)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def run_all() -> dict:
    log.info("=" * 60)
    log.info("Bluestock MF — D4 Performance Analytics")
    log.info("=" * 60)

    nav_wide, fm, bm_dict, perf = load_data()

    ret     = compute_daily_returns(nav_wide)
    cagr    = compute_cagr(nav_wide)
    sharpe  = compute_sharpe(ret)
    sortino = compute_sortino(ret)
    ab      = compute_alpha_beta(ret, bm_dict)
    dd      = compute_max_drawdown(nav_wide)
    vol     = compute_volatility(ret)
    te      = compute_tracking_error(ret, bm_dict)
    score   = compute_scorecard(cagr, sharpe, ab, dd, fm)

    # ── Merge master output ────────────────────────────────────────────────────
    meta_cols = ["scheme_name","fund_house","category","sub_category","expense_ratio_pct"]
    if "plan" in fm.columns:
        meta_cols.insert(4, "plan")

    meta = fm.set_index("amfi_code")[meta_cols]
    if "plan" not in meta.columns:
        meta["plan"] = np.nan

    # aum_crore comes from scheme_performance
    if "aum_crore" in perf.columns:
        meta = meta.join(perf.set_index("amfi_code")[["aum_crore"]], how="left")

    full = (meta
            .join(cagr,    how="left")
            .join(sharpe,  how="left")
            .join(sortino, how="left")
            .join(ab,      how="left")
            .join(dd[["max_drawdown_pct","peak_date","trough_date",
                       "recovery_date","drawdown_duration_days","recovery_duration_days"]], how="left")
            .join(vol,     how="left")
            .join(te,      how="left"))

    # ── Save CSVs ──────────────────────────────────────────────────────────────
    log.info("\nSaving processed CSVs …")

    ret.to_csv(PROCESSED / "daily_returns.csv")
    log.info("  daily_returns.csv         %s", ret.shape)

    cagr.to_csv(PROCESSED / "cagr_table.csv")
    log.info("  cagr_table.csv            %s", cagr.shape)

    ab_out = ab.join(meta[["scheme_name","fund_house","category","plan"]], how="left")
    ab_out = ab_out[["scheme_name","fund_house","category","plan",
                     "alpha_annual_pct","beta","r_squared","tracking_error_pct"]]
    ab_out.to_csv(PROCESSED / "alpha_beta.csv")
    log.info("  alpha_beta.csv            %s", ab_out.shape)

    sc_out = score.join(meta[["scheme_name","fund_house","category","plan"]], how="left")
    sc_out = sc_out[["scheme_name","fund_house","category","plan",
                     "composite_score","scorecard_rank",
                     "cagr_3yr","sharpe","alpha","expense","max_dd",
                     "rank_cagr3yr","rank_sharpe","rank_alpha","rank_expense","rank_maxdd"]]
    sc_out.to_csv(PROCESSED / "fund_scorecard.csv")
    log.info("  fund_scorecard.csv        %s", sc_out.shape)

    full.to_csv(PROCESSED / "risk_metrics_computed.csv")
    log.info("  risk_metrics_computed.csv %s", full.shape)

    log.info("\n" + "=" * 60)
    log.info("Performance analytics complete.")
    log.info("=" * 60)

    return {
        "nav_wide": nav_wide, "ret": ret, "fm": fm, "bm_dict": bm_dict,
        "cagr": cagr, "sharpe": sharpe, "sortino": sortino,
        "alpha_beta": ab, "drawdown": dd, "vol": vol,
        "tracking_error": te, "scorecard": score,
        "full_metrics": full,
    }


if __name__ == "__main__":
    results = run_all()
