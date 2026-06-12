"""
eda_charts.py — Generate all 15+ EDA charts for Bluestock MF Capstone
Uses real provided datasets (01_fund_master.csv through 10_benchmark_indices.csv)
Exports PNG charts to reports/charts/ and HTML to notebooks/
"""

import warnings
warnings.filterwarnings("ignore")

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE    = Path(__file__).resolve().parent.parent
RAW     = BASE / "data" / "raw"
CHARTS  = BASE / "reports" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Style ─────────────────────────────────────────────────────────────────────
BRAND_BLUE  = "#1a3c6b"
BRAND_TEAL  = "#00a8a8"
BRAND_RED   = "#e63946"
BRAND_AMBER = "#f4a261"
BRAND_GREEN = "#2a9d8f"
PALETTE_10  = ["#1a3c6b","#00a8a8","#e63946","#f4a261","#2a9d8f",
               "#457b9d","#e76f51","#264653","#a8dadc","#6d6875"]

sns.set_theme(style="whitegrid", font_scale=1.1)
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 14,
    "axes.titleweight": "bold",
    "figure.facecolor": "white",
})

PLOTLY_LAYOUT = dict(
    font_family="Arial",
    paper_bgcolor="white",
    plot_bgcolor="white",
    title_font_size=16,
    title_font_color=BRAND_BLUE,
    margin=dict(l=60, r=40, t=70, b=60),
)

def save_plotly(fig, name):
    fig.write_image(str(CHARTS / f"{name}.png"), width=1200, height=650, scale=2)
    fig.write_html(str(CHARTS / f"{name}.html"))
    print(f"  ✓ {name}.png")

def save_mpl(fig, name):
    fig.savefig(str(CHARTS / f"{name}.png"), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  ✓ {name}.png")


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
print("Loading datasets …")
fm   = pd.read_csv(RAW / "fund_master.csv")
nav  = pd.read_csv(RAW / "nav_history.csv",    parse_dates=["date"])
aum  = pd.read_csv(RAW / "aum_by_fund_house.csv", parse_dates=["date"])
sip  = pd.read_csv(RAW / "monthly_sip_inflows.csv")
cat  = pd.read_csv(RAW / "category_inflows.csv")
fol  = pd.read_csv(RAW / "industry_folio_count.csv")
perf = pd.read_csv(RAW / "scheme_performance.csv")
txn  = pd.read_csv(RAW / "investor_transactions.csv", parse_dates=["transaction_date"])
ph   = pd.read_csv(RAW / "portfolio_holdings.csv")
bm   = pd.read_csv(RAW / "benchmark_indices.csv", parse_dates=["date"])

# Derived
nav  = nav.merge(fm[["amfi_code","scheme_name","fund_house","category","plan","sub_category"]],
                 on="amfi_code", how="left")
nav["nav_date"] = nav["date"]
sip["month_dt"] = pd.to_datetime(sip["month"])
cat["month_dt"] = pd.to_datetime(cat["month"])

print(f"  nav: {nav.shape}  txn: {txn.shape}  aum: {aum.shape}")
print("All data loaded.\n")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 1 — NAV Trend: All 40 schemes 2022–2026 (Plotly)
# Highlight 2023 bull run and 2024 corrections
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 01: NAV Trend …")

# Normalise NAV to 100 at start for comparability
nav_pivot = nav.pivot_table(index="date", columns="amfi_code", values="nav").ffill()
nav_norm  = nav_pivot.div(nav_pivot.iloc[0]) * 100

fig = go.Figure()

# Dim all lines first
for col in nav_norm.columns:
    name = fm[fm.amfi_code==col]["scheme_name"].values
    label = name[0][:35] if len(name) else str(col)
    fig.add_trace(go.Scatter(
        x=nav_norm.index, y=nav_norm[col],
        mode="lines", name=label,
        line=dict(width=0.8, color="rgba(100,130,180,0.25)"),
        showlegend=False, hovertemplate=f"{label}<br>%{{y:.1f}}<extra></extra>"
    ))

# Benchmark NIFTY50 on top
nifty = bm[bm.index_name=="NIFTY50"].set_index("date")["close_value"]
nifty_norm = nifty / nifty.iloc[0] * 100
fig.add_trace(go.Scatter(
    x=nifty_norm.index, y=nifty_norm.values,
    mode="lines", name="NIFTY50 (Benchmark)",
    line=dict(width=2.5, color=BRAND_AMBER, dash="dash"),
))

# Add shaded regions
fig.add_vrect(x0="2023-01-01", x1="2023-12-31",
    fillcolor="rgba(42,157,143,0.12)", line_width=0,
    annotation_text="2023 Bull Run", annotation_position="top left",
    annotation_font=dict(color=BRAND_GREEN, size=11))

fig.add_vrect(x0="2024-04-01", x1="2024-06-30",
    fillcolor="rgba(230,57,70,0.10)", line_width=0,
    annotation_text="2024 Election Volatility", annotation_position="top left",
    annotation_font=dict(color=BRAND_RED, size=11))

fig.add_vrect(x0="2024-09-01", x1="2024-12-31",
    fillcolor="rgba(230,57,70,0.10)", line_width=0,
    annotation_text="2024 Q4 Correction", annotation_position="top right",
    annotation_font=dict(color=BRAND_RED, size=11))

fig.update_layout(
    **PLOTLY_LAYOUT,
    title="NAV Trend — All 40 Schemes (Indexed to 100, Jan 2022)",
    xaxis_title="Date", yaxis_title="Indexed NAV (Base = 100)",
    legend=dict(x=0.01, y=0.99),
    height=600
)
fig.update_xaxes(showgrid=True, gridcolor="#eaeaea")
fig.update_yaxes(showgrid=True, gridcolor="#eaeaea")
save_plotly(fig, "01_nav_trend_all_schemes")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2 — AUM Growth Grouped Bar by Fund House (Seaborn)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 02: AUM Growth Bar …")

aum["year"] = aum["date"].dt.year
aum_yr = (aum.groupby(["year","fund_house"])["aum_lakh_crore"]
            .mean().reset_index())
aum_yr = aum_yr[aum_yr["year"].isin([2022,2023,2024,2025])]

fig, ax = plt.subplots(figsize=(14, 7))
palette = dict(zip(sorted(aum_yr["fund_house"].unique()), PALETTE_10))

sns.barplot(data=aum_yr, x="fund_house", y="aum_lakh_crore", hue="year",
            palette="Blues_d", ax=ax, edgecolor="white")

# Highlight SBI
sbi_data = aum_yr[(aum_yr.fund_house=="SBI Mutual Fund") & (aum_yr.year==2025)]
if not sbi_data.empty:
    ax.annotate(
        f"SBI ₹{sbi_data['aum_lakh_crore'].values[0]:.1f}L Cr\n(Market Leader)",
        xy=(0, sbi_data["aum_lakh_crore"].values[0]),
        xytext=(1.5, sbi_data["aum_lakh_crore"].values[0] + 0.8),
        arrowprops=dict(arrowstyle="->", color=BRAND_RED, lw=2),
        fontsize=11, color=BRAND_RED, fontweight="bold",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=BRAND_RED, alpha=0.9)
    )

ax.set_title("AUM by Fund House 2022–2025 (₹ Lakh Crore)", fontsize=15, fontweight="bold")
ax.set_xlabel("Fund House", fontsize=12)
ax.set_ylabel("Average AUM (₹ Lakh Crore)", fontsize=12)
ax.tick_params(axis="x", rotation=30)
ax.legend(title="Year", loc="upper right")
ax.spines[["top","right"]].set_visible(False)
plt.tight_layout()
save_mpl(fig, "02_aum_growth_by_fund_house")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 3 — SIP Inflow Time-Series (Plotly)
# Annotate Dec 2025 ₹31,002 Cr all-time high
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 03: SIP Inflow Time-Series …")

sip_sorted = sip.sort_values("month_dt")
peak_idx   = sip_sorted["sip_inflow_crore"].idxmax()
peak_row   = sip_sorted.loc[peak_idx]

fig = go.Figure()

# Area fill
fig.add_trace(go.Scatter(
    x=sip_sorted["month_dt"], y=sip_sorted["sip_inflow_crore"],
    mode="lines+markers",
    fill="tozeroy",
    fillcolor="rgba(0,168,168,0.15)",
    line=dict(color=BRAND_TEAL, width=2.5),
    marker=dict(size=6, color=BRAND_TEAL),
    name="Monthly SIP Inflow",
    hovertemplate="%{x|%b %Y}<br>₹%{y:,.0f} Cr<extra></extra>"
))

# Moving average
ma3 = sip_sorted["sip_inflow_crore"].rolling(3).mean()
fig.add_trace(go.Scatter(
    x=sip_sorted["month_dt"], y=ma3,
    mode="lines", name="3M Moving Avg",
    line=dict(color=BRAND_AMBER, width=2, dash="dot"),
))

# Annotate peak
fig.add_annotation(
    x=peak_row["month_dt"], y=peak_row["sip_inflow_crore"],
    text=f"<b>₹{peak_row['sip_inflow_crore']:,.0f} Cr</b><br>All-Time High<br>Dec 2025",
    showarrow=True, arrowhead=2, arrowcolor=BRAND_RED,
    font=dict(color=BRAND_RED, size=13),
    bgcolor="white", bordercolor=BRAND_RED, borderwidth=1.5,
    ax=40, ay=-60
)

fig.update_layout(
    **PLOTLY_LAYOUT,
    title="Monthly SIP Inflows — Jan 2022 to Dec 2025",
    xaxis_title="Month", yaxis_title="SIP Inflow (₹ Crore)",
    yaxis=dict(tickformat=",.0f"),
    legend=dict(x=0.01, y=0.99),
    height=500
)
save_plotly(fig, "03_sip_inflow_timeseries")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 4 — Category Inflow Heatmap (Seaborn)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 04: Category Inflow Heatmap …")

cat_pivot = cat.pivot_table(index="category", columns="month", values="net_inflow_crore", aggfunc="sum")
cat_pivot = cat_pivot[sorted(cat_pivot.columns)]
# Rename months for display
col_labels = {c: pd.to_datetime(c).strftime("%b %y") for c in cat_pivot.columns}
cat_display = cat_pivot.rename(columns=col_labels)

fig, ax = plt.subplots(figsize=(15, 7))
mask = cat_display.isna()
cmap = sns.diverging_palette(10, 145, s=80, l=55, as_cmap=True)

sns.heatmap(cat_display, ax=ax, cmap=cmap, center=0,
            annot=True, fmt=".0f", linewidths=0.5,
            linecolor="#e0e0e0", mask=mask,
            cbar_kws={"label": "Net Inflow (₹ Crore)", "shrink": 0.7},
            annot_kws={"size": 9})

ax.set_title("Category Net Inflows — Monthly Heatmap (₹ Crore)", fontsize=15, fontweight="bold", pad=15)
ax.set_xlabel("Month", fontsize=12)
ax.set_ylabel("Fund Category", fontsize=12)
ax.tick_params(axis="x", rotation=30, labelsize=10)
ax.tick_params(axis="y", rotation=0, labelsize=10)
plt.tight_layout()
save_mpl(fig, "04_category_inflow_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 5 — Investor Demographics: Pie + Box Plot (Matplotlib)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 05: Investor Demographics …")

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# 5a — Age group pie
age_sip = (txn[txn.transaction_type=="SIP"]
           .groupby("age_group")["amount_inr"].sum().reset_index())
age_order = ["18-25","26-35","36-45","46-55","56+"]
age_sip = age_sip.set_index("age_group").reindex(age_order).reset_index()
colors_age = ["#a8dadc","#457b9d","#1d3557","#e63946","#f4a261"]

wedges, texts, autotexts = axes[0].pie(
    age_sip["amount_inr"],
    labels=age_sip["age_group"],
    autopct="%1.1f%%",
    colors=colors_age,
    pctdistance=0.8,
    startangle=140,
    wedgeprops=dict(edgecolor="white", linewidth=2)
)
for at in autotexts:
    at.set_fontsize(10)
    at.set_fontweight("bold")
axes[0].set_title("SIP Amount by Age Group", fontweight="bold")

# 5b — Box plot SIP amount by age group
sip_txn = txn[txn.transaction_type == "SIP"]
bp_data = [sip_txn[sip_txn.age_group==ag]["amount_inr"].dropna().values
           for ag in age_order]
bp = axes[1].boxplot(bp_data, labels=age_order, patch_artist=True,
                     medianprops=dict(color="white", linewidth=2.5),
                     flierprops=dict(marker="o", markersize=3, alpha=0.4))
for patch, color in zip(bp["boxes"], colors_age):
    patch.set_facecolor(color)
    patch.set_alpha(0.85)
axes[1].set_title("SIP Amount Distribution by Age Group", fontweight="bold")
axes[1].set_xlabel("Age Group")
axes[1].set_ylabel("SIP Amount (₹)")
axes[1].tick_params(axis="x", rotation=15)
axes[1].spines[["top","right"]].set_visible(False)

# 5c — Gender split pie
gender_data = txn.groupby("gender")["amount_inr"].sum()
axes[2].pie(gender_data, labels=gender_data.index, autopct="%1.1f%%",
            colors=[BRAND_TEAL, BRAND_BLUE],
            wedgeprops=dict(edgecolor="white", linewidth=2),
            startangle=90)
axes[2].set_title("Transaction Amount by Gender", fontweight="bold")

fig.suptitle("Investor Demographics Analysis", fontsize=16, fontweight="bold", y=1.01)
plt.tight_layout()
save_mpl(fig, "05_investor_demographics")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 6 — Geographic Distribution (Matplotlib)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 06: Geographic Distribution …")

fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# 6a — SIP by state horizontal bar
state_sip = (txn[txn.transaction_type=="SIP"]
             .groupby("state")["amount_inr"].sum()
             .sort_values(ascending=True))

colors_bar = [BRAND_RED if s == state_sip.index[-1] else BRAND_BLUE for s in state_sip.index]
bars = axes[0].barh(state_sip.index, state_sip.values / 1e7,
                    color=colors_bar, edgecolor="white", height=0.7)
axes[0].set_xlabel("SIP Amount (₹ Crore)", fontsize=11)
axes[0].set_title("SIP Inflow by State", fontweight="bold", fontsize=13)

for bar, val in zip(bars, state_sip.values):
    axes[0].text(val/1e7 + 0.1, bar.get_y() + bar.get_height()/2,
                 f"₹{val/1e7:.1f} Cr", va="center", fontsize=8.5)
axes[0].spines[["top","right"]].set_visible(False)
axes[0].set_xlim(0, state_sip.values[-1]/1e7 * 1.25)

# 6b — T30 vs B30 pie
tier_data = txn.groupby("city_tier")["amount_inr"].sum()
explode = (0.04, 0.04)
axes[1].pie(tier_data, labels=tier_data.index, autopct="%1.1f%%",
            colors=[BRAND_TEAL, BRAND_AMBER],
            wedgeprops=dict(edgecolor="white", linewidth=2.5),
            explode=explode, startangle=80,
            textprops={"fontsize": 12})
axes[1].set_title("T30 vs B30 City Tier Distribution\n(by Transaction Amount)", 
                  fontweight="bold", fontsize=13)

fig.suptitle("Geographic Distribution of Investments", fontsize=15, fontweight="bold")
plt.tight_layout()
save_mpl(fig, "06_geographic_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 7 — Folio Count Growth (Plotly)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 07: Folio Count Growth …")

fol["month_dt"] = pd.to_datetime(fol["month"])
fol_s = fol.sort_values("month_dt")

fig = go.Figure()

cols_map = {
    "equity_folios_crore":  ("Equity Folios",  BRAND_BLUE),
    "debt_folios_crore":    ("Debt Folios",    BRAND_TEAL),
    "hybrid_folios_crore":  ("Hybrid Folios",  BRAND_AMBER),
}
for col, (label, color) in cols_map.items():
    fig.add_trace(go.Scatter(
        x=fol_s["month_dt"], y=fol_s[col],
        mode="lines+markers", name=label,
        line=dict(width=2.5, color=color),
        marker=dict(size=7),
        stackgroup="one",
        hovertemplate=f"{label}: %{{y:.2f}} Cr<br>%{{x|%b %Y}}<extra></extra>"
    ))

# Total line
fig.add_trace(go.Scatter(
    x=fol_s["month_dt"], y=fol_s["total_folios_crore"],
    mode="lines+markers", name="Total Folios",
    line=dict(width=3, color=BRAND_RED, dash="solid"),
    marker=dict(size=9, symbol="diamond"),
    hovertemplate="Total: %{y:.2f} Cr<br>%{x|%b %Y}<extra></extra>"
))

# Key milestones
milestones = [
    ("2022-01", 13.26, "13.26 Cr Start"),
    ("2024-01", 17.78, "17.78 Cr"),
    ("2025-12", 26.12, "26.12 Cr\nAll-Time High"),
]
for m_date, val, label in milestones:
    dt = pd.to_datetime(m_date)
    fig.add_annotation(
        x=dt, y=val,
        text=f"<b>{label}</b>",
        showarrow=True, arrowhead=2, arrowcolor=BRAND_RED,
        font=dict(size=11, color=BRAND_RED),
        bgcolor="white", bordercolor=BRAND_RED, borderwidth=1.5,
        ax=30, ay=-50
    )

fig.update_layout(
    **PLOTLY_LAYOUT,
    title="Industry Folio Count Growth — Jan 2022 to Dec 2025 (Crore)",
    xaxis_title="Date", yaxis_title="Folio Count (Crore)",
    legend=dict(x=0.01, y=0.99), height=520
)
save_plotly(fig, "07_folio_count_growth")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 8 — NAV Return Correlation Matrix (Seaborn)
# 10 selected schemes (5 equity + 3 debt + 2 hybrid) Direct plans
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 08: Return Correlation Matrix …")

# Pick 10 diverse schemes
selected_codes = (
    fm[(fm.plan=="Direct") & (fm.category=="Equity")]["amfi_code"].head(6).tolist() +
    fm[(fm.plan=="Direct") & (fm.category=="Debt")]["amfi_code"].head(2).tolist() +
    fm[(fm.plan=="Direct") & (fm.category.str.contains("Hybrid", na=False))]["amfi_code"].head(2).tolist()
)
selected_codes = selected_codes[:10]

nav_sel = nav[nav.amfi_code.isin(selected_codes)].copy()
nav_piv = nav_sel.pivot_table(index="date", columns="amfi_code", values="nav").ffill()
ret_piv = nav_piv.pct_change().dropna()

# Short labels
code_to_name = {row.amfi_code: row.scheme_name[:25] for row in fm.itertuples()
                if row.amfi_code in selected_codes}
ret_piv.columns = [code_to_name.get(c, str(c)) for c in ret_piv.columns]

corr = ret_piv.corr()

fig, ax = plt.subplots(figsize=(12, 10))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
cmap = sns.diverging_palette(230, 20, as_cmap=True)

sns.heatmap(corr, ax=ax, cmap=cmap, vmin=-1, vmax=1, center=0,
            annot=True, fmt=".2f", linewidths=0.8,
            square=True, linecolor="#e0e0e0",
            cbar_kws={"shrink": 0.7, "label": "Pearson Correlation"},
            annot_kws={"size": 9})

ax.set_title("NAV Return Correlation Matrix — 10 Selected Funds\n(Daily Returns 2022–2026)",
             fontsize=14, fontweight="bold", pad=15)
ax.tick_params(axis="x", rotation=35, labelsize=9)
ax.tick_params(axis="y", rotation=0,  labelsize=9)
plt.tight_layout()
save_mpl(fig, "08_return_correlation_matrix")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 9 — Sector Allocation Donut (Plotly)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 09: Sector Allocation Donut …")

# Equity funds only
equity_codes = fm[fm.category=="Equity"]["amfi_code"].unique()
ph_eq = ph[ph.amfi_code.isin(equity_codes)].copy()

sector_wt = ph_eq.groupby("sector")["weight_pct"].sum().sort_values(ascending=False)

fig = go.Figure(go.Pie(
    labels=sector_wt.index,
    values=sector_wt.values,
    hole=0.52,
    marker=dict(colors=px.colors.qualitative.Bold[:len(sector_wt)],
                line=dict(color="white", width=2.5)),
    textinfo="label+percent",
    textfont_size=11,
    hovertemplate="<b>%{label}</b><br>Weight: %{value:.1f}%<br>Share: %{percent}<extra></extra>",
    direction="clockwise",
    sort=True,
))

fig.add_annotation(
    text="<b>Sector</b><br>Allocation",
    x=0.5, y=0.5, showarrow=False,
    font=dict(size=15, color=BRAND_BLUE),
    xanchor="center"
)

fig.update_layout(
    **PLOTLY_LAYOUT,
    title="Aggregate Sector Allocation — Equity Funds Portfolio",
    legend=dict(orientation="v", x=1.02, y=0.5),
    height=580
)
save_plotly(fig, "09_sector_allocation_donut")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 10 — Performance Scatter: Return vs Risk (Plotly)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 10: Return vs Risk Scatter …")

perf_clean = perf.dropna(subset=["return_3yr_pct","std_dev_ann_pct","sharpe_ratio"])
perf_clean = perf_clean[perf_clean.plan=="Direct"]

fig = px.scatter(
    perf_clean, x="std_dev_ann_pct", y="return_3yr_pct",
    size="aum_crore", color="category",
    hover_name="scheme_name",
    hover_data={"sharpe_ratio":True,"aum_crore":True,
                "std_dev_ann_pct":True,"return_3yr_pct":True},
    color_discrete_sequence=[BRAND_BLUE, BRAND_TEAL, BRAND_AMBER],
    size_max=50,
    labels={
        "std_dev_ann_pct": "Annualised Volatility (Risk) %",
        "return_3yr_pct":  "3-Year CAGR Return %",
        "category":        "Category"
    },
    title="Risk vs Return — Direct Plans (Bubble = AUM Size)",
)
# Efficient frontier line hint
fig.add_hline(y=perf_clean["return_3yr_pct"].median(),
    line_dash="dot", line_color=BRAND_RED,
    annotation_text=f"Median Return {perf_clean['return_3yr_pct'].median():.1f}%",
    annotation_font=dict(color=BRAND_RED))

fig.update_layout(**PLOTLY_LAYOUT, height=560, legend=dict(x=0.01, y=0.99))
fig.update_traces(marker=dict(opacity=0.8, line=dict(width=1.5, color="white")))
save_plotly(fig, "10_return_vs_risk_scatter")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 11 — Top 10 Schemes by AUM (Seaborn horizontal bar)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 11: Top 10 Schemes by AUM …")

top10_aum = perf[perf.plan=="Regular"].nlargest(10, "aum_crore")

fig, ax = plt.subplots(figsize=(12, 7))
colors = [BRAND_BLUE if "SBI" not in fh else BRAND_RED
          for fh in top10_aum["fund_house"]]
bars = ax.barh(
    [n[:40] for n in top10_aum["scheme_name"][::-1]],
    top10_aum["aum_crore"][::-1] / 1000,
    color=colors[::-1], edgecolor="white", height=0.65
)
for bar in bars:
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            f"₹{bar.get_width():.0f}K Cr", va="center", fontsize=9)

ax.set_xlabel("AUM (₹ Thousand Crore)", fontsize=12)
ax.set_title("Top 10 Schemes by AUM", fontsize=14, fontweight="bold")
ax.spines[["top","right"]].set_visible(False)
red_patch  = mpatches.Patch(color=BRAND_RED,  label="SBI Fund House")
blue_patch = mpatches.Patch(color=BRAND_BLUE, label="Other Fund House")
ax.legend(handles=[red_patch, blue_patch], loc="lower right")
plt.tight_layout()
save_mpl(fig, "11_top10_schemes_by_aum")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 12 — SIP Active Accounts Growth (Plotly dual-axis)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 12: SIP Accounts Growth …")

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(go.Bar(
    x=sip_sorted["month_dt"], y=sip_sorted["sip_inflow_crore"],
    name="SIP Inflow (₹ Cr)", marker_color=BRAND_TEAL,
    opacity=0.75,
    hovertemplate="%{x|%b %Y}<br>₹%{y:,.0f} Cr<extra></extra>"
), secondary_y=False)

fig.add_trace(go.Scatter(
    x=sip_sorted["month_dt"], y=sip_sorted["active_sip_accounts_crore"],
    name="Active SIP Accounts (Cr)",
    mode="lines+markers",
    line=dict(color=BRAND_RED, width=2.5),
    marker=dict(size=7),
    hovertemplate="%{x|%b %Y}<br>%{y:.2f} Cr Accounts<extra></extra>"
), secondary_y=True)

fig.update_layout(
    **PLOTLY_LAYOUT,
    title="Monthly SIP Inflow vs Active SIP Accounts",
    legend=dict(x=0.01, y=0.99), height=500
)
fig.update_yaxes(title_text="SIP Inflow (₹ Crore)", secondary_y=False)
fig.update_yaxes(title_text="Active SIP Accounts (Crore)", secondary_y=True)
save_plotly(fig, "12_sip_accounts_vs_inflow")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 13 — Morningstar Rating Distribution (Seaborn)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 13: Morningstar Rating Distribution …")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Rating bar by category
rating_cat = perf.groupby(["category","morningstar_rating"]).size().reset_index(name="count")
sns.barplot(data=rating_cat, x="morningstar_rating", y="count", hue="category",
            palette=[BRAND_BLUE, BRAND_TEAL, BRAND_AMBER],
            ax=axes[0], edgecolor="white")
axes[0].set_title("Morningstar Rating Distribution by Category", fontweight="bold")
axes[0].set_xlabel("Morningstar Rating (Stars)")
axes[0].set_ylabel("Number of Schemes")
axes[0].spines[["top","right"]].set_visible(False)

# Expense ratio vs rating box
perf_direct = perf[perf.plan=="Direct"]
sns.boxplot(data=perf_direct, x="morningstar_rating", y="expense_ratio_pct",
            palette="Blues", ax=axes[1],
            flierprops=dict(marker="o", markersize=6, alpha=0.5))
axes[1].set_title("Expense Ratio vs Morningstar Rating\n(Direct Plans)", fontweight="bold")
axes[1].set_xlabel("Morningstar Rating (Stars)")
axes[1].set_ylabel("Expense Ratio (%)")
axes[1].spines[["top","right"]].set_visible(False)

plt.tight_layout()
save_mpl(fig, "13_morningstar_ratings")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 14 — Transaction Type Monthly Mix (Plotly stacked area)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 14: Transaction Type Mix …")

txn["ym"] = txn["transaction_date"].dt.to_period("M").dt.to_timestamp()
txn_monthly = (txn.groupby(["ym","transaction_type"])["amount_inr"]
               .sum().reset_index())

fig = px.area(txn_monthly, x="ym", y="amount_inr",
              color="transaction_type",
              color_discrete_map={"SIP": BRAND_TEAL,
                                  "Lumpsum": BRAND_BLUE,
                                  "Redemption": BRAND_RED},
              labels={"ym": "Month", "amount_inr": "Amount (₹)",
                      "transaction_type": "Type"},
              title="Monthly Transaction Volume by Type")

fig.update_layout(**PLOTLY_LAYOUT, height=480,
                  yaxis=dict(tickformat=",.0f"),
                  legend=dict(x=0.01, y=0.99))
save_plotly(fig, "14_transaction_type_mix")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 15 — Benchmark Indices Comparison (Plotly)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 15: Benchmark Indices …")

bm_pivot = bm.pivot_table(index="date", columns="index_name", values="close_value")
bm_norm  = bm_pivot.div(bm_pivot.iloc[0]) * 100

BENCH_COLORS = {
    "NIFTY50":        BRAND_BLUE,
    "NIFTY100":       BRAND_TEAL,
    "NIFTY_MIDCAP150": BRAND_AMBER,
    "BSE_SMALLCAP":   BRAND_RED,
    "NIFTY500":       BRAND_GREEN,
    "CRISIL_LIQUID":  "#6d6875",
    "CRISIL_GILT":    "#457b9d",
}

fig = go.Figure()
for col in bm_norm.columns:
    fig.add_trace(go.Scatter(
        x=bm_norm.index, y=bm_norm[col],
        mode="lines", name=col,
        line=dict(width=2, color=BENCH_COLORS.get(col, "#999")),
        hovertemplate=f"{col}: %{{y:.1f}}<br>%{{x|%d %b %Y}}<extra></extra>"
    ))

fig.add_vrect(x0="2023-01-01", x1="2023-12-31",
    fillcolor="rgba(42,157,143,0.08)", line_width=0,
    annotation_text="2023 Bull Run", annotation_position="top left",
    annotation_font=dict(color=BRAND_GREEN, size=10))
fig.add_vrect(x0="2024-09-01", x1="2024-12-31",
    fillcolor="rgba(230,57,70,0.08)", line_width=0,
    annotation_text="2024 Q4 Correction", annotation_position="top right",
    annotation_font=dict(color=BRAND_RED, size=10))

fig.update_layout(
    **PLOTLY_LAYOUT,
    title="Benchmark Indices Performance (Indexed to 100, Jan 2022)",
    xaxis_title="Date", yaxis_title="Indexed Value",
    legend=dict(x=0.01, y=0.99), height=560
)
save_plotly(fig, "15_benchmark_indices_comparison")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 16 — Sharpe Ratio Ranking (Seaborn)  
# ══════════════════════════════════════════════════════════════════════════════
print("Chart 16: Sharpe Ratio Ranking …")

sharpe_top = (perf[perf.plan=="Direct"]
              .nlargest(15, "sharpe_ratio")
              .sort_values("sharpe_ratio"))

fig, ax = plt.subplots(figsize=(12, 8))
colors_sharpe = [BRAND_RED if v >= sharpe_top["sharpe_ratio"].quantile(0.75) else BRAND_BLUE
                 for v in sharpe_top["sharpe_ratio"]]
bars = ax.barh(
    [n[:38] for n in sharpe_top["scheme_name"]],
    sharpe_top["sharpe_ratio"],
    color=colors_sharpe, edgecolor="white", height=0.65
)
for bar in bars:
    ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
            f"{bar.get_width():.2f}", va="center", fontsize=9)

ax.axvline(x=1.0, color=BRAND_AMBER, linestyle="--", linewidth=1.5,
           label="Sharpe = 1.0 (Good threshold)")
ax.set_xlabel("Sharpe Ratio", fontsize=12)
ax.set_title("Top 15 Funds by Sharpe Ratio — Direct Plans", fontsize=14, fontweight="bold")
ax.legend(loc="lower right")
ax.spines[["top","right"]].set_visible(False)
plt.tight_layout()
save_mpl(fig, "16_sharpe_ratio_ranking")


print("\n" + "═"*60)
print(f"  All 16 charts saved to:  {CHARTS}")
print("═"*60)

# Return summary dict for notebook
CHART_SUMMARY = {
    "01": ("NAV Trend All 40 Schemes",        "01_nav_trend_all_schemes"),
    "02": ("AUM Growth by Fund House",         "02_aum_growth_by_fund_house"),
    "03": ("SIP Inflow Time-Series",           "03_sip_inflow_timeseries"),
    "04": ("Category Inflow Heatmap",          "04_category_inflow_heatmap"),
    "05": ("Investor Demographics",            "05_investor_demographics"),
    "06": ("Geographic Distribution",          "06_geographic_distribution"),
    "07": ("Folio Count Growth",               "07_folio_count_growth"),
    "08": ("Return Correlation Matrix",        "08_return_correlation_matrix"),
    "09": ("Sector Allocation Donut",          "09_sector_allocation_donut"),
    "10": ("Return vs Risk Scatter",           "10_return_vs_risk_scatter"),
    "11": ("Top 10 Schemes by AUM",            "11_top10_schemes_by_aum"),
    "12": ("SIP Accounts vs Inflow",           "12_sip_accounts_vs_inflow"),
    "13": ("Morningstar Rating Distribution",  "13_morningstar_ratings"),
    "14": ("Transaction Type Mix",             "14_transaction_type_mix"),
    "15": ("Benchmark Indices Comparison",     "15_benchmark_indices_comparison"),
    "16": ("Sharpe Ratio Ranking",             "16_sharpe_ratio_ranking"),
}
