"""
Generate realistic Mutual Fund datasets for the Bluestock MF Capstone project.
These mirror the structure of AMFI / Value Research data exports.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date, timedelta
import random

rng = np.random.default_rng(42)
RAW = Path(__file__).parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# ── SCHEME MASTER ────────────────────────────────────────────────────────────
SCHEMES = [
    (125497, "HDFC Top 100 Fund - Direct Plan - Growth", "HDFC Mutual Fund",       "Equity", "Large Cap", "Moderately High"),
    (119551, "SBI Bluechip Fund - Direct Plan - Growth",  "SBI Mutual Fund",        "Equity", "Large Cap", "Moderately High"),
    (120503, "ICICI Pru Bluechip Fund - Direct Plan - Growth","ICICI Prudential MF","Equity", "Large Cap", "Moderately High"),
    (118632, "Nippon India Large Cap Fund - Direct Plan - Growth","Nippon India MF","Equity", "Large Cap", "Moderately High"),
    (119092, "Axis Bluechip Fund - Direct Plan - Growth", "Axis Mutual Fund",       "Equity", "Large Cap", "Moderately High"),
    (120841, "Kotak Bluechip Fund - Direct Plan - Growth","Kotak Mahindra MF",      "Equity", "Large Cap", "Moderately High"),
    (100033, "Mirae Asset Large Cap Fund - Direct - Growth","Mirae Asset MF",       "Equity", "Large Cap", "High"),
    (108467, "DSP Top 100 Equity Fund - Direct Plan - Growth","DSP Mutual Fund",    "Equity", "Large Cap", "High"),
    (112090, "Franklin India Bluechip Fund - Direct - Growth","Franklin Templeton", "Equity", "Large Cap", "Moderately High"),
    (101539, "UTI Mastershare - Direct Plan - Growth",    "UTI Mutual Fund",        "Equity", "Large Cap", "Moderately High"),
    (130503, "Parag Parikh Flexi Cap Fund - Direct - Growth","PPFAS MF",           "Equity", "Flexi Cap",  "Moderately High"),
    (101305, "HDFC Mid-Cap Opportunities - Direct - Growth","HDFC Mutual Fund",    "Equity", "Mid Cap",   "High"),
    (100356, "Nippon India Small Cap Fund - Direct - Growth","Nippon India MF",    "Equity", "Small Cap", "Very High"),
    (103504, "SBI Small Cap Fund - Direct Plan - Growth", "SBI Mutual Fund",        "Equity", "Small Cap", "Very High"),
    (107494, "HDFC Balanced Advantage Fund - Direct - Growth","HDFC Mutual Fund",  "Hybrid", "Dynamic Asset Allocation","Moderately High"),
    (108005, "ICICI Pru Equity & Debt Fund - Direct - Growth","ICICI Prudential MF","Hybrid","Aggressive Hybrid","Moderately High"),
    (110478, "SBI Magnum Gilt Fund - Direct Plan - Growth","SBI Mutual Fund",      "Debt",   "Gilt",      "Moderate"),
    (118701, "HDFC Corporate Bond Fund - Direct - Growth","HDFC Mutual Fund",      "Debt",   "Corporate Bond","Moderate"),
    (119597, "Axis Liquid Fund - Direct Plan - Growth",   "Axis Mutual Fund",       "Debt",   "Liquid",    "Low to Moderate"),
    (116230, "HDFC Liquid Fund - Direct Plan - Growth",   "HDFC Mutual Fund",       "Debt",   "Liquid",    "Low to Moderate"),
]

fund_master = pd.DataFrame(SCHEMES, columns=[
    "amfi_code","scheme_name","fund_house","category","sub_category","risk_grade"
])
fund_master["aum_cr"] = rng.integers(500, 50000, len(fund_master))
fund_master["expense_ratio_pct"] = np.round(rng.uniform(0.3, 1.2, len(fund_master)), 2)
fund_master["launch_date"] = pd.to_datetime(
    [date(2013, 1, 1) + timedelta(days=int(d)) for d in rng.integers(0, 365*3, len(fund_master))]
)
fund_master["benchmark"] = fund_master["category"].map({
    "Equity":"NIFTY 100 TRI","Hybrid":"NIFTY 500 TRI","Debt":"CRISIL Short Term Bond Index"
})
fund_master.to_csv(RAW / "fund_master.csv", index=False)
print(f"✓ fund_master.csv  {fund_master.shape}")

# ── NAV HISTORY ──────────────────────────────────────────────────────────────
dates = pd.bdate_range("2019-04-01", "2024-03-31")
nav_rows = []
BASE_NAVS = {row.amfi_code: rng.uniform(30, 200) for row in fund_master.itertuples()}

for code, base_nav in BASE_NAVS.items():
    nav = base_nav
    for d in dates:
        ret = rng.normal(0.0004, 0.012)
        nav = max(nav * (1 + ret), 0.5)
        nav_rows.append((code, d.date(), round(nav, 4)))

nav_history = pd.DataFrame(nav_rows, columns=["amfi_code","nav_date","nav"])
nav_history.to_csv(RAW / "nav_history.csv", index=False)
print(f"✓ nav_history.csv  {nav_history.shape}")

# ── RETURNS SUMMARY ──────────────────────────────────────────────────────────
returns_data = []
for code in BASE_NAVS:
    df_s = nav_history[nav_history.amfi_code == code].sort_values("nav_date")
    if len(df_s) < 252:
        continue
    nav_arr = df_s["nav"].values
    ret_1y = round((nav_arr[-1]/nav_arr[-252] - 1)*100, 2)
    ret_3y = round(((nav_arr[-1]/nav_arr[-756])**(1/3) - 1)*100, 2) if len(nav_arr) >= 756 else None
    ret_5y = round(((nav_arr[-1]/nav_arr[0])**(1/5) - 1)*100, 2)
    daily = pd.Series(nav_arr).pct_change().dropna()
    sharpe = round((daily.mean()*252) / (daily.std()*np.sqrt(252)), 4) if daily.std() > 0 else None
    returns_data.append([code, ret_1y, ret_3y, ret_5y, sharpe])

returns_df = pd.DataFrame(returns_data, columns=["amfi_code","return_1y_pct","return_3y_cagr_pct","return_5y_cagr_pct","sharpe_ratio"])
returns_df.to_csv(RAW / "returns_summary.csv", index=False)
print(f"✓ returns_summary.csv  {returns_df.shape}")

# ── PORTFOLIO HOLDINGS ────────────────────────────────────────────────────────
NSE_STOCKS = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN",
    "BHARTIARTL","ITC","KOTAKBANK","LT","HCLTECH","AXISBANK","ASIANPAINT",
    "BAJFINANCE","MARUTI","TITAN","WIPRO","SUNPHARMA","ULTRACEMCO"
]
holdings_rows = []
for code in [s[0] for s in SCHEMES if s[4] in ("Large Cap","Mid Cap","Flexi Cap")]:
    n_stocks = rng.integers(10, 20)
    stocks = rng.choice(NSE_STOCKS, n_stocks, replace=False).tolist()
    weights = rng.dirichlet(np.ones(n_stocks))
    for stk, wt in zip(stocks, weights):
        holdings_rows.append((code, stk, round(wt*100, 2), round(rng.uniform(50,3000), 2)))

holdings = pd.DataFrame(holdings_rows, columns=["amfi_code","stock_symbol","weight_pct","market_value_cr"])
holdings.to_csv(RAW / "portfolio_holdings.csv", index=False)
print(f"✓ portfolio_holdings.csv  {holdings.shape}")

# ── BENCHMARK (NIFTY 100) ────────────────────────────────────────────────────
bm_nav = 10000.0
bm_rows = []
for d in dates:
    ret = rng.normal(0.00035, 0.011)
    bm_nav = max(bm_nav * (1 + ret), 1)
    bm_rows.append((d.date(), round(bm_nav, 2)))

benchmark = pd.DataFrame(bm_rows, columns=["date","nifty100_tri"])
benchmark.to_csv(RAW / "benchmark_nifty100.csv", index=False)
print(f"✓ benchmark_nifty100.csv  {benchmark.shape}")

# ── SIP TRANSACTIONS ─────────────────────────────────────────────────────────
sip_rows = []
investor_ids = [f"INV{i:04d}" for i in range(1, 201)]
for inv in investor_ids:
    code = int(rng.choice([s[0] for s in SCHEMES]))
    sip_amt = int(rng.choice([500, 1000, 2000, 5000, 10000]))
    start = date(2019, 4, 1) + timedelta(days=int(rng.integers(0, 365*2)))
    for m in range(int(rng.integers(6, 60))):
        sip_date = start + timedelta(days=m*30)
        if sip_date > date(2024, 3, 31):
            break
        close_navs = nav_history[(nav_history.amfi_code == code)]["nav"]
        if len(close_navs) == 0:
            continue
        nav_val = float(close_navs.sample(1, random_state=m).values[0])
        units = round(sip_amt / nav_val, 4)
        sip_rows.append((inv, code, sip_date, sip_amt, round(nav_val, 4), units))

sip_df = pd.DataFrame(sip_rows, columns=["investor_id","amfi_code","transaction_date","sip_amount","nav_at_purchase","units_allotted"])
sip_df.to_csv(RAW / "sip_transactions.csv", index=False)
print(f"✓ sip_transactions.csv  {sip_df.shape}")

# ── LUMPSUM TRANSACTIONS ──────────────────────────────────────────────────────
lump_rows = []
for _ in range(500):
    inv = rng.choice(investor_ids)
    code = int(rng.choice([s[0] for s in SCHEMES]))
    t_date = date(2019, 4, 1) + timedelta(days=int(rng.integers(0, 365*5)))
    amount = int(rng.choice([10000, 25000, 50000, 100000, 250000, 500000]))
    close_navs = nav_history[nav_history.amfi_code == code]["nav"]
    if len(close_navs) == 0:
        continue
    nav_val = float(close_navs.sample(1).values[0])
    units = round(amount / nav_val, 4)
    lump_rows.append((inv, code, t_date, amount, round(nav_val, 4), units))

lump_df = pd.DataFrame(lump_rows, columns=["investor_id","amfi_code","transaction_date","amount","nav_at_purchase","units_allotted"])
lump_df.to_csv(RAW / "lumpsum_transactions.csv", index=False)
print(f"✓ lumpsum_transactions.csv  {lump_df.shape}")

# ── INVESTOR PROFILES ─────────────────────────────────────────────────────────
ages = rng.integers(22, 65, 200)
profiles = pd.DataFrame({
    "investor_id": investor_ids,
    "age": ages,
    "city": rng.choice(["Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Pune","Kolkata","Ahmedabad"], 200),
    "risk_profile": rng.choice(["Conservative","Moderate","Aggressive"], 200, p=[0.25,0.45,0.30]),
    "annual_income_lakh": np.round(rng.uniform(5, 150, 200), 1),
    "kyc_status": rng.choice(["Verified","Pending"], 200, p=[0.92, 0.08]),
    "registration_date": pd.to_datetime(
        [date(2018, 1, 1) + timedelta(days=int(d)) for d in rng.integers(0, 365*3, 200)]
    )
})
profiles.to_csv(RAW / "investor_profiles.csv", index=False)
print(f"✓ investor_profiles.csv  {profiles.shape}")

# ── DIVIDEND HISTORY ──────────────────────────────────────────────────────────
div_rows = []
dividend_funds = [s[0] for s in SCHEMES if s[3] == "Equity"][:8]
for code in dividend_funds:
    for year in range(2019, 2024):
        for qtr in [3, 6, 9, 12]:
            div_date = date(year, qtr, 15)
            if div_date > date(2024, 3, 31):
                continue
            div_rows.append((code, div_date, round(rng.uniform(0.5, 5.0), 2), "Per Unit"))

div_df = pd.DataFrame(div_rows, columns=["amfi_code","dividend_date","dividend_per_unit","dividend_type"])
div_df.to_csv(RAW / "dividend_history.csv", index=False)
print(f"✓ dividend_history.csv  {div_df.shape}")

# ── RISK METRICS ──────────────────────────────────────────────────────────────
risk_rows = []
for code in [s[0] for s in SCHEMES]:
    df_s = nav_history[nav_history.amfi_code == code].sort_values("nav_date")
    daily_ret = df_s["nav"].pct_change().dropna()
    bm_ret = benchmark["nifty100_tri"].pct_change().dropna()
    min_len = min(len(daily_ret), len(bm_ret))
    r = daily_ret.values[-min_len:]
    b = bm_ret.values[-min_len:]
    vol = round(float(np.std(r) * np.sqrt(252) * 100), 4)
    var_95 = round(float(np.percentile(r, 5) * 100), 4)
    max_dd = 0.0
    peak = -np.inf
    for nav_v in df_s["nav"].values:
        if nav_v > peak:
            peak = nav_v
        dd = (nav_v - peak) / peak
        if dd < max_dd:
            max_dd = dd
    beta = round(float(np.cov(r, b)[0,1] / np.var(b)), 4) if np.var(b) > 0 else 1.0
    risk_rows.append((code, vol, var_95, round(max_dd*100, 4), beta))

risk_df = pd.DataFrame(risk_rows, columns=["amfi_code","annualised_volatility_pct","var_95_daily_pct","max_drawdown_pct","beta"])
risk_df.to_csv(RAW / "risk_metrics.csv", index=False)
print(f"✓ risk_metrics.csv  {risk_df.shape}")

print("\n All 10 datasets generated in data/raw/")
