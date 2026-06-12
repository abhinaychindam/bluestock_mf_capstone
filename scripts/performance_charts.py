"""
performance_charts.py — D4 Chart Generation
All 8 performance analytics charts → reports/charts/perf_*.png
"""

import warnings
warnings.filterwarnings("ignore")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy import stats

BASE      = Path(__file__).resolve().parent.parent
RAW       = BASE / "data" / "raw"
PROCESSED = BASE / "data" / "processed"
CHARTS    = BASE / "reports" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "blue":   "#1a3c6b", "teal":   "#00a8a8", "red":    "#e63946",
    "amber":  "#f4a261", "green":  "#2a9d8f", "indigo": "#4361ee",
    "pink":   "#e9c46a", "slate":  "#457b9d", "dark":   "#264653",
}
sns.set_theme(style="whitegrid", font_scale=1.05)
plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150,
                     "figure.facecolor": "white", "font.family": "DejaVu Sans"})
PLOTLY_BASE = dict(font_family="Arial", paper_bgcolor="white", plot_bgcolor="white",
                   title_font_size=15, title_font_color=C["blue"],
                   margin=dict(l=70, r=40, t=75, b=65))

def save_png(fig, name):
    path = CHARTS / f"perf_{name}.png"
    fig.savefig(str(path), bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"  ✓ perf_{name}.png")
    return path

def save_plotly(fig, name):
    path_png  = CHARTS / f"perf_{name}.png"
    path_html = CHARTS / f"perf_{name}.html"
    fig.write_image(str(path_png), width=1200, height=650, scale=2)
    fig.write_html(str(path_html))
    print(f"  ✓ perf_{name}.png")
    return path_png


# ══════════════════════════════════════════════════════════════════════════════
# LOAD COMPUTED DATA
# ══════════════════════════════════════════════════════════════════════════════
print("Loading computed metrics …")
fm      = pd.read_csv(RAW / "01_fund_master.csv")
bm_raw  = pd.read_csv(RAW / "10_benchmark_indices.csv", parse_dates=["date"])
nav_raw = pd.read_csv(RAW / "02_nav_history.csv", parse_dates=["date"])
perf    = pd.read_csv(RAW / "07_scheme_performance.csv")

ret_wide  = pd.read_csv(PROCESSED / "daily_returns.csv",     index_col="date", parse_dates=["date"])
ret_wide.columns = ret_wide.columns.astype(int)

scorecard = pd.read_csv(PROCESSED / "fund_scorecard.csv",   index_col="amfi_code")
alpha_beta= pd.read_csv(PROCESSED / "alpha_beta.csv",       index_col="amfi_code")
full_met  = pd.read_csv(PROCESSED / "risk_metrics_computed.csv", index_col="amfi_code")
cagr_tbl  = pd.read_csv(PROCESSED / "cagr_table.csv",       index_col="amfi_code")

nav_wide = nav_raw.pivot_table(index="date", columns="amfi_code", values="nav").sort_index().ffill()
bm_dict  = {name: grp.set_index("date")["close_value"].sort_index().reindex(nav_wide.index).ffill()
            for name, grp in bm_raw.groupby("index_name")}

# Short name helper
def short_name(code, maxlen=32):
    rows = fm[fm.amfi_code == code]["scheme_name"]
    if len(rows): return rows.values[0][:maxlen]
    return str(code)

print(f"  Scorecard: {scorecard.shape}  |  Full metrics: {full_met.shape}")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P1 — Daily Returns Distribution (all 40 schemes)
# ══════════════════════════════════════════════════════════════════════════════
print("\nChart P1: Daily Returns Distribution …")

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# P1a — Histogram of ALL daily returns stacked
all_ret = ret_wide.values.flatten()
all_ret = all_ret[~np.isnan(all_ret)]

axes[0].hist(all_ret * 100, bins=120, color=C["blue"], alpha=0.75, edgecolor="white",
             linewidth=0.3, density=True)
# Normal overlay
mu, sigma = np.mean(all_ret)*100, np.std(all_ret)*100
x = np.linspace(mu - 4*sigma, mu + 4*sigma, 300)
axes[0].plot(x, stats.norm.pdf(x, mu, sigma), color=C["red"], lw=2, label="Normal fit")
axes[0].axvline(mu, color=C["amber"], lw=1.5, linestyle="--", label=f"Mean={mu:.3f}%")
axes[0].set_title("Distribution of All Daily Returns\n(40 Schemes Combined)", fontweight="bold")
axes[0].set_xlabel("Daily Return (%)"); axes[0].set_ylabel("Density")
axes[0].legend(); axes[0].spines[["top","right"]].set_visible(False)

# P1b — Box-plot by category (equity vs debt)
fm_idx = fm.set_index("amfi_code")
cat_data = {}
for cat in ["Equity", "Debt"]:
    codes = fm_idx[fm_idx.category == cat].index.tolist()
    valid = [c for c in codes if c in ret_wide.columns]
    vals  = ret_wide[valid].values.flatten()
    cat_data[cat] = vals[~np.isnan(vals)] * 100

bp = axes[1].boxplot(cat_data.values(), labels=cat_data.keys(), patch_artist=True,
                     medianprops=dict(color="white", linewidth=2.5),
                     flierprops=dict(marker=".", markersize=2, alpha=0.3))
colors_cat = [C["blue"], C["teal"]]
for patch, col in zip(bp["boxes"], colors_cat):
    patch.set_facecolor(col); patch.set_alpha(0.85)
axes[1].set_title("Daily Return Distribution\nEquity vs Debt", fontweight="bold")
axes[1].set_ylabel("Daily Return (%)"); axes[1].spines[["top","right"]].set_visible(False)

# P1c — Q-Q plot for top fund
top_code = scorecard.index[0]
fund_ret_sorted = np.sort(ret_wide[top_code].dropna().values * 100)
(osm, osr), (slope, intercept, r) = stats.probplot(fund_ret_sorted)
axes[2].plot(osm, osr, "o", color=C["blue"], markersize=3, alpha=0.6, label="Actual")
axes[2].plot(osm, slope*np.array(osm)+intercept, color=C["red"], lw=2, label=f"Normal (r={r:.3f})")
axes[2].set_title(f"Q-Q Plot: {short_name(top_code, 28)}\n(Top Scored Fund)", fontweight="bold")
axes[2].set_xlabel("Theoretical Quantiles"); axes[2].set_ylabel("Sample Quantiles")
axes[2].legend(); axes[2].spines[["top","right"]].set_visible(False)

plt.suptitle("Daily Return Distribution Analysis — All 40 Schemes", fontsize=14,
             fontweight="bold", y=1.01)
plt.tight_layout()
save_png(fig, "p1_return_distribution")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P2 — CAGR Comparison Table (Heatmap)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P2: CAGR Comparison Heatmap …")

cagr_display = cagr_tbl.join(fm.set_index("amfi_code")[["scheme_name","category","plan"]])
cagr_display = cagr_display.sort_values("cagr_3yr_pct", ascending=False)
cagr_display["label"] = cagr_display["scheme_name"].str[:40]

cagr_vals = cagr_display[["cagr_1yr_pct","cagr_3yr_pct","cagr_full_pct"]].rename(
    columns={"cagr_1yr_pct":"1-Year CAGR %",
             "cagr_3yr_pct":"3-Year CAGR %",
             "cagr_full_pct":"Full Period CAGR %"})
cagr_vals.index = cagr_display["label"].values

fig, ax = plt.subplots(figsize=(12, 14))
cmap = sns.diverging_palette(10, 133, s=85, l=45, as_cmap=True)
sns.heatmap(cagr_vals, ax=ax, cmap=cmap, center=12,
            annot=True, fmt=".1f", linewidths=0.5, linecolor="#e0e0e0",
            cbar_kws={"label": "CAGR %", "shrink": 0.6},
            annot_kws={"size": 9, "weight": "bold"})
ax.set_title("CAGR Comparison — All 40 Schemes\n(Sorted by 3-Year CAGR)", fontsize=13,
             fontweight="bold", pad=15)
ax.tick_params(axis="y", labelsize=8.5)
ax.tick_params(axis="x", labelsize=11)
plt.tight_layout()
save_png(fig, "p2_cagr_heatmap")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P3 — Sharpe & Sortino Ranking
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P3: Sharpe & Sortino Ranking …")

sharpe_data = full_met[["scheme_name","sharpe_ratio","sortino_ratio","category","plan"]].copy()
sharpe_data = sharpe_data.sort_values("sharpe_ratio", ascending=False).head(20)
y_pos = np.arange(len(sharpe_data))
labels = [n[:38] for n in sharpe_data["scheme_name"][::-1]]

fig, axes = plt.subplots(1, 2, figsize=(18, 10))

colors_sharpe = [C["red"] if v >= 1.0 else C["blue"] for v in sharpe_data["sharpe_ratio"][::-1]]
bars1 = axes[0].barh(y_pos, sharpe_data["sharpe_ratio"][::-1].values,
                     color=colors_sharpe, edgecolor="white", height=0.65)
axes[0].set_yticks(y_pos); axes[0].set_yticklabels(labels, fontsize=8.5)
axes[0].axvline(1.0, color=C["amber"], lw=2, linestyle="--", label="Sharpe=1.0 (good)")
axes[0].axvline(0.0, color="#cccccc", lw=1)
for bar in bars1:
    axes[0].text(bar.get_width()+0.02, bar.get_y()+bar.get_height()/2,
                 f"{bar.get_width():.2f}", va="center", fontsize=8)
axes[0].set_title("Top 20 Funds — Sharpe Ratio\n(Rf = 6.5% p.a.)", fontweight="bold", fontsize=12)
axes[0].set_xlabel("Sharpe Ratio"); axes[0].legend()
axes[0].spines[["top","right"]].set_visible(False)

sortino_data = full_met[["scheme_name","sortino_ratio","category"]].sort_values(
    "sortino_ratio", ascending=False).head(20)
labels_s = [n[:38] for n in sortino_data["scheme_name"][::-1]]
colors_sort = [C["green"] if v >= 1.5 else C["teal"] for v in sortino_data["sortino_ratio"][::-1]]
bars2 = axes[1].barh(y_pos, sortino_data["sortino_ratio"][::-1].values,
                     color=colors_sort, edgecolor="white", height=0.65)
axes[1].set_yticks(y_pos); axes[1].set_yticklabels(labels_s, fontsize=8.5)
axes[1].axvline(1.5, color=C["amber"], lw=2, linestyle="--", label="Sortino=1.5")
for bar in bars2:
    axes[1].text(bar.get_width()+0.02, bar.get_y()+bar.get_height()/2,
                 f"{bar.get_width():.2f}", va="center", fontsize=8)
axes[1].set_title("Top 20 Funds — Sortino Ratio\n(Downside Deviation)", fontweight="bold", fontsize=12)
axes[1].set_xlabel("Sortino Ratio"); axes[1].legend()
axes[1].spines[["top","right"]].set_visible(False)

plt.suptitle("Risk-Adjusted Performance: Sharpe & Sortino Ratios", fontsize=14, fontweight="bold")
plt.tight_layout()
save_png(fig, "p3_sharpe_sortino")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P4 — Alpha & Beta Scatter (all 40 funds)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P4: Alpha-Beta Scatter …")

ab = full_met[["scheme_name","alpha_annual_pct","beta","category","plan","r_squared"]].dropna()
ab_meta = fm.set_index("amfi_code")

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# P4a — Scatter alpha vs beta
cat_colors = {"Equity": C["blue"], "Debt": C["teal"]}
for cat, grp in ab.groupby("category"):
    axes[0].scatter(grp["beta"], grp["alpha_annual_pct"],
                    color=cat_colors.get(cat, C["slate"]),
                    s=80, alpha=0.85, edgecolors="white", lw=1.5, label=cat, zorder=3)

# Quadrant lines
axes[0].axhline(0, color="#aaa", lw=1, ls="--")
axes[0].axvline(1.0, color="#aaa", lw=1, ls="--")
axes[0].axvline(0.0, color="#bbb", lw=0.8)

# Annotate top 5 alpha
top_alpha = ab.nlargest(5, "alpha_annual_pct")
for idx, row in top_alpha.iterrows():
    axes[0].annotate(short_name(idx, 22),
                     xy=(row["beta"], row["alpha_annual_pct"]),
                     xytext=(row["beta"]+0.01, row["alpha_annual_pct"]+0.5),
                     fontsize=7.5, color=C["red"],
                     arrowprops=dict(arrowstyle="-", color=C["red"], lw=0.8))

axes[0].set_xlabel("Beta (vs NIFTY100)", fontsize=11)
axes[0].set_ylabel("Annualised Alpha (%)", fontsize=11)
axes[0].set_title("Alpha vs Beta — All 40 Schemes\n(OLS vs NIFTY100)", fontweight="bold")
axes[0].legend(); axes[0].spines[["top","right"]].set_visible(False)

# Quadrant annotations
axes[0].text(0.01, axes[0].get_ylim()[1]*0.95,
             "Low Beta, High Alpha\n(Ideal)", fontsize=8, color=C["green"], ha="left")

# P4b — Alpha bar chart top 15
alpha_top = ab.sort_values("alpha_annual_pct", ascending=False).head(15)
y_pos2 = np.arange(len(alpha_top))
cols_alpha = [C["red"] if v >= alpha_top["alpha_annual_pct"].quantile(0.75)
              else C["blue"] for v in alpha_top["alpha_annual_pct"][::-1]]
bars = axes[1].barh(y_pos2,
                    alpha_top["alpha_annual_pct"][::-1].values,
                    color=cols_alpha, edgecolor="white", height=0.65)
axes[1].set_yticks(y_pos2)
axes[1].set_yticklabels([short_name(c, 35) for c in alpha_top.index[::-1]], fontsize=8.5)
axes[1].axvline(0, color="#aaa", lw=1)
for bar in bars:
    axes[1].text(bar.get_width()+0.1, bar.get_y()+bar.get_height()/2,
                 f"{bar.get_width():.1f}%", va="center", fontsize=8.5)
axes[1].set_title("Top 15 Funds by Alpha (Annualised %)\nvs NIFTY100", fontweight="bold")
axes[1].set_xlabel("Alpha (% p.a.)"); axes[1].spines[["top","right"]].set_visible(False)

plt.suptitle("Alpha & Beta Analysis — OLS Regression vs NIFTY100", fontsize=14, fontweight="bold")
plt.tight_layout()
save_png(fig, "p4_alpha_beta")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P5 — Maximum Drawdown Analysis
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P5: Maximum Drawdown …")

dd = full_met[["scheme_name","max_drawdown_pct","peak_date","trough_date",
               "drawdown_duration_days","recovery_duration_days","category"]].copy()
dd = dd.sort_values("max_drawdown_pct")

fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# P5a — Drawdown bar chart (all funds)
y_pos = np.arange(len(dd))
labels_dd = [n[:36] for n in dd["scheme_name"]]
colors_dd = [C["red"] if v <= -20 else C["amber"] if v <= -10 else C["teal"]
             for v in dd["max_drawdown_pct"]]
axes[0].barh(y_pos, dd["max_drawdown_pct"].values, color=colors_dd, edgecolor="white", height=0.7)
axes[0].set_yticks(y_pos); axes[0].set_yticklabels(labels_dd, fontsize=8)
axes[0].set_xlabel("Maximum Drawdown (%)"); axes[0].axvline(0, color="#aaa", lw=0.8)
axes[0].axvline(-20, color=C["red"], lw=1.5, linestyle="--", alpha=0.6, label="-20% threshold")
axes[0].set_title("Maximum Drawdown — All 40 Schemes\n(Lower = More Drawdown)", fontweight="bold")
axes[0].legend(loc="lower right")
axes[0].spines[["top","right"]].set_visible(False)

patch_r = mpatches.Patch(color=C["red"],   label="DD > 20% (Severe)")
patch_a = mpatches.Patch(color=C["amber"], label="DD 10–20% (Moderate)")
patch_t = mpatches.Patch(color=C["teal"],  label="DD < 10% (Mild)")
axes[0].legend(handles=[patch_r, patch_a, patch_t], loc="lower right", fontsize=9)

# P5b — Underwater chart for top 5 worst-DD funds
top5_dd_codes = dd.nsmallest(5, "max_drawdown_pct").index.tolist()
nav_sub = nav_wide[top5_dd_codes]

for i, code in enumerate(top5_dd_codes):
    series = nav_sub[code]
    running_max = series.cummax()
    underwater  = (series / running_max - 1) * 100
    axes[1].fill_between(underwater.index, underwater.values, 0,
                         alpha=0.55 - i*0.05,
                         label=short_name(code, 28))
axes[1].set_title("Underwater Chart — Top 5 Worst Drawdown Funds\n(Recovery Periods Visible)",
                  fontweight="bold")
axes[1].set_xlabel("Date"); axes[1].set_ylabel("Drawdown from Peak (%)")
axes[1].legend(fontsize=8, loc="lower left")
axes[1].spines[["top","right"]].set_visible(False)

# Shade 2024 correction
axes[1].axvspan(pd.Timestamp("2024-09-01"), pd.Timestamp("2024-12-31"),
                alpha=0.10, color=C["red"], label="2024 Q4 Correction")

plt.suptitle("Maximum Drawdown Analysis — Drawdown Severity & Recovery", fontsize=13, fontweight="bold")
plt.tight_layout()
save_png(fig, "p5_max_drawdown")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P6 — Fund Scorecard (composite 0–100)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P6: Fund Scorecard …")

sc = scorecard.sort_values("composite_score", ascending=False).head(20)
y_pos = np.arange(len(sc))

fig, axes = plt.subplots(1, 2, figsize=(20, 9))

# P6a — Composite score bar
bar_colors = plt.cm.RdYlGn(sc["composite_score"].values[::-1] / 100)
bars = axes[0].barh(y_pos, sc["composite_score"].values[::-1],
                    color=bar_colors, edgecolor="white", height=0.7)
axes[0].set_yticks(y_pos)
axes[0].set_yticklabels([n[:40] for n in sc["scheme_name"].values[::-1]], fontsize=8.5)
for bar in bars:
    axes[0].text(bar.get_width()+0.3, bar.get_y()+bar.get_height()/2,
                 f"{bar.get_width():.1f}", va="center", fontsize=9, fontweight="bold")
axes[0].set_xlabel("Composite Score (0–100)")
axes[0].set_title("Fund Scorecard — Top 20 Funds\n(30% CAGR + 25% Sharpe + 20% Alpha + 15% Expense + 10% DD)",
                  fontweight="bold", fontsize=11)
axes[0].axvline(75, color=C["green"], lw=1.5, linestyle="--", alpha=0.7, label="Score=75 (Top Tier)")
axes[0].legend(); axes[0].spines[["top","right"]].set_visible(False)

# P6b — Spider/Radar sub-components for top 5
top5_codes = sc.head(5).index.tolist()
categories = ["3yr CAGR", "Sharpe", "Alpha", "Expense\n(inv)", "Max DD\n(inv)"]
rank_cols   = ["rank_cagr3yr","rank_sharpe","rank_alpha","rank_expense","rank_maxdd"]
n_cat = len(categories)
angles = np.linspace(0, 2*np.pi, n_cat, endpoint=False).tolist()
angles += angles[:1]

ax_r = axes[1]
ax_r.set_aspect("equal")
theta = np.linspace(0, 2*np.pi, 100)
for level in [25, 50, 75, 100]:
    ax_r.plot(level*np.cos(theta), level*np.sin(theta),
              color="#ddd", lw=0.8, linestyle=":")

palette5 = [C["blue"], C["red"], C["teal"], C["amber"], C["green"]]
for i, code in enumerate(top5_codes):
    vals = sc.loc[code, rank_cols].values.tolist()
    vals += vals[:1]
    x = [v * np.cos(a) for v, a in zip(vals, angles)]
    y = [v * np.sin(a) for v, a in zip(vals, angles)]
    ax_r.plot(x, y, color=palette5[i], lw=2, label=short_name(code, 28))
    ax_r.fill(x, y, color=palette5[i], alpha=0.08)

for j, (cat, angle) in enumerate(zip(categories, angles[:-1])):
    ax_r.text(108 * np.cos(angle), 108 * np.sin(angle), cat,
              ha="center", va="center", fontsize=9, fontweight="bold")

ax_r.set_xlim(-120, 120); ax_r.set_ylim(-120, 120)
ax_r.axis("off")
ax_r.set_title("Scorecard Radar — Top 5 Funds\n(Each axis = percentile rank 0–100)",
               fontweight="bold", fontsize=11, pad=20)
ax_r.legend(loc="lower right", fontsize=8, bbox_to_anchor=(1.3, 0))

plt.suptitle("Fund Scorecard (0–100) — Composite Performance Ranking", fontsize=13, fontweight="bold")
plt.tight_layout()
save_png(fig, "p6_fund_scorecard")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P7 — Benchmark Comparison (Top 5 vs NIFTY50 & NIFTY100) — PRIMARY DELIVERABLE
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P7: Benchmark Comparison (Top 5 funds) …")

top5_codes = scorecard.sort_values("composite_score", ascending=False).head(5).index.tolist()

# 3-year window: last 3 years of data
latest = nav_wide.index[-1]
start_3yr = nav_wide.index[nav_wide.index >= latest - pd.DateOffset(years=3)][0]

nav_3yr = nav_wide.loc[start_3yr:, top5_codes].copy()
bm50    = bm_dict["NIFTY50"].loc[start_3yr:].copy()
bm100   = bm_dict["NIFTY100"].loc[start_3yr:].copy()

# Index to 100
def idx100(series):
    return series / series.iloc[0] * 100

fig = go.Figure()

# Benchmark lines
fig.add_trace(go.Scatter(x=bm50.index, y=idx100(bm50),
    mode="lines", name="NIFTY 50",
    line=dict(color="#999999", width=2.5, dash="dash"),
    hovertemplate="NIFTY50: %{y:.1f}<br>%{x|%d %b %Y}<extra></extra>"))
fig.add_trace(go.Scatter(x=bm100.index, y=idx100(bm100),
    mode="lines", name="NIFTY 100",
    line=dict(color="#bbbbbb", width=2, dash="dot"),
    hovertemplate="NIFTY100: %{y:.1f}<br>%{x|%d %b %Y}<extra></extra>"))

colors_top5 = [C["blue"], C["red"], C["teal"], C["amber"], C["green"]]
for i, code in enumerate(top5_codes):
    label = short_name(code, 35)
    sc_val = scorecard.loc[code, "composite_score"]
    te_val = full_met.loc[code, "te_vs_nifty100_pct"] if "te_vs_nifty100_pct" in full_met.columns else np.nan
    alpha_val = full_met.loc[code, "alpha_annual_pct"] if "alpha_annual_pct" in full_met.columns else np.nan
    fig.add_trace(go.Scatter(
        x=nav_3yr.index, y=idx100(nav_3yr[code]),
        mode="lines",
        name=f"{label} [Score:{sc_val:.0f} | TE:{te_val:.1f}% | α:{alpha_val:.1f}%]",
        line=dict(width=2.5, color=colors_top5[i]),
        hovertemplate=f"{label}<br>Indexed NAV: %{{y:.1f}}<br>%{{x|%d %b %Y}}<extra></extra>"
    ))

# Highlight 2023 bull run and 2024 correction within 3yr window
for x0, x1, label_text, pos, color in [
    ("2023-05-29","2023-12-31", "2023 Bull Run", "top left", "rgba(42,157,143,0.10)"),
    ("2024-09-01","2024-12-31", "2024 Q4 Correction", "top right", "rgba(230,57,70,0.10)"),
]:
    t0, t1 = pd.Timestamp(x0), pd.Timestamp(x1)
    if t0 >= start_3yr:
        fig.add_vrect(x0=x0, x1=x1, fillcolor=color, line_width=0,
                      annotation_text=label_text, annotation_position=pos,
                      annotation_font=dict(size=10))

fig.update_layout(
    **PLOTLY_BASE,
    title=dict(text="Top 5 Funds vs NIFTY50 & NIFTY100 — 3-Year Performance<br>"
                    "<sup>Indexed to 100 | TE = Tracking Error vs NIFTY100 | α = Annualised Alpha</sup>"),
    xaxis_title="Date", yaxis_title="Indexed NAV (Base = 100 at 3yr start)",
    legend=dict(x=0.01, y=0.99, font=dict(size=9)),
    height=640,
)
fig.update_xaxes(showgrid=True, gridcolor="#eeeeee")
fig.update_yaxes(showgrid=True, gridcolor="#eeeeee")
save_plotly(fig, "p7_benchmark_comparison")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P8 — Tracking Error Bubble Chart
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P8: Tracking Error Analysis …")

te_data = full_met[["scheme_name","te_vs_nifty100_pct","te_vs_nifty50_pct",
                     "alpha_annual_pct","ann_vol_pct","category","plan"]].dropna()

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# P8a — Tracking error vs Alpha scatter
cat_map = {"Equity": C["blue"], "Debt": C["teal"]}
for cat, grp in te_data.groupby("category"):
    axes[0].scatter(grp["te_vs_nifty100_pct"], grp["alpha_annual_pct"],
                    s=grp["ann_vol_pct"] * 4,
                    color=cat_map.get(cat, C["slate"]),
                    alpha=0.75, edgecolors="white", lw=1.5, label=f"{cat} (size=volatility)")

for idx, row in te_data.nlargest(5, "alpha_annual_pct").iterrows():
    axes[0].annotate(short_name(idx, 20),
                     (row["te_vs_nifty100_pct"], row["alpha_annual_pct"]),
                     fontsize=7.5, color=C["red"], ha="left",
                     xytext=(3, 2), textcoords="offset points")

axes[0].axhline(0, color="#aaa", lw=1, linestyle="--")
axes[0].set_xlabel("Tracking Error vs NIFTY100 (% p.a.)")
axes[0].set_ylabel("Alpha (% p.a.)")
axes[0].set_title("Tracking Error vs Alpha\n(Bubble = Annualised Volatility)", fontweight="bold")
axes[0].legend(); axes[0].spines[["top","right"]].set_visible(False)

# P8b — TE comparison bar (NIFTY50 vs NIFTY100)
te_compare = te_data[["scheme_name","te_vs_nifty50_pct","te_vs_nifty100_pct"]].sort_values(
    "te_vs_nifty100_pct").head(15)
y_pos = np.arange(len(te_compare))
width = 0.38
axes[1].barh(y_pos + width/2, te_compare["te_vs_nifty50_pct"].values,
             width, color=C["blue"], alpha=0.85, label="vs NIFTY50", edgecolor="white")
axes[1].barh(y_pos - width/2, te_compare["te_vs_nifty100_pct"].values,
             width, color=C["teal"], alpha=0.85, label="vs NIFTY100", edgecolor="white")
axes[1].set_yticks(y_pos)
axes[1].set_yticklabels([n[:35] for n in te_compare["scheme_name"]], fontsize=8.5)
axes[1].set_xlabel("Tracking Error (% p.a.)")
axes[1].set_title("Tracking Error vs NIFTY50 & NIFTY100\n(Bottom 15 = Closest to Benchmark)",
                  fontweight="bold")
axes[1].legend(); axes[1].spines[["top","right"]].set_visible(False)

plt.suptitle("Tracking Error Analysis — Active vs Passive Risk", fontsize=13, fontweight="bold")
plt.tight_layout()
save_png(fig, "p8_tracking_error")


# ══════════════════════════════════════════════════════════════════════════════
# CHART P9 — Risk-Return Quadrant (final summary)
# ══════════════════════════════════════════════════════════════════════════════
print("Chart P9: Risk-Return Quadrant …")

quad = full_met[["scheme_name","ann_return_pct","ann_vol_pct",
                 "sharpe_ratio","category"]].dropna()
quad = quad.join(scorecard[["composite_score","scorecard_rank"]], how="left")

fig = go.Figure()
cat_colors_map = {"Equity": C["blue"], "Debt": C["teal"]}
for cat, grp in quad.groupby("category"):
    fig.add_trace(go.Scatter(
        x=grp["ann_vol_pct"], y=grp["ann_return_pct"],
        mode="markers+text",
        name=cat,
        marker=dict(size=grp["composite_score"]/4 + 8,
                    color=cat_colors_map.get(cat, C["slate"]),
                    opacity=0.8,
                    line=dict(width=1.5, color="white")),
        text=["#"+str(int(r)) for r in grp["scorecard_rank"].fillna(99)],
        textposition="top center",
        textfont=dict(size=9),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Return: %{y:.1f}%<br>Volatility: %{x:.1f}%<br>"
            "Sharpe: %{customdata[1]:.2f}<br>Score: %{customdata[2]:.0f}<extra></extra>"
        ),
        customdata=grp[["scheme_name","sharpe_ratio","composite_score"]].values
    ))

# Quadrant lines at medians
med_vol = quad["ann_vol_pct"].median()
med_ret = quad["ann_return_pct"].median()
fig.add_hline(y=med_ret, line_dash="dot", line_color="#ccc",
              annotation_text=f"Median Return {med_ret:.1f}%", annotation_font_size=10)
fig.add_vline(x=med_vol, line_dash="dot", line_color="#ccc",
              annotation_text=f"Median Vol {med_vol:.1f}%", annotation_font_size=10)

fig.add_annotation(x=quad["ann_vol_pct"].min()+1, y=quad["ann_return_pct"].max()-1,
    text="⭐ High Return<br>Low Risk", font=dict(size=11, color=C["green"]),
    showarrow=False, bgcolor="rgba(42,157,143,0.1)", bordercolor=C["green"])
fig.add_annotation(x=quad["ann_vol_pct"].max()-2, y=quad["ann_return_pct"].min()+1,
    text="⚠ Low Return<br>High Risk", font=dict(size=11, color=C["red"]),
    showarrow=False, bgcolor="rgba(230,57,70,0.1)", bordercolor=C["red"])

fig.update_layout(
    **PLOTLY_BASE,
    title="Risk-Return Quadrant — All 40 Funds<br><sup>Bubble Size = Composite Score | Labels = Scorecard Rank</sup>",
    xaxis_title="Annualised Volatility (Risk) %",
    yaxis_title="Annualised Return %",
    legend=dict(x=0.01, y=0.99),
    height=620
)
save_plotly(fig, "p9_risk_return_quadrant")

print("\n" + "═"*60)
all_charts = sorted(p for p in CHARTS.iterdir() if "perf_" in p.name and p.suffix == ".png")
print(f"  Performance charts saved: {len(all_charts)} PNGs")
for p in all_charts:
    print(f"    {p.name}  ({p.stat().st_size//1024} KB)")
print("═"*60)
