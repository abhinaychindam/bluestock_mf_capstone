"""
app.py — Bluestock MF Analytics Dashboard
Bonus B2 | D5 Alternative
4 pages: Industry Overview · Fund Performance · Investor Analytics · SIP & Market Trends
Run: streamlit run dashboard/app.py
"""
import warnings; warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

BASE = Path(__file__).resolve().parent
RAW  = BASE / "data" / "raw"
PROC = BASE / "data" / "processed"

st.set_page_config(page_title="Bluestock MF Analytics",page_icon="📊",
                   layout="wide",initial_sidebar_state="expanded")

C = {"navy":"#0d2137","blue":"#1a3c6b","teal":"#00a8a8","red":"#e63946",
     "amber":"#f4a261","green":"#2a9d8f","light":"#f0f4f8","grey":"#6c757d"}

PLOTLY_BASE = dict(font_family="Inter, Arial, sans-serif",
    paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
    title_font_color=C["blue"],title_font_size=14,
    margin=dict(l=50,r=30,t=50,b=50),
    colorway=[C["blue"],C["teal"],C["amber"],C["red"],C["green"],"#457b9d","#e76f51"])

st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif;}}
[data-testid="stSidebar"]{{background:linear-gradient(180deg,{C["navy"]} 0%,{C["blue"]} 100%);}}
[data-testid="stSidebar"] *{{color:white !important;}}
.kpi-card{{background:white;border-radius:12px;padding:18px 22px;border-left:5px solid {C["teal"]};
           box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:12px;}}
.kpi-value{{font-size:26px;font-weight:700;color:{C["blue"]};margin:4px 0;}}
.kpi-label{{font-size:11px;color:{C["grey"]};text-transform:uppercase;letter-spacing:0.8px;}}
.kpi-delta{{font-size:12px;font-weight:600;color:{C["green"]};}}
.page-header{{background:linear-gradient(135deg,{C["navy"]} 0%,{C["blue"]} 60%,{C["teal"]} 100%);
              color:white;padding:20px 28px;border-radius:14px;margin-bottom:20px;}}
.page-header h1{{color:white !important;margin:0;font-size:21px;font-weight:700;}}
.page-header p{{color:#a8dadc;margin:4px 0 0 0;font-size:12px;}}
.sec-title{{font-size:14px;font-weight:600;color:{C["blue"]};
            border-bottom:2px solid {C["teal"]};padding-bottom:5px;margin:14px 0 10px 0;}}
div[data-testid="stMetric"]{{background:white;border-radius:10px;padding:12px 16px;
  box-shadow:0 2px 8px rgba(0,0,0,0.06);border-left:4px solid {C["teal"]};}}
</style>""",unsafe_allow_html=True)

@st.cache_data(show_spinner="Loading data…")
def load_all():
    fm   = pd.read_csv(RAW/"01_fund_master.csv")
    nav  = pd.read_csv(RAW/"02_nav_history.csv",    parse_dates=["date"])
    aum  = pd.read_csv(RAW/"03_aum_by_fund_house.csv",parse_dates=["date"])
    sip  = pd.read_csv(RAW/"04_monthly_sip_inflows.csv")
    cat  = pd.read_csv(RAW/"05_category_inflows.csv")
    fol  = pd.read_csv(RAW/"06_industry_folio_count.csv")
    perf = pd.read_csv(RAW/"07_scheme_performance.csv")
    txn  = pd.read_csv(RAW/"08_investor_transactions.csv",parse_dates=["transaction_date"])
    ph   = pd.read_csv(RAW/"09_portfolio_holdings.csv")
    bm   = pd.read_csv(RAW/"10_benchmark_indices.csv",parse_dates=["date"])
    sc   = pd.read_csv(PROC/"fund_scorecard.csv")
    cagr = pd.read_csv(PROC/"cagr_table.csv")
    ab   = pd.read_csv(PROC/"alpha_beta.csv")
    rm   = pd.read_csv(PROC/"risk_metrics_computed.csv")
    sip["month_dt"]=pd.to_datetime(sip["month"])
    cat["month_dt"]=pd.to_datetime(cat["month"])
    fol["month_dt"]=pd.to_datetime(fol["month"])
    return fm,nav,aum,sip,cat,fol,perf,txn,ph,bm,sc,cagr,ab,rm

fm,nav,aum,sip,cat,fol,perf,txn,ph,bm,sc,cagr,ab,rm = load_all()
nifty50  = bm[bm.index_name=="NIFTY50"].set_index("date")["close_value"].sort_index()
nifty100 = bm[bm.index_name=="NIFTY100"].set_index("date")["close_value"].sort_index()
nav_wide = nav.pivot_table(index="date",columns="amfi_code",values="nav").ffill()

with st.sidebar:
    st.markdown("""<div style='text-align:center;padding:16px 0 24px 0;'>
      <div style='font-size:32px;'>📊</div>
      <div style='font-size:18px;font-weight:700;color:white;'>Bluestock MF</div>
      <div style='font-size:11px;color:#a8dadc;margin-top:2px;'>Analytics Dashboard</div>
    </div>""",unsafe_allow_html=True)
    PAGE = st.radio("Navigate",
        ["🏦 Industry Overview","📈 Fund Performance",
         "👥 Investor Analytics","💰 SIP & Market Trends"],
        label_visibility="collapsed")
    st.markdown("---")
    st.markdown("""<div style='font-size:11px;color:#a8dadc;padding:8px 0;'>
    <b>Period:</b> Jan 2022 – May 2026<br><b>Schemes:</b> 40 | <b>AMCs:</b> 10<br>
    <b>Transactions:</b> 32,778</div>""",unsafe_allow_html=True)

# ═══════ PAGE 1 — INDUSTRY OVERVIEW ═══════════════════════════════════════════
if PAGE == "🏦 Industry Overview":
    st.markdown("""<div class='page-header'><div style='font-size:36px;'>🏦</div>
    <div><h1>Industry Overview</h1>
    <p>Indian MF Industry — AUM, Folios & Growth 2022–2025</p></div></div>""",
    unsafe_allow_html=True)

    latest_aum = aum[aum.date==aum.date.max()]["aum_lakh_crore"].sum()
    peak_sip   = sip["sip_inflow_crore"].max()
    latest_fol = fol.sort_values("month_dt").iloc[-1]["total_folios_crore"]

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='kpi-card'><div class='kpi-label'>Total Industry AUM</div>
        <div class='kpi-value'>₹{latest_aum:.1f}L Cr</div>
        <div class='kpi-delta'>↑ Dec 2025 Snapshot</div></div>""",unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='kpi-card' style='border-color:{C["amber"]};'>
        <div class='kpi-label'>Peak SIP Inflow</div>
        <div class='kpi-value'>₹{peak_sip:,.0f}Cr</div>
        <div class='kpi-delta'>↑ All-Time High Dec 2025</div></div>""",unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='kpi-card' style='border-color:{C["green"]};'>
        <div class='kpi-label'>Total Folios</div>
        <div class='kpi-value'>{latest_fol:.2f} Cr</div>
        <div class='kpi-delta'>↑ +97% since Jan 2022</div></div>""",unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='kpi-card' style='border-color:{C["red"]};'>
        <div class='kpi-label'>Active Schemes</div>
        <div class='kpi-value'>{perf["amfi_code"].nunique()}</div>
        <div class='kpi-delta'>Across 10 AMCs</div></div>""",unsafe_allow_html=True)

    st.markdown("")
    col1,col2 = st.columns([3,2])
    with col1:
        st.markdown("<div class='sec-title'>Industry AUM Trend 2022–2025</div>",unsafe_allow_html=True)
        aum_total = aum.groupby("date")["aum_lakh_crore"].sum().reset_index().sort_values("date")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=aum_total["date"],y=aum_total["aum_lakh_crore"],
            mode="lines+markers",fill="tozeroy",fillcolor="rgba(0,168,168,0.12)",
            line=dict(color=C["teal"],width=3),marker=dict(size=7),
            hovertemplate="<b>%{x|%b %Y}</b><br>₹%{y:.2f}L Cr<extra></extra>"))
        fig.add_annotation(x=aum_total["date"].iloc[-1],y=aum_total["aum_lakh_crore"].iloc[-1],
            text=f"<b>₹{aum_total['aum_lakh_crore'].iloc[-1]:.1f}L Cr</b>",
            showarrow=True,arrowhead=2,arrowcolor=C["blue"],
            font=dict(size=12,color=C["blue"]),bgcolor="white",
            bordercolor=C["blue"],borderwidth=1.5,ax=-60,ay=-40)
        fig.update_layout(**PLOTLY_BASE,height=310,showlegend=False,
            yaxis_title="AUM (₹ Lakh Crore)",yaxis=dict(gridcolor="#f0f0f0"),
            xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig,use_container_width=True)
    with col2:
        st.markdown("<div class='sec-title'>Folio Growth — Stacked</div>",unsafe_allow_html=True)
        fol_s = fol.sort_values("month_dt")
        fig2 = go.Figure()
        for col_n,color,label in [("equity_folios_crore",C["blue"],"Equity"),
                                   ("hybrid_folios_crore",C["amber"],"Hybrid"),
                                   ("debt_folios_crore",C["teal"],"Debt")]:
            fig2.add_trace(go.Scatter(x=fol_s["month_dt"],y=fol_s[col_n],
                mode="lines",name=label,stackgroup="one",
                line=dict(width=0.5,color=color),
                hovertemplate=f"{label}: %{{y:.2f}} Cr<extra></extra>"))
        fig2.add_trace(go.Scatter(x=fol_s["month_dt"],y=fol_s["total_folios_crore"],
            mode="lines",name="Total",line=dict(color=C["red"],width=2.5,dash="dot")))
        fig2.update_layout(**PLOTLY_BASE,height=310,
            yaxis_title="Folios (Crore)",legend=dict(orientation="h",y=-0.25,x=0),
            yaxis=dict(gridcolor="#f0f0f0"),xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig2,use_container_width=True)

    col3,col4 = st.columns([2,3])
    with col3:
        st.markdown("<div class='sec-title'>AUM by AMC — Latest</div>",unsafe_allow_html=True)
        aum_fh = aum[aum.date==aum.date.max()].sort_values("aum_lakh_crore")
        cols_b = [C["red"] if "SBI" in fh else C["blue"] for fh in aum_fh["fund_house"]]
        fig3 = go.Figure(go.Bar(x=aum_fh["aum_lakh_crore"],y=aum_fh["fund_house"],
            orientation="h",marker_color=cols_b,
            text=[f"₹{v:.1f}L" for v in aum_fh["aum_lakh_crore"]],textposition="outside",
            hovertemplate="<b>%{y}</b><br>₹%{x:.2f}L Cr<extra></extra>"))
        fig3.update_layout(**PLOTLY_BASE,height=340,showlegend=False,
            xaxis_title="AUM (₹ Lakh Crore)",xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig3,use_container_width=True)
    with col4:
        st.markdown("<div class='sec-title'>AUM by Fund House — Annual Growth</div>",unsafe_allow_html=True)
        aum["year"] = aum["date"].dt.year
        aum_yr = aum.groupby(["year","fund_house"])["aum_lakh_crore"].mean().reset_index()
        aum_yr = aum_yr[aum_yr["year"].isin([2022,2023,2024,2025])]
        fig4 = px.bar(aum_yr,x="fund_house",y="aum_lakh_crore",color="year",barmode="group",
            color_discrete_sequence=[C["blue"],C["teal"],C["amber"],C["red"]],
            labels={"aum_lakh_crore":"Avg AUM (₹L Cr)","fund_house":"AMC","year":"Year"})
        fig4.update_layout(**PLOTLY_BASE,height=340,xaxis_tickangle=-30,
            legend=dict(orientation="h",y=1.1,x=0),yaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig4,use_container_width=True)

    col5,col6 = st.columns([1,2])
    with col5:
        st.markdown("<div class='sec-title'>Schemes by Category</div>",unsafe_allow_html=True)
        cat_cnt = fm.groupby("category").size().reset_index(name="count")
        fig5 = go.Figure(go.Pie(labels=cat_cnt["category"],values=cat_cnt["count"],hole=0.5,
            marker=dict(colors=[C["blue"],C["teal"],C["amber"]],line=dict(color="white",width=2.5)),
            textinfo="label+percent"))
        fig5.update_layout(**PLOTLY_BASE,height=260,showlegend=False)
        st.plotly_chart(fig5,use_container_width=True)
    with col6:
        st.markdown("<div class='sec-title'>Sub-Category Treemap</div>",unsafe_allow_html=True)
        sub_cnt = fm.groupby(["category","sub_category"]).size().reset_index(name="count")
        fig6 = px.treemap(sub_cnt,path=["category","sub_category"],values="count",color="category",
            color_discrete_map={"Equity":C["blue"],"Debt":C["teal"],"Hybrid":C["amber"]})
        fig6.update_layout(**PLOTLY_BASE,height=260)
        fig6.update_traces(textfont_size=12,marker_line_width=2)
        st.plotly_chart(fig6,use_container_width=True)

# ═══════ PAGE 2 — FUND PERFORMANCE ════════════════════════════════════════════
elif PAGE == "📈 Fund Performance":
    st.markdown("""<div class='page-header'><div style='font-size:36px;'>📈</div>
    <div><h1>Fund Performance</h1>
    <p>Return vs Risk · Scorecard · NAV vs Benchmark · Alpha & Beta</p></div></div>""",
    unsafe_allow_html=True)

    sb1,sb2,sb3 = st.columns(3)
    sel_fh   = sb1.selectbox("Fund House",["All"]+sorted(perf["fund_house"].unique()))
    sel_cat  = sb2.selectbox("Category",  ["All"]+sorted(perf["category"].unique()))
    sel_plan = sb3.selectbox("Plan",      ["All"]+sorted(perf["plan"].unique()))

    p = perf.copy()
    if sel_fh  !="All": p=p[p.fund_house==sel_fh]
    if sel_cat !="All": p=p[p.category==sel_cat]
    if sel_plan!="All": p=p[p.plan==sel_plan]
    st.caption(f"Showing {len(p)} schemes")

    col1,col2 = st.columns([3,2])
    with col1:
        st.markdown("<div class='sec-title'>Return vs Risk — Bubble = AUM</div>",unsafe_allow_html=True)
        pc = p.dropna(subset=["return_3yr_pct","std_dev_ann_pct","aum_crore"])
        fig_sc = px.scatter(pc,x="std_dev_ann_pct",y="return_3yr_pct",size="aum_crore",
            color="category",hover_name="scheme_name",
            hover_data={"sharpe_ratio":True,"aum_crore":True,"expense_ratio_pct":True},
            color_discrete_map={"Equity":C["blue"],"Debt":C["teal"],"Hybrid":C["amber"]},
            size_max=55,
            labels={"std_dev_ann_pct":"Volatility (Std Dev %)","return_3yr_pct":"3-Year Return (%)"})
        fig_sc.add_hline(y=pc["return_3yr_pct"].median(),line_dash="dot",line_color="#ccc",
            annotation_text="Median Return",annotation_font=dict(size=9,color=C["grey"]))
        fig_sc.add_vline(x=pc["std_dev_ann_pct"].median(),line_dash="dot",line_color="#ccc",
            annotation_text="Median Risk",annotation_font=dict(size=9,color=C["grey"]))
        fig_sc.update_layout(**PLOTLY_BASE,height=380,legend=dict(x=0.01,y=0.99),
            yaxis=dict(gridcolor="#f0f0f0"),xaxis=dict(gridcolor="#f0f0f0"))
        fig_sc.update_traces(marker=dict(opacity=0.82,line=dict(width=1.5,color="white")))
        st.plotly_chart(fig_sc,use_container_width=True)

    with col2:
        st.markdown("<div class='sec-title'>Sharpe Ratio Ranking</div>",unsafe_allow_html=True)
        top_sh = p.nlargest(12,"sharpe_ratio")
        fig_sh = go.Figure(go.Bar(
            x=top_sh["sharpe_ratio"],y=[n[:28] for n in top_sh["scheme_name"]],
            orientation="h",
            marker_color=[C["red"] if v>=1.0 else C["blue"] for v in top_sh["sharpe_ratio"]],
            text=[f"{v:.2f}" for v in top_sh["sharpe_ratio"]],textposition="outside",
            hovertemplate="<b>%{y}</b><br>Sharpe:%{x:.3f}<extra></extra>"))
        fig_sh.add_vline(x=1.0,line_dash="dash",line_color=C["amber"],annotation_text="1.0")
        fig_sh.update_layout(**PLOTLY_BASE,height=380,showlegend=False,
            xaxis_title="Sharpe Ratio",xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_sh,use_container_width=True)

    st.markdown("<div class='sec-title'>Fund Scorecard — Composite Ranking (0–100)</div>",unsafe_allow_html=True)
    sc_d = sc.copy()
    if sel_fh  !="All": sc_d=sc_d[sc_d.fund_house==sel_fh]
    if sel_cat !="All": sc_d=sc_d[sc_d.category==sel_cat]
    if sel_plan!="All": sc_d=sc_d[sc_d.plan==sel_plan]
    sc_d = sc_d.sort_values("scorecard_rank")
    tbl = sc_d[["scorecard_rank","scheme_name","fund_house","category","plan",
                "composite_score","cagr_3yr","sharpe","alpha","expense","max_dd"]].rename(columns={
        "scorecard_rank":"Rank","scheme_name":"Scheme","fund_house":"AMC",
        "category":"Cat","plan":"Plan","composite_score":"Score",
        "cagr_3yr":"3yr%","sharpe":"Sharpe","alpha":"Alpha%","expense":"Exp%","max_dd":"MaxDD%"})
    for nc in ["Score","3yr%","Sharpe","Alpha%","Exp%","MaxDD%"]:
        if nc in tbl: tbl[nc]=tbl[nc].round(2)
    st.dataframe(tbl.set_index("Rank"),use_container_width=True,height=300,
        column_config={"Score":st.column_config.ProgressColumn("Score",min_value=0,max_value=100),
                       "3yr%":st.column_config.NumberColumn(format="%.1f%%"),
                       "Sharpe":st.column_config.NumberColumn(format="%.2f")})

    col3,col4 = st.columns([1,4])
    with col3:
        st.markdown("<div class='sec-title'>NAV Detail</div>",unsafe_allow_html=True)
        fund_list = p.sort_values("scheme_name")["scheme_name"].tolist() or \
                    perf.sort_values("scheme_name")["scheme_name"].tolist()
        sel_fund = st.selectbox("Scheme",fund_list,label_visibility="collapsed")
        sel_code = perf[perf.scheme_name==sel_fund]["amfi_code"].values[0]
        show_n50  = st.checkbox("NIFTY 50", True)
        show_n100 = st.checkbox("NIFTY 100",True)
        period = st.radio("Period",["1yr","3yr","Full"],index=1,label_visibility="collapsed")
    with col4:
        if sel_code in nav_wide.columns:
            nav_s = nav_wide[sel_code].dropna().sort_index()
            ld = nav_s.index[-1]
            sd = nav_s.index[nav_s.index>=(ld-pd.DateOffset(years=int(period[0])))][0] \
                 if period!="Full" else nav_s.index[0]
            nav_sub = nav_s.loc[sd:]; nav_norm = nav_sub/nav_sub.iloc[0]*100
            fig_nav = go.Figure()
            fig_nav.add_trace(go.Scatter(x=nav_norm.index,y=nav_norm.values,mode="lines",
                name=sel_fund[:38],line=dict(color=C["blue"],width=2.5),
                hovertemplate="NAV:%{y:.1f}<br>%{x|%d %b %Y}<extra></extra>"))
            if show_n50:
                b5=nifty50.reindex(nav_norm.index).ffill(); b5n=b5/b5.iloc[0]*100
                fig_nav.add_trace(go.Scatter(x=b5n.index,y=b5n.values,mode="lines",
                    name="NIFTY50",line=dict(color=C["amber"],width=2,dash="dash")))
            if show_n100:
                b1=nifty100.reindex(nav_norm.index).ffill(); b1n=b1/b1.iloc[0]*100
                fig_nav.add_trace(go.Scatter(x=b1n.index,y=b1n.values,mode="lines",
                    name="NIFTY100",line=dict(color=C["grey"],width=1.5,dash="dot")))
            fig_nav.update_layout(**PLOTLY_BASE,height=280,
                title=f"{sel_fund[:50]} (Indexed 100, {period})",yaxis_title="Indexed",
                legend=dict(x=0.01,y=0.99,font=dict(size=9)),
                yaxis=dict(gridcolor="#f0f0f0"),xaxis=dict(gridcolor="#f0f0f0"))
            st.plotly_chart(fig_nav,use_container_width=True)

    col5,col6 = st.columns(2)
    with col5:
        st.markdown("<div class='sec-title'>Alpha vs Beta</div>",unsafe_allow_html=True)
        ab_p = ab.dropna(subset=["alpha_annual_pct","beta"])
        if sel_cat!="All": ab_p=ab_p[ab_p.category==sel_cat]
        fig_ab = px.scatter(ab_p,x="beta",y="alpha_annual_pct",color="category",
            hover_name="scheme_name",
            color_discrete_map={"Equity":C["blue"],"Debt":C["teal"],"Hybrid":C["amber"]},
            labels={"beta":"Beta (vs NIFTY100)","alpha_annual_pct":"Alpha (% p.a.)"})
        fig_ab.add_hline(y=0,line_dash="dot",line_color="#ccc")
        fig_ab.add_vline(x=1,line_dash="dot",line_color="#ccc",annotation_text="β=1")
        fig_ab.update_layout(**PLOTLY_BASE,height=280,legend=dict(x=0.01,y=0.99),
            yaxis=dict(gridcolor="#f0f0f0"),xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_ab,use_container_width=True)
    with col6:
        st.markdown("<div class='sec-title'>Max Drawdown by Fund</div>",unsafe_allow_html=True)
        rm_p = rm.copy()
        if sel_cat!="All": rm_p=rm_p[rm_p.category==sel_cat]
        rm_s = rm_p.sort_values("max_drawdown_pct").head(15)
        fig_dd = go.Figure(go.Bar(x=rm_s["max_drawdown_pct"],
            y=[n[:30] for n in rm_s["scheme_name"]],orientation="h",
            marker_color=[C["red"] if v<=-25 else C["amber"] if v<=-15 else C["teal"]
                          for v in rm_s["max_drawdown_pct"]],
            hovertemplate="<b>%{y}</b><br>MaxDD:%{x:.1f}%<extra></extra>"))
        fig_dd.update_layout(**PLOTLY_BASE,height=280,showlegend=False,
            xaxis_title="Max Drawdown (%)",xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_dd,use_container_width=True)

# ═══════ PAGE 3 — INVESTOR ANALYTICS ══════════════════════════════════════════
elif PAGE == "👥 Investor Analytics":
    st.markdown("""<div class='page-header'><div style='font-size:36px;'>👥</div>
    <div><h1>Investor Analytics</h1>
    <p>Demographics · Geographic Distribution · Transaction Patterns</p></div></div>""",
    unsafe_allow_html=True)

    s1,s2,s3,s4 = st.columns(4)
    sel_state   = s1.selectbox("State",    ["All"]+sorted(txn["state"].unique()))
    sel_age     = s2.selectbox("Age Group",["All"]+sorted(txn["age_group"].unique()))
    sel_tier    = s3.selectbox("City Tier",["All","T30","B30"])
    sel_ttype   = s4.selectbox("Txn Type", ["All","SIP","Lumpsum","Redemption"])

    t = txn.copy()
    if sel_state !="All": t=t[t.state==sel_state]
    if sel_age   !="All": t=t[t.age_group==sel_age]
    if sel_tier  !="All": t=t[t.city_tier==sel_tier]
    if sel_ttype !="All": t=t[t.transaction_type==sel_ttype]

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total Amount",    f"₹{t['amount_inr'].sum()/1e7:,.0f} Cr")
    k2.metric("Transactions",    f"{len(t):,}")
    k3.metric("Unique Investors",f"{t['investor_id'].nunique():,}")
    k4.metric("Avg Ticket",      f"₹{t['amount_inr'].mean():,.0f}")

    st.markdown("")
    col1,col2 = st.columns([3,2])
    with col1:
        st.markdown("<div class='sec-title'>Transaction Amount by State</div>",unsafe_allow_html=True)
        st_agg = t.groupby("state")["amount_inr"].sum().sort_values().reset_index()
        fig_st = go.Figure(go.Bar(x=st_agg["amount_inr"]/1e7,y=st_agg["state"],
            orientation="h",
            marker_color=[C["red"] if s==st_agg["state"].iloc[-1] else C["blue"]
                          for s in st_agg["state"]],
            text=[f"₹{v/1e7:.0f}Cr" for v in st_agg["amount_inr"]],textposition="outside",
            hovertemplate="<b>%{y}</b><br>₹%{x:.1f}Cr<extra></extra>"))
        fig_st.update_layout(**PLOTLY_BASE,height=360,showlegend=False,
            xaxis_title="₹ Crore",xaxis=dict(gridcolor="#d3d8de"))
        st.plotly_chart(fig_st,use_container_width=True)
    with col2:
        st.markdown("<div class='sec-title'>Transaction Split</div>",unsafe_allow_html=True)
        ts = t.groupby("transaction_type")["amount_inr"].sum().reset_index()
        fig_d = go.Figure(go.Pie(labels=ts["transaction_type"],values=ts["amount_inr"],hole=0.5,
            marker=dict(colors=[C["teal"],C["blue"],C["red"]],
                        line=dict(color="white",width=2.5)),textinfo="label+percent"))
        fig_d.update_layout(**PLOTLY_BASE,height=230,showlegend=False)
        st.plotly_chart(fig_d,use_container_width=True)
        tier_s = t.groupby("city_tier")["amount_inr"].sum().reset_index()
        fig_tier = go.Figure(go.Pie(labels=tier_s["city_tier"],values=tier_s["amount_inr"],
            hole=0.5,marker=dict(colors=[C["blue"],C["amber"]],
                                  line=dict(color="white",width=2.5)),
            textinfo="label+percent"))
        fig_tier.update_layout(**PLOTLY_BASE,height=230,showlegend=False,title="T30 vs B30")
        st.plotly_chart(fig_tier,use_container_width=True)

    col3,col4 = st.columns(2)
    with col3:
        st.markdown("<div class='sec-title'>Avg SIP by Age Group</div>",unsafe_allow_html=True)
        age_order = ["18-25","26-35","36-45","46-55","56+"]
        ag = t[t.transaction_type=="SIP"].groupby("age_group")["amount_inr"]\
               .mean().reindex(age_order).reset_index()
        fig_ag = go.Figure(go.Bar(x=ag["age_group"],y=ag["amount_inr"],
            marker_color=[C["red"] if v==ag["amount_inr"].max() else C["blue"]
                          for v in ag["amount_inr"]],
            text=[f"₹{v:,.0f}" for v in ag["amount_inr"]],textposition="outside"))
        fig_ag.update_layout(**PLOTLY_BASE,height=280,showlegend=False,
            yaxis_title="Avg SIP (₹)",yaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_ag,use_container_width=True)
    with col4:
        st.markdown("<div class='sec-title'>Monthly Transaction Volume</div>",unsafe_allow_html=True)
        t["ym"] = t["transaction_date"].dt.to_period("M").dt.to_timestamp()
        mv = t.groupby(["ym","transaction_type"])["amount_inr"].sum().reset_index()
        tc = {"SIP":C["teal"],"Lumpsum":C["blue"],"Redemption":C["red"]}
        fig_mv = go.Figure()
        for tt,grp in mv.groupby("transaction_type"):
            fig_mv.add_trace(go.Scatter(x=grp["ym"],y=grp["amount_inr"]/1e5,mode="lines",
                name=tt,line=dict(color=tc.get(tt,C["grey"]),width=2),
                stackgroup="one" if tt!="Redemption" else None,
                hovertemplate=f"{tt}:₹%{{y:.1f}}L<extra></extra>"))
        fig_mv.update_layout(**PLOTLY_BASE,height=280,
            yaxis_title="₹ Lakh",legend=dict(x=0.01,y=0.99,font=dict(size=9)),
            yaxis=dict(gridcolor="#f0f0f0"),xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_mv,use_container_width=True)

    col5,col6 = st.columns(2)
    with col5:
        st.markdown("<div class='sec-title'>Gender Split</div>",unsafe_allow_html=True)
        gs = t.groupby("gender")["amount_inr"].sum().reset_index()
        fig_g = go.Figure(go.Pie(labels=gs["gender"],values=gs["amount_inr"],hole=0.5,
            marker=dict(colors=[C["blue"],C["teal"],C["amber"]],
                        line=dict(color="white",width=2.5)),textinfo="label+percent"))
        fig_g.update_layout(**PLOTLY_BASE,height=240,showlegend=False)
        st.plotly_chart(fig_g,use_container_width=True)
    with col6:
        st.markdown("<div class='sec-title'>KYC Status vs Amount</div>",unsafe_allow_html=True)
        ks = t.groupby("kyc_status")["amount_inr"].sum().reset_index()
        fig_k = go.Figure(go.Bar(x=ks["kyc_status"],y=ks["amount_inr"]/1e7,
            marker_color=[C["green"],C["amber"]],
            text=[f"₹{v/1e7:.0f}Cr" for v in ks["amount_inr"]],textposition="outside"))
        fig_k.update_layout(**PLOTLY_BASE,height=240,showlegend=False,
            yaxis_title="₹ Crore",yaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_k,use_container_width=True)

# ═══════ PAGE 4 — SIP & MARKET TRENDS ═════════════════════════════════════════
elif PAGE == "💰 SIP & Market Trends":
    st.markdown("""<div class='page-header'><div style='font-size:36px;'>💰</div>
    <div><h1>SIP & Market Trends</h1>
    <p>SIP Flows · Nifty50 Overlay · Category Inflows · Sector Allocation</p></div></div>""",
    unsafe_allow_html=True)

    sip_s = sip.sort_values("month_dt")
    nifty_m = nifty50.resample("ME").last().reset_index()\
                     .rename(columns={"date":"month_dt","close_value":"nifty50"})
    merged = pd.merge(sip_s,nifty_m,on="month_dt",how="left")

    st.markdown("<div class='sec-title'>SIP Inflow (Bar) + NIFTY 50 (Line) — 2022–2025</div>",unsafe_allow_html=True)
    peak_idx = sip_s["sip_inflow_crore"].idxmax()
    peak_row = sip_s.loc[peak_idx]
    bar_cols = [C["red"] if i==peak_idx else C["teal"] for i in sip_s.index]

    fig_dual = make_subplots(specs=[[{"secondary_y":True}]])
    fig_dual.add_trace(go.Bar(x=merged["month_dt"],y=merged["sip_inflow_crore"],
        name="SIP Inflow (₹ Cr)",marker_color=bar_cols,opacity=0.85,
        hovertemplate="SIP:₹%{y:,.0f}Cr<br>%{x|%b %Y}<extra></extra>"),secondary_y=False)
    fig_dual.add_trace(go.Scatter(x=merged["month_dt"],y=merged["nifty50"],
        mode="lines+markers",name="NIFTY 50",
        line=dict(color=C["amber"],width=2.5),marker=dict(size=5),
        hovertemplate="NIFTY50:%{y:,.0f}<br>%{x|%b %Y}<extra></extra>"),secondary_y=True)
    fig_dual.add_annotation(x=peak_row["month_dt"],y=peak_row["sip_inflow_crore"],
        text=f"<b>ATH: ₹{peak_row['sip_inflow_crore']:,.0f}Cr</b>",
        showarrow=True,arrowhead=2,arrowcolor=C["red"],
        font=dict(size=11,color=C["red"]),bgcolor="white",
        bordercolor=C["red"],borderwidth=1.5,ax=30,ay=-50)
    fig_dual.update_layout(**PLOTLY_BASE,height=360,legend=dict(x=0.01,y=0.99),
        yaxis=dict(gridcolor="#f0f0f0"))
    fig_dual.update_yaxes(title_text="SIP Inflow (₹ Crore)",secondary_y=False)
    fig_dual.update_yaxes(title_text="NIFTY 50",secondary_y=True)
    st.plotly_chart(fig_dual,use_container_width=True)

    col1,col2 = st.columns([3,2])
    with col1:
        st.markdown("<div class='sec-title'>Category Net Inflow Heatmap</div>",unsafe_allow_html=True)
        cp = cat.pivot_table(index="category",columns="month",values="net_inflow_crore",aggfunc="sum")
        cp = cp[sorted(cp.columns)]
        xl = [pd.to_datetime(c).strftime("%b %y") for c in cp.columns]
        yl = list(cp.index)
        z  = cp.values.tolist()
        zt = [[f"{v:.0f}" if pd.notna(v) else "" for v in row] for row in z]
        fig_h = go.Figure(go.Heatmap(z=z,x=xl,y=yl,text=zt,texttemplate="%{text}",
            textfont=dict(size=9),
            colorscale=[[0,"#c0392b"],[0.45,"#ffffff"],[1,"#1a9850"]],
            zmid=0,hoverongaps=False,
            hovertemplate="<b>%{y}</b><br>%{x}<br>₹%{z:.0f}Cr<extra></extra>",
            colorbar=dict(title="₹Cr",thickness=12)))
        fig_h.update_layout(**PLOTLY_BASE,height=360,
            xaxis=dict(tickangle=-30,tickfont=dict(size=9)),yaxis=dict(tickfont=dict(size=9)))
        st.plotly_chart(fig_h,use_container_width=True)
    with col2:
        st.markdown("<div class='sec-title'>Top 5 Categories — FY25</div>",unsafe_allow_html=True)
        fy25 = cat[(cat.month_dt>="2024-04-01")&(cat.month_dt<="2025-03-31")]
        t5c  = fy25.groupby("category")["net_inflow_crore"].sum().nlargest(5).reset_index()
        fig_tc = go.Figure(go.Bar(x=t5c["net_inflow_crore"],y=t5c["category"],
            orientation="h",
            marker_color=[C["red"] if i==0 else C["blue"] for i in range(len(t5c))],
            text=[f"₹{v:,.0f}Cr" for v in t5c["net_inflow_crore"]],textposition="outside"))
        fig_tc.update_layout(**PLOTLY_BASE,height=260,showlegend=False,
            xaxis_title="Net Inflow (₹ Cr)",xaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig_tc,use_container_width=True)
        st.markdown("<div class='sec-title'>SIP YoY Growth by Year</div>",unsafe_allow_html=True)
        yoy = sip_s[sip_s.yoy_growth_pct.notna()].copy()
        yoy["year"] = yoy["month_dt"].dt.year
        yoy_t = yoy.groupby("year")["yoy_growth_pct"].mean().round(1).reset_index()
        yoy_t.columns=["Year","Avg YoY%"]
        st.dataframe(yoy_t,use_container_width=True,hide_index=True,height=130)

    col3,col4 = st.columns([2,3])
    with col3:
        st.markdown("<div class='sec-title'>Sector Allocation — Equity Funds</div>",unsafe_allow_html=True)
        eq_codes = fm[fm.category=="Equity"]["amfi_code"].unique()
        sec_wt = ph[ph.amfi_code.isin(eq_codes)].groupby("sector")["weight_pct"].sum()\
                   .sort_values(ascending=False)
        fig_sec = go.Figure(go.Pie(labels=sec_wt.index,values=sec_wt.values,hole=0.5,
            marker=dict(colors=px.colors.qualitative.Bold[:len(sec_wt)],
                        line=dict(color="white",width=2)),
            textinfo="label+percent",textfont_size=9))
        fig_sec.update_layout(**PLOTLY_BASE,height=340,showlegend=False)
        st.plotly_chart(fig_sec,use_container_width=True)
    with col4:
        st.markdown("<div class='sec-title'>Benchmark Indices (Indexed to 100)</div>",unsafe_allow_html=True)
        bm_opts = ["NIFTY50","NIFTY100","NIFTY_MIDCAP150","BSE_SMALLCAP","NIFTY500"]
        sel_bm  = st.multiselect("Indices",bm_opts,default=["NIFTY50","NIFTY100","NIFTY_MIDCAP150"])
        bm_c = {"NIFTY50":C["blue"],"NIFTY100":C["teal"],"NIFTY_MIDCAP150":C["amber"],
                "BSE_SMALLCAP":C["red"],"NIFTY500":C["green"]}
        if sel_bm:
            fig_bm = go.Figure()
            for idx_n in sel_bm:
                bs = bm[bm.index_name==idx_n].set_index("date")["close_value"]
                bn = bs/bs.iloc[0]*100
                fig_bm.add_trace(go.Scatter(x=bn.index,y=bn.values,mode="lines",name=idx_n,
                    line=dict(color=bm_c.get(idx_n,C["grey"]),width=2.5)))
            fig_bm.add_vrect(x0="2023-01-01",x1="2023-12-31",
                fillcolor="rgba(42,157,143,0.08)",line_width=0,
                annotation_text="2023 Bull Run",annotation_font=dict(color=C["green"],size=9))
            fig_bm.add_vrect(x0="2024-09-01",x1="2024-12-31",
                fillcolor="rgba(230,57,70,0.08)",line_width=0,
                annotation_text="2024 Correction",annotation_font=dict(color=C["red"],size=9))
            fig_bm.update_layout(**PLOTLY_BASE,height=340,
                yaxis_title="Indexed Value",legend=dict(x=0.01,y=0.99),
                yaxis=dict(gridcolor="#f0f0f0"),xaxis=dict(gridcolor="#f0f0f0"))
            st.plotly_chart(fig_bm,use_container_width=True)

st.markdown(f"""<hr style='border:1px solid #eee;margin:28px 0 10px 0;'>
<div style='text-align:center;font-size:11px;color:{C["grey"]};'>
  Bluestock MF Analytics · D5 / Bonus B2 · Streamlit + Plotly · 
  Data: AMFI / mfapi.in (Jan 2022 – May 2026)
</div>""",unsafe_allow_html=True)