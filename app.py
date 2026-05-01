# app.py  ─ Standalone Streamlit dashboard (no FastAPI required)
# Deploy on Streamlit Cloud:
#   1. Put app.py + retail_sales.csv + requirements.txt in your repo root
#   2. In Streamlit Cloud → Settings → Secrets add:
#      GEMINI_API_KEY = "AIza..."

import os
from dotenv import load_dotenv
load_dotenv()  # loads .env file from project root
import requests as http_requests

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Retail Sales Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Material Icons loaded via CSS @import below

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons+Round');

    * { font-family: 'Inter', sans-serif !important; }
    [data-testid="stAppViewContainer"] { background: #0a0c14; }
    [data-testid="stSidebar"] { background: #0f1221; border-right: 1px solid #1e2240; }
    [data-testid="stSidebar"] .stMarkdown { color: #a0a8c0; }
    .stTabs [data-baseweb="tab-list"] { background: #0f1221; border-bottom: 1px solid #1e2240; gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        color: #6b7290; background: transparent;
        border-radius: 8px 8px 0 0; padding: 10px 18px;
        font-size: 0.88rem; font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        color: #7c83fd !important; background: #1a1d30 !important;
        border-bottom: 2px solid #7c83fd !important;
    }
    @keyframes fadeSlideUp {
        from { opacity: 0; transform: translateY(16px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    .metric-card {
        background: linear-gradient(135deg, #13162b 0%, #1a1e35 100%);
        border: 1px solid #252a48; border-radius: 14px;
        padding: 22px 18px; text-align: center;
        box-shadow: 0 4px 24px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.04);
        animation: fadeSlideUp 0.45s ease both;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative; overflow: hidden;
    }
    .metric-card::before {
        content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #7c83fd, transparent);
        background-size: 200% auto; animation: shimmer 3s linear infinite;
    }
    .metric-card:hover { transform: translateY(-3px); box-shadow: 0 8px 32px rgba(124,131,253,.2); }
    .metric-value {
        font-size: 1.85rem; font-weight: 700;
        background: linear-gradient(135deg, #7c83fd, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .metric-label { font-size: .78rem; color: #6b7290; margin-top: 6px; letter-spacing: .04em; text-transform: uppercase; }
    .metric-delta { font-size: .82rem; margin-top: 4px; }
    .delta-pos { color: #4ade80; }
    .delta-neg { color: #f87171; }
    .section-header {
        font-size: 1.05rem; font-weight: 600; color: #c5cae9;
        border-left: 3px solid #7c83fd; padding-left: 12px;
        margin: 28px 0 14px;
    }
    .section-sub { font-size: .82rem; color: #6b7290; margin-top: -10px; margin-bottom: 14px; padding-left: 15px; }
    .chat-wrap { max-height: 480px; overflow-y: auto; padding: 4px 0; scroll-behavior: smooth; }
    .chat-msg-user {
        background: linear-gradient(135deg, #2a2d4a, #323565);
        border: 1px solid #3a3f6a; border-radius: 14px 14px 4px 14px;
        padding: 12px 16px; margin: 6px 0 6px 60px;
        color: #e0e4f7; font-size: .91rem; line-height: 1.55;
        animation: fadeSlideUp .25s ease both;
    }
    .chat-msg-ai {
        background: linear-gradient(135deg, #13162b, #1a1e35);
        border: 1px solid #7c83fd44; border-radius: 14px 14px 14px 4px;
        padding: 12px 16px; margin: 6px 60px 6px 0;
        color: #c5cae9; font-size: .91rem; line-height: 1.6;
        animation: fadeSlideUp .25s ease both;
    }
    .chat-label-user { text-align:right; font-size:.72rem; color:#6b7290; margin:4px 4px 0 0; }
    .chat-label-ai   { font-size:.72rem; color:#7c83fd; margin:4px 0 0 4px; }
    .quality-bar { background: #1a1e35; border-radius: 8px; height: 8px; overflow: hidden; margin-top: 4px; }
    .quality-fill { height: 100%; border-radius: 8px; background: linear-gradient(90deg, #7c83fd, #4ade80); transition: width .8s ease; }
    .filter-label { font-size: .75rem; color: #7c83fd; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; font-weight: 600; }
    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] *,
    section[data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"],
    button[kind="header"],
    .st-emotion-cache-pb6fr7,
    [data-testid="baseButton-header"] { display: none !important; visibility: hidden !important; }

    /* Fix Material Icon text showing as raw strings */
    .material-icons, .material-icons-round, .material-icons-outlined {
        font-family: "Material Icons" !important;
        font-size: 20px !important;
        line-height: 1 !important;
        display: inline-block !important;
    }

    /* Hide sidebar toggle arrow button completely */
    [data-testid="stSidebarNav"] ~ div button { display: none !important; }
    section[tabindex="0"] > div:first-child > div:first-child > button { display: none !important; }
    h1,h2,h3,h4 { color: #e0e4f7 !important; }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    .status-ok  { color: #4ade80; font-weight: 600; }
    .status-err { color: #f87171; font-weight: 600; }
    [data-testid="stExpander"] { border: 1px solid #1e2240 !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

PALETTE  = ["#7c83fd","#f7797d","#43e97b","#fa8231","#a29bfe","#fd79a8","#00cec9","#fdcb6e","#e17055","#74b9ff"]
TEMPLATE = "plotly_dark"
PLOTLY_BASE = dict(
    template=TEMPLATE,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter", color="#a0a8c0"),
    margin=dict(t=20, b=10, l=10, r=10),
)

try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING & ANALYTICS  (previously backend/data_loader.py + main.py)
# ══════════════════════════════════════════════════════════════════════════════

DATA_PATH = os.getenv("DATA_PATH", "retail_sales.csv")

@st.cache_data
def load_and_clean() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)

    # ── Date ──────────────────────────────────────────────────────────────────
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # ── Category & Region — normalise NaN-like strings ────────────────────────
    nan_vals = {"nan", "nan?", "null", "none", ""}
    for col in ["Category", "Region"]:
        col_str = df[col].astype(object).fillna("").astype(str).str.strip().str.lower()
        df[col] = df[col].astype(object)
        df.loc[col_str.isin(nan_vals), col] = np.nan

    # ── Numeric columns ───────────────────────────────────────────────────────
    for col in ["Sales", "Quantity", "Profit"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.loc[df["Sales"] == 0,    "Sales"]    = np.nan
    df.loc[df["Quantity"] == 0, "Quantity"] = np.nan

    # ── Impute ────────────────────────────────────────────────────────────────
    df["Category"] = df["Category"].fillna(df["Category"].mode()[0])
    df["Region"]   = df["Region"].fillna(df["Region"].mode()[0])
    df["Sales"]    = df["Sales"].fillna(df["Sales"].median())
    df["Quantity"] = df["Quantity"].fillna(df["Quantity"].median())
    df["Profit"]   = df["Profit"].fillna(df["Profit"].median())

    # ── Derived columns ───────────────────────────────────────────────────────
    df["Month"]         = df["Date"].dt.month
    df["Month_Name"]    = df["Date"].dt.strftime("%b")
    df["Week"]          = df["Date"].dt.isocalendar().week.astype(int)
    df["DayOfWeek"]     = df["Date"].dt.day_name()
    df["Quarter"]       = df["Date"].dt.quarter.apply(lambda q: f"Q{q}")
    df["Profit_Margin"] = (df["Profit"] / df["Sales"] * 100).round(2)

    return df.dropna(subset=["Date"])


def build_summary(df: pd.DataFrame) -> str:
    cat   = df.groupby("Category").agg(Sales=("Sales","sum"), Profit=("Profit","sum"),
                                        Margin=("Profit_Margin","mean"), Txns=("Sales","count")).round(2)
    reg   = df.groupby("Region").agg(Sales=("Sales","sum"), Profit=("Profit","sum"),
                                      Txns=("Sales","count")).round(2)
    mon   = df.groupby("Month_Name")["Sales"].sum().round(2)
    dow   = df.groupby("DayOfWeek")["Sales"].mean().round(2)
    best  = df.groupby("Date")["Sales"].sum().idxmax()
    worst = df.groupby("Date")["Sales"].sum().idxmin()
    top5  = df.groupby(["Category","Region"])["Sales"].sum().nlargest(5).round(2)

    return f"""
You are an expert retail sales analyst. Answer questions ONLY from the data below.
Be concise, use specific numbers, format with $ and commas where relevant.

=== DATASET ===
Date range : {df['Date'].min().date()} → {df['Date'].max().date()}
Rows       : {len(df):,}
Categories : {', '.join(sorted(df['Category'].unique()))}
Regions    : {', '.join(sorted(df['Region'].unique()))}

=== KEY METRICS ===
Total Sales       : ${df['Sales'].sum():,.2f}
Total Profit      : ${df['Profit'].sum():,.2f}
Avg Profit Margin : {df['Profit_Margin'].mean():.1f}%
Total Units Sold  : {df['Quantity'].sum():,.0f}
Avg Order Value   : ${df['Sales'].mean():,.2f}
Best Sales Day    : {best.date()} (${df.groupby('Date')['Sales'].sum()[best]:,.2f})
Worst Sales Day   : {worst.date()} (${df.groupby('Date')['Sales'].sum()[worst]:,.2f})

=== BY CATEGORY ===
{cat.to_string()}

=== BY REGION ===
{reg.to_string()}

=== MONTHLY SALES ===
{mon.to_string()}

=== AVG SALES BY DAY OF WEEK ===
{dow.to_string()}

=== TOP 5 CATEGORY × REGION ===
{top5.to_string()}

=== MARGIN STATS ===
Min: {df['Profit_Margin'].min():.1f}%  Max: {df['Profit_Margin'].max():.1f}%  Std: {df['Profit_Margin'].std():.1f}%
"""


def filtered_df(df, date_from=None, date_to=None, categories=None, regions=None):
    d = df.copy()
    if date_from:
        d = d[d["Date"] >= pd.Timestamp(date_from)]
    if date_to:
        d = d[d["Date"] <= pd.Timestamp(date_to)]
    if categories:
        cat_list = [c.strip() for c in categories] if isinstance(categories, list) else [c.strip() for c in categories.split(",") if c.strip()]
        if cat_list:
            d = d[d["Category"].isin(cat_list)]
    if regions:
        reg_list = [r.strip() for r in regions] if isinstance(regions, list) else [r.strip() for r in regions.split(",") if r.strip()]
        if reg_list:
            d = d[d["Region"].isin(reg_list)]
    return d


def get_kpis(df):
    return dict(
        total_sales=round(float(df["Sales"].sum()), 2),
        total_profit=round(float(df["Profit"].sum()), 2),
        total_quantity=round(float(df["Quantity"].sum()), 2),
        avg_margin=round(float(df["Profit_Margin"].mean()), 2),
        total_transactions=int(len(df)),
        avg_order_value=round(float(df["Sales"].mean()), 2),
    )


def get_categories(df):
    grp = (df.groupby("Category")
             .agg(total_sales=("Sales","sum"), total_profit=("Profit","sum"),
                  avg_margin=("Profit_Margin","mean"), transactions=("Sales","count"))
             .reset_index().round(2))
    grp.columns = ["category","total_sales","total_profit","avg_margin","transactions"]
    return grp


def get_regions(df):
    grp = (df.groupby("Region")
             .agg(total_sales=("Sales","sum"), total_profit=("Profit","sum"), transactions=("Sales","count"))
             .reset_index().round(2))
    grp.columns = ["region","total_sales","total_profit","transactions"]
    return grp


def get_monthly(df):
    grp = (df.groupby(["Month","Month_Name"])
             .agg(sales=("Sales","sum"), profit=("Profit","sum"))
             .reset_index().sort_values("Month").round(2))
    grp = grp.rename(columns={"Month_Name": "month"})
    return grp


def get_daily(df):
    grp = (df.groupby("Date")
             .agg(sales=("Sales","sum"), profit=("Profit","sum"), transactions=("Sales","count"))
             .reset_index().sort_values("Date").round(2))
    grp["date"] = grp["Date"].dt.strftime("%Y-%m-%d")
    return grp


def get_weekly(df):
    grp = (df.groupby("Week")
             .agg(sales=("Sales","sum"), profit=("Profit","sum"), transactions=("Sales","count"))
             .reset_index().sort_values("Week").round(2))
    return grp


def get_dayofweek(df):
    day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    grp = (df.groupby("DayOfWeek")
             .agg(sales=("Sales","sum"), profit=("Profit","sum"),
                  avg_sales=("Sales","mean"), transactions=("Sales","count"))
             .reindex(day_order).reset_index().round(2))
    grp.columns = ["day","sales","profit","avg_sales","transactions"]
    grp = grp.fillna(0)
    return grp


def get_quarterly(df):
    grp = (df.groupby("Quarter")
             .agg(sales=("Sales","sum"), profit=("Profit","sum"),
                  transactions=("Sales","count"), avg_margin=("Profit_Margin","mean"))
             .reset_index().sort_values("Quarter").round(2))
    return grp


def get_heatmap(df):
    grp = (df.groupby(["Category","Region"])
             .agg(sales=("Sales","sum"), profit=("Profit","sum"), transactions=("Sales","count"))
             .reset_index().round(2))
    grp.columns = ["category","region","sales","profit","transactions"]
    return grp


def get_deepdive(df, category=None, region=None):
    d = df.copy()
    if category and category != "All":
        d = d[d["Category"] == category]
    if region and region != "All":
        d = d[d["Region"] == region]
    grp = (d.groupby(["Category","Region","Month_Name","Month"])
            .agg(sales=("Sales","sum"), profit=("Profit","sum"), transactions=("Sales","count"))
            .reset_index().sort_values(["Category","Region","Month"]).round(2))
    grp = grp.drop(columns=["Month"])
    grp = grp.rename(columns={"Month_Name":"month","Category":"category","Region":"region"})
    return grp


def get_quality(df_raw):
    raw = df_raw.copy()
    return dict(
        total_rows=int(len(raw)),
        complete_rows=int(raw.dropna().shape[0]),
        missing_dates=int(raw["Date"].isna().sum()),
        missing_categories=int(raw["Category"].isna().sum()),
        missing_regions=int(raw["Region"].isna().sum()),
        missing_sales=int(raw["Sales"].isna().sum()),
        missing_profit=int(raw["Profit"].isna().sum()),
        missing_quantity=int(raw["Quantity"].isna().sum()),
        duplicate_rows=int(raw.duplicated().sum()),
        sales_min=round(float(raw["Sales"].min()), 2),
        sales_max=round(float(raw["Sales"].max()), 2),
        sales_mean=round(float(raw["Sales"].mean()), 2),
        profit_min=round(float(raw["Profit"].min()), 2),
        profit_max=round(float(raw["Profit"].max()), 2),
        date_min=str(raw["Date"].min().date()),
        date_max=str(raw["Date"].max().date()),
        categories=sorted(raw["Category"].dropna().unique().tolist()),
        regions=sorted(raw["Region"].dropna().unique().tolist()),
    )


def get_raw(df, limit=100, offset=0, sort_by=None, sort_dir="desc"):
    d = df.copy()
    if sort_by and sort_by in d.columns:
        d = d.sort_values(sort_by, ascending=(sort_dir == "asc"))
    total = len(d)
    sliced = d.iloc[offset: offset + limit].copy()
    sliced["Date"] = sliced["Date"].dt.strftime("%Y-%m-%d")
    return {"total": total, "data": sliced.astype(object).where(sliced.notna(), None)}


# ── Gemini chat (same logic as original main.py /chat endpoint) ───────────────
def gemini_chat(history, user_message, data_summary):
    history.append({"role": "user", "parts": [user_message]})
    contents = [
        {"role": msg["role"], "parts": [{"text": msg["parts"][0]}]}
        for msg in history
    ]
    payload = {
        "system_instruction": {"parts": [{"text": data_summary}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.3},
    }
    resp = http_requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=payload, timeout=30
    )
    if resp.status_code != 200:
        err = resp.json().get("error", {}).get("message", "Unknown Gemini error")
        return None, err
    reply_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    history.append({"role": "model", "parts": [reply_text]})
    return reply_text, None


# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════
DF = load_and_clean()
DATA_SUMMARY = build_summary(DF)

ALL_CATS    = sorted(DF["Category"].unique().tolist())
ALL_REGIONS = sorted(DF["Region"].unique().tolist())
DATE_MIN    = str(DF["Date"].min().date())
DATE_MAX    = str(DF["Date"].max().date())

# ─── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛒 Retail Sales")
    st.markdown(
        f'<span class="status-ok">● Data loaded</span><br>'
        f'<span style="color:#6b7290;font-size:.8rem">{len(DF):,} rows · {DATE_MIN} → {DATE_MAX}</span>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown('<div class="filter-label">📅 Date Range</div>', unsafe_allow_html=True)
    d_from = st.date_input("From", value=date.fromisoformat(DATE_MIN),
                            min_value=date.fromisoformat(DATE_MIN),
                            max_value=date.fromisoformat(DATE_MAX),
                            label_visibility="collapsed", key="d_from")
    d_to   = st.date_input("To",   value=date.fromisoformat(DATE_MAX),
                            min_value=date.fromisoformat(DATE_MIN),
                            max_value=date.fromisoformat(DATE_MAX),
                            label_visibility="collapsed", key="d_to")
    st.markdown('<div class="filter-label" style="margin-top:12px">🏷️ Categories</div>', unsafe_allow_html=True)
    sel_cats = st.multiselect("Categories", ALL_CATS, default=ALL_CATS,
                               label_visibility="collapsed", key="sel_cats")
    st.markdown('<div class="filter-label" style="margin-top:12px">🌐 Regions</div>', unsafe_allow_html=True)
    sel_regs = st.multiselect("Regions", ALL_REGIONS, default=ALL_REGIONS,
                               label_visibility="collapsed", key="sel_regs")
    if st.button("↺ Reset Filters", use_container_width=True):
        for k in ["d_from","d_to","sel_cats","sel_regs"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
    st.markdown("---")
    st.markdown('<div style="font-size:.75rem;color:#6b7290">Streamlit + Gemini AI<br>All charts respond to filters above.</div>', unsafe_allow_html=True)

if not sel_cats or not sel_regs:
    st.warning("Please select at least one Category and one Region in the sidebar.")
    st.stop()

# ── Build filtered dataframes (replaces all API fetch calls) ──────────────────
f_cats = sel_cats if len(sel_cats) < len(ALL_CATS) else None
f_regs = sel_regs if len(sel_regs) < len(ALL_REGIONS) else None

df_filtered  = filtered_df(DF, d_from, d_to, f_cats, f_regs)
df_cats_only = filtered_df(DF, d_from, d_to, None,   f_regs)   # for categories tab (no cat filter)
df_regs_only = filtered_df(DF, d_from, d_to, f_cats, None)     # for regions tab (no reg filter)
df_heatmap_base = filtered_df(DF, d_from, d_to, None, None)    # heatmap ignores cat/reg filter

kpis        = get_kpis(df_filtered)
df_cats_df  = get_categories(df_cats_only)
df_regs_df  = get_regions(df_regs_only)
df_monthly  = get_monthly(df_filtered)
df_daily    = get_daily(df_filtered)
df_weekly   = get_weekly(df_filtered)
df_dow      = get_dayofweek(df_filtered)
df_qtr      = get_quarterly(df_filtered)
df_heatmap  = get_heatmap(df_heatmap_base)
quality_raw = get_quality(DF)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE TITLE + TABS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("# 🛒 Retail Sales Analytics Dashboard")

tabs = st.tabs([
    "📊 Overview",
    "📈 Trends",
    "🗓️ Time Patterns",
    "🏷️ Categories",
    "🌐 Regions",
    "🔥 Heatmap",
    "🔬 Deep Dive",
    "🤖 AI Assistant",
    "📋 Raw Data",
    "🩺 Data Quality",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 · OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    delays = ["0.05s","0.12s","0.19s","0.26s","0.33s","0.40s"]
    metrics = [
        ("💰", "Total Sales",    f"${kpis['total_sales']:,.0f}"),
        ("📈", "Total Profit",   f"${kpis['total_profit']:,.0f}"),
        ("📦", "Units Sold",     f"{kpis['total_quantity']:,.0f}"),
        ("🎯", "Avg Margin",     f"{kpis['avg_margin']:.1f}%"),
        ("🧾", "Transactions",   f"{kpis['total_transactions']:,}"),
        ("🛍️","Avg Order Value", f"${kpis['avg_order_value']:,.2f}"),
    ]
    cols = st.columns(6)
    for i, (icon, label, val) in enumerate(metrics):
        with cols[i]:
            st.markdown(f"""
            <div class="metric-card" style="animation-delay:{delays[i]}">
                <div style="font-size:1.6rem">{icon}</div>
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="section-header">Sales by Category</div>', unsafe_allow_html=True)
        if not df_cats_df.empty:
            fig = px.pie(df_cats_df, values="total_sales", names="category",
                         hole=0.5, color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="outside", textinfo="percent+label",
                              pull=[0.04]*len(df_cats_df))
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Monthly Revenue vs Profit</div>', unsafe_allow_html=True)
        if not df_monthly.empty:
            fig = go.Figure()
            fig.add_bar(x=df_monthly["month"], y=df_monthly["sales"],
                        name="Sales", marker_color="#7c83fd", opacity=0.85)
            fig.add_bar(x=df_monthly["month"], y=df_monthly["profit"],
                        name="Profit", marker_color="#f7797d", opacity=0.85)
            fig.update_layout(**PLOTLY_BASE, barmode="group",
                               legend=dict(orientation="h", y=1.12, x=0))
            st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Sales by Region</div>', unsafe_allow_html=True)
        if not df_regs_df.empty:
            fig = px.bar(df_regs_df.sort_values("total_sales"), x="total_sales", y="region",
                         orientation="h", color="total_sales",
                         color_continuous_scale=["#1a1e35","#7c83fd"], text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Profit by Category</div>', unsafe_allow_html=True)
        if not df_cats_df.empty:
            fig = px.bar(df_cats_df.sort_values("total_profit"), x="total_profit", y="category",
                         orientation="h", color="avg_margin",
                         color_continuous_scale="RdYlGn", text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, coloraxis_colorbar=dict(title="Margin%", thickness=12))
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 · TRENDS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-header">Daily Sales & Profit Trend</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Full time-series view — use date filter to zoom in</div>', unsafe_allow_html=True)

    if not df_daily.empty:
        df_daily["date"] = pd.to_datetime(df_daily["date"])
        df_daily["sales_ma7"]  = df_daily["sales"].rolling(7, center=True).mean()
        df_daily["profit_ma7"] = df_daily["profit"].rolling(7, center=True).mean()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_daily["date"], y=df_daily["sales"],
            name="Daily Sales", mode="lines",
            line=dict(color="#7c83fd", width=1), opacity=0.35,
            fill="tozeroy", fillcolor="rgba(124,131,253,0.06)"
        ))
        fig.add_trace(go.Scatter(
            x=df_daily["date"], y=df_daily["sales_ma7"],
            name="7-day MA (Sales)", mode="lines",
            line=dict(color="#7c83fd", width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=df_daily["date"], y=df_daily["profit_ma7"],
            name="7-day MA (Profit)", mode="lines",
            line=dict(color="#f7797d", width=2, dash="dot")
        ))
        fig.update_layout(**PLOTLY_BASE, hovermode="x unified",
                           legend=dict(orientation="h", y=1.12, x=0))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Monthly Trend (Line)</div>', unsafe_allow_html=True)
        if not df_monthly.empty:
            fig = go.Figure()
            fig.add_scatter(x=df_monthly["month"], y=df_monthly["sales"],
                            name="Sales", mode="lines+markers",
                            line=dict(color="#7c83fd", width=3),
                            marker=dict(size=8, symbol="circle"))
            fig.add_scatter(x=df_monthly["month"], y=df_monthly["profit"],
                            name="Profit", mode="lines+markers",
                            line=dict(color="#f7797d", width=2, dash="dash"),
                            marker=dict(size=7))
            fig.update_layout(**PLOTLY_BASE, legend=dict(orientation="h", y=1.12, x=0))
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Weekly Sales Volume</div>', unsafe_allow_html=True)
        if not df_weekly.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_weekly["Week"], y=df_weekly["sales"],
                name="Sales", marker_color="#7c83fd", opacity=0.8
            ))
            fig.add_trace(go.Scatter(
                x=df_weekly["Week"], y=df_weekly["sales"].rolling(4, center=True).mean(),
                name="4-wk MA", mode="lines", line=dict(color="#f7797d", width=2.5)
            ))
            fig.update_layout(**PLOTLY_BASE, xaxis_title="ISO Week",
                               legend=dict(orientation="h", y=1.12, x=0))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Quarterly Performance</div>', unsafe_allow_html=True)
    if not df_qtr.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_qtr["Quarter"], y=df_qtr["sales"],
                             name="Sales", marker_color="#7c83fd", opacity=0.85), secondary_y=False)
        fig.add_trace(go.Bar(x=df_qtr["Quarter"], y=df_qtr["profit"],
                             name="Profit", marker_color="#f7797d", opacity=0.85), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_qtr["Quarter"], y=df_qtr["avg_margin"],
                                 name="Avg Margin %", mode="lines+markers",
                                 line=dict(color="#43e97b", width=2.5),
                                 marker=dict(size=9)), secondary_y=True)
        fig.update_layout(**PLOTLY_BASE, barmode="group",
                           legend=dict(orientation="h", y=1.12, x=0))
        fig.update_yaxes(title_text="Revenue ($)", secondary_y=False, showgrid=False)
        fig.update_yaxes(title_text="Margin (%)", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 · TIME PATTERNS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Average Sales by Day of Week</div>', unsafe_allow_html=True)
        if not df_dow.empty:
            fig = px.bar(df_dow, x="day", y="avg_sales",
                         color="avg_sales", color_continuous_scale=["#1a1e35","#7c83fd","#a78bfa"],
                         text=df_dow["avg_sales"].map("${:,.0f}".format))
            fig.update_traces(textposition="outside")
            fig.update_layout(**PLOTLY_BASE, coloraxis_showscale=False, xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Total Transactions by Day of Week</div>', unsafe_allow_html=True)
        if not df_dow.empty:
            fig = go.Figure(go.Scatterpolar(
                r=df_dow["transactions"],
                theta=df_dow["day"],
                fill="toself",
                line=dict(color="#7c83fd", width=2),
                fillcolor="rgba(124,131,253,0.18)",
                name="Transactions"
            ))
            fig.update_layout(**PLOTLY_BASE,
                               polar=dict(
                                   bgcolor="rgba(0,0,0,0)",
                                   radialaxis=dict(showticklabels=True, tickcolor="#3a3f6a",
                                                   gridcolor="#1e2240"),
                                   angularaxis=dict(tickcolor="#3a3f6a", gridcolor="#1e2240")
                               ))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Day-of-Week Sales vs Profit</div>', unsafe_allow_html=True)
    if not df_dow.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_dow["day"], y=df_dow["sales"],  name="Total Sales",  marker_color="#7c83fd", opacity=0.8))
        fig.add_trace(go.Bar(x=df_dow["day"], y=df_dow["profit"], name="Total Profit", marker_color="#43e97b", opacity=0.8))
        fig.update_layout(**PLOTLY_BASE, barmode="group", legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Quarterly Sales Share</div>', unsafe_allow_html=True)
        if not df_qtr.empty:
            fig = px.pie(df_qtr, values="sales", names="Quarter",
                         hole=0.45, color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo="percent+label", pull=[0.04]*len(df_qtr))
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Quarterly Margin Trend</div>', unsafe_allow_html=True)
        if not df_qtr.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_qtr["Quarter"], y=df_qtr["avg_margin"],
                mode="lines+markers+text",
                text=df_qtr["avg_margin"].map("{:.1f}%".format),
                textposition="top center",
                line=dict(color="#43e97b", width=3),
                marker=dict(size=12, color="#43e97b",
                             line=dict(width=2, color="#0a0c14")),
                fill="tozeroy", fillcolor="rgba(67,233,123,0.08)"
            ))
            fig.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 · CATEGORIES
# ══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    if not df_cats_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Sales by Category</div>', unsafe_allow_html=True)
            fig = px.bar(df_cats_df.sort_values("total_sales", ascending=True),
                         x="total_sales", y="category", orientation="h",
                         color="category", color_discrete_sequence=PALETTE, text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Average Profit Margin</div>', unsafe_allow_html=True)
            fig = px.bar(df_cats_df.sort_values("avg_margin", ascending=True),
                         x="avg_margin", y="category", orientation="h",
                         color="avg_margin", color_continuous_scale="RdYlGn")
            fig.update_layout(**PLOTLY_BASE,
                               coloraxis_colorbar=dict(title="Margin%", thickness=12))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Sales vs Profit Bubble Chart</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Bubble size = number of transactions</div>', unsafe_allow_html=True)
        fig = px.scatter(df_cats_df, x="total_sales", y="total_profit", size="transactions",
                         color="category", text="category",
                         color_discrete_sequence=PALETTE, size_max=70)
        fig.update_traces(textposition="top center")
        fig.update_layout(**PLOTLY_BASE, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Category vs Monthly Sales (Area)</div>', unsafe_allow_html=True)
        dd = get_deepdive(df_filtered)
        if not dd.empty:
            pivot = dd.groupby(["month","category"])["sales"].sum().reset_index()
            month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            pivot["month"] = pd.Categorical(pivot["month"], categories=month_order, ordered=True)
            pivot = pivot.sort_values("month")
            fig = px.area(pivot, x="month", y="sales", color="category",
                          color_discrete_sequence=PALETTE)
            fig.update_layout(**PLOTLY_BASE, legend=dict(orientation="h", y=1.12))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Category Summary Table</div>', unsafe_allow_html=True)
        disp = df_cats_df.copy()
        disp["total_sales"]  = disp["total_sales"].map("${:,.0f}".format)
        disp["total_profit"] = disp["total_profit"].map("${:,.0f}".format)
        disp["avg_margin"]   = disp["avg_margin"].map("{:.1f}%".format)
        disp.columns = ["Category","Total Sales","Total Profit","Avg Margin","Transactions"]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 · REGIONS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    if not df_regs_df.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Revenue Share by Region</div>', unsafe_allow_html=True)
            fig = px.pie(df_regs_df, names="region", values="total_sales",
                         hole=0.45, color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo="percent+label", pull=[0.04]*len(df_regs_df))
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Profit vs Transactions by Region</div>', unsafe_allow_html=True)
            fig = px.scatter(df_regs_df, x="transactions", y="total_profit",
                             size="total_sales", color="region", text="region",
                             color_discrete_sequence=PALETTE, size_max=60)
            fig.update_traces(textposition="top center")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Sales by Region (Bar)</div>', unsafe_allow_html=True)
            fig = px.bar(df_regs_df, x="region", y="total_sales",
                         color="region", color_discrete_sequence=PALETTE, text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Profit by Region (Bar)</div>', unsafe_allow_html=True)
            fig = px.bar(df_regs_df, x="region", y="total_profit",
                         color="region", color_discrete_sequence=PALETTE, text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Region Summary Table</div>', unsafe_allow_html=True)
        disp = df_regs_df.copy()
        disp["total_sales"]  = disp["total_sales"].map("${:,.0f}".format)
        disp["total_profit"] = disp["total_profit"].map("${:,.0f}".format)
        disp.columns = ["Region","Total Sales","Total Profit","Transactions"]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 · HEATMAP
# ══════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="section-header">Category × Region Heatmap</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Intensity = value of selected metric</div>', unsafe_allow_html=True)

    metric_choice = st.radio("Metric", ["sales","profit","transactions"], horizontal=True)

    if not df_heatmap.empty:
        pivot = df_heatmap.pivot(index="category", columns="region", values=metric_choice).fillna(0)

        fig = go.Figure(go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="Purples",
            hoverongaps=False,
            text=pivot.values,
            texttemplate="%{text:,.0f}",
            textfont=dict(size=12),
        ))
        fig.update_layout(**PLOTLY_BASE, xaxis_title="Region", yaxis_title="Category", height=380)
        st.plotly_chart(fig, use_container_width=True)

        grp = df_heatmap.groupby("category")[metric_choice].sum().reset_index().sort_values(metric_choice, ascending=False)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Ranked by Category</div>', unsafe_allow_html=True)
            fig = px.bar(grp, x="category", y=metric_choice,
                         color=metric_choice, color_continuous_scale=["#1a1e35","#7c83fd"],
                         text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Ranked by Region</div>', unsafe_allow_html=True)
            grp2 = df_heatmap.groupby("region")[metric_choice].sum().reset_index().sort_values(metric_choice, ascending=False)
            fig = px.bar(grp2, x="region", y=metric_choice,
                         color=metric_choice, color_continuous_scale=["#1a1e35","#f7797d"],
                         text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 · DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="section-header">Deep Dive: Category × Region × Month</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)
    with col_a:
        dd_cat = st.selectbox("Filter Category", ["All"] + ALL_CATS, key="dd_cat")
    with col_b:
        dd_reg = st.selectbox("Filter Region",   ["All"] + ALL_REGIONS, key="dd_reg")

    df_dd = get_deepdive(df_filtered, dd_cat, dd_reg)

    if not df_dd.empty:
        month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        df_dd["month"] = pd.Categorical(df_dd["month"], categories=month_order, ordered=True)
        df_dd = df_dd.sort_values("month")

        st.markdown('<div class="section-header">Monthly Sales by Category per Region (Faceted)</div>', unsafe_allow_html=True)
        fig = px.line(df_dd, x="month", y="sales", color="category",
                      facet_col="region", facet_col_wrap=2,
                      color_discrete_sequence=PALETTE, markers=True)
        fig.update_layout(**PLOTLY_BASE, height=500,
                           legend=dict(orientation="h", y=-0.12))
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Stacked Sales: Category per Month</div>', unsafe_allow_html=True)
        fig = px.bar(df_dd, x="month", y="sales", color="category",
                     facet_row="region" if dd_reg == "All" else None,
                     color_discrete_sequence=PALETTE, barmode="stack")
        fig.update_layout(**PLOTLY_BASE, height=420 if dd_reg != "All" else 600,
                           legend=dict(orientation="h", y=1.05))
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Deep Dive Data Table</div>', unsafe_allow_html=True)
        disp = df_dd.copy()
        disp["sales"]  = disp["sales"].map("${:,.0f}".format)
        disp["profit"] = disp["profit"].map("${:,.0f}".format)
        disp.columns   = [c.capitalize() for c in disp.columns]
        st.dataframe(disp, use_container_width=True, hide_index=True, height=300)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 · AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-header">🤖 AI Sales Analyst — Powered by Gemini</div>', unsafe_allow_html=True)
    st.caption("Each browser tab gets its own private session. Gemini answers from real data only.")

    if not GEMINI_API_KEY:
        st.warning("⚠️ GEMINI_API_KEY not set. Add it in Streamlit Cloud → Settings → Secrets:\n```\nGEMINI_API_KEY = \"AIza...\"\n```")
    else:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        suggestions = [
            "Which category had the highest profit margin?",
            "What was the best performing region?",
            "Which month had the highest sales?",
            "Compare Electronics vs Clothing",
            "What day of the week sells the most?",
            "Give me a full performance summary",
            "Which region has the lowest profit margin?",
            "What are the top 5 category-region combos?",
        ]

        if not st.session_state.chat_history:
            st.markdown("**💡 Quick questions:**")
            cols = st.columns(4)
            for i, s in enumerate(suggestions):
                with cols[i % 4]:
                    if st.button(s, key=f"sugg_{i}", use_container_width=True):
                        st.session_state.pending_message = s
                        st.rerun()

        # Render history
        chat_html = '<div class="chat-wrap">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f'<div class="chat-label-user">You</div><div class="chat-msg-user">{msg["parts"][0]}</div>'
            else:
                chat_html += f'<div class="chat-label-ai">🤖 Gemini Analyst</div><div class="chat-msg-ai">{msg["parts"][0]}</div>'
        chat_html += "</div>"
        if st.session_state.chat_history:
            st.markdown(chat_html, unsafe_allow_html=True)

        # Send pending message
        pending = st.session_state.pop("pending_message", None)
        if pending:
            with st.spinner("Gemini is thinking…"):
                reply, err = gemini_chat(st.session_state.chat_history, pending, DATA_SUMMARY)
                if err:
                    st.error(f"Gemini error: {err}")
                else:
                    st.rerun()

        st.markdown("---")
        col_inp, col_send, col_clr = st.columns([7, 1, 1])
        with col_inp:
            user_input = st.text_input("msg", placeholder="Ask anything about your sales data…",
                                       label_visibility="collapsed",
                                       key=f"inp_{len(st.session_state.chat_history)}")
        with col_send:
            send = st.button("Send ➤", use_container_width=True)
        with col_clr:
            if st.button("Clear 🗑️", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        if send and user_input.strip():
            st.session_state.pending_message = user_input.strip()
            st.rerun()

        with st.expander("Session info"):
            st.code(f"Messages : {len(st.session_state.chat_history)}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 · RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="section-header">Raw Transaction Data</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([2, 2, 2])
    with col_a:
        sort_col = st.selectbox("Sort by", ["Date","Sales","Profit","Quantity"], index=0)
    with col_b:
        sort_dir = st.radio("Direction", ["Descending","Ascending"], horizontal=True)
    with col_c:
        page_size = st.select_slider("Rows per page", [50, 100, 200, 500], value=100)

    if "raw_offset" not in st.session_state:
        st.session_state.raw_offset = 0

    raw = get_raw(df_filtered, limit=page_size, offset=st.session_state.raw_offset,
                  sort_by=sort_col, sort_dir="asc" if sort_dir == "Ascending" else "desc")

    total = raw["total"]
    start = st.session_state.raw_offset + 1
    end   = min(st.session_state.raw_offset + page_size, total)
    st.caption(f"Showing rows **{start:,}–{end:,}** of **{total:,}** (filtered)")
    df_raw = raw["data"]
    if not df_raw.empty:
        def color_profit(val):
            try:
                v = float(val)
                return "color: #4ade80" if v > 0 else "color: #f87171"
            except:
                return ""
        st.dataframe(df_raw.style.map(color_profit, subset=["Profit"] if "Profit" in df_raw.columns else []),
                     use_container_width=True, height=420)

    c1, c2, c3 = st.columns([1, 1, 5])
    with c1:
        if st.button("⬅️ Prev") and st.session_state.raw_offset >= page_size:
            st.session_state.raw_offset -= page_size
            st.rerun()
    with c2:
        if st.button("Next ➡️") and st.session_state.raw_offset + page_size < total:
            st.session_state.raw_offset += page_size
            st.rerun()
    with c3:
        if total > 0:
            page_num    = st.session_state.raw_offset // page_size + 1
            total_pages = (total + page_size - 1) // page_size
            st.markdown(f'<span style="color:#6b7290;font-size:.82rem">Page {page_num} of {total_pages}</span>',
                         unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 10 · DATA QUALITY
# ══════════════════════════════════════════════════════════════════════════════
with tabs[9]:
    st.markdown('<div class="section-header">🩺 Data Quality Report</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Profiling of the loaded dataset after cleaning</div>', unsafe_allow_html=True)

    q = quality_raw
    completeness = round(q["complete_rows"] / q["total_rows"] * 100, 1) if q["total_rows"] else 0

    c1, c2, c3, c4 = st.columns(4)
    for col, icon, label, val in [
        (c1, "📋", "Total Rows",     f"{q['total_rows']:,}"),
        (c2, "✅", "Complete Rows",  f"{q['complete_rows']:,}"),
        (c3, "🔁", "Duplicate Rows", f"{q['duplicate_rows']:,}"),
        (c4, "📅", "Date Range",     f"{q['date_min']} → {q['date_max']}"),
    ]:
        with col:
            st.markdown(f'<div class="metric-card"><div style="font-size:1.4rem">{icon}</div>'
                         f'<div class="metric-value" style="font-size:1.4rem">{val}</div>'
                         f'<div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

    st.markdown("")
    st.markdown(f'<div class="section-header">Completeness: {completeness}%</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="quality-bar"><div class="quality-fill" style="width:{completeness}%"></div></div>',
        unsafe_allow_html=True
    )
    st.markdown("")

    missing = {
        "Date":     q["missing_dates"],
        "Category": q["missing_categories"],
        "Region":   q["missing_regions"],
        "Sales":    q["missing_sales"],
        "Profit":   q["missing_profit"],
        "Quantity": q["missing_quantity"],
    }
    df_miss = pd.DataFrame({"Column": list(missing.keys()), "Missing": list(missing.values())})
    df_miss["% Missing"] = (df_miss["Missing"] / q["total_rows"] * 100).round(2)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Missing Values by Column</div>', unsafe_allow_html=True)
        fig = px.bar(df_miss, x="Column", y="Missing",
                     color="Missing", color_continuous_scale=["#1a1e35","#f7797d"],
                     text="Missing")
        fig.update_traces(textposition="outside")
        fig.update_layout(**PLOTLY_BASE, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Sales Distribution</div>', unsafe_allow_html=True)
        if not df_filtered.empty:
            fig = px.histogram(df_filtered, x="Sales", nbins=40,
                               color_discrete_sequence=["#7c83fd"])
            fig.update_layout(**PLOTLY_BASE)
            st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    stats = [
        ("Sales",  q["sales_min"],  q["sales_max"],  q["sales_mean"]),
        ("Profit", q["profit_min"], q["profit_max"], None),
    ]
    for col, (name, mn, mx, avg) in zip([c1, c2], stats):
        with col:
            st.markdown(f'<div class="section-header">{name} Stats</div>', unsafe_allow_html=True)
            rows = {"Min": f"${mn:,.2f}", "Max": f"${mx:,.2f}"}
            if avg is not None:
                rows["Mean"] = f"${avg:,.2f}"
            for k, v in rows.items():
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #1e2240">'
                             f'<span style="color:#6b7290">{k}</span><span style="color:#c5cae9;font-weight:600">{v}</span></div>',
                             unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="section-header">Schema</div>', unsafe_allow_html=True)
        schema = {
            "Date": "datetime", "Category": "string", "Region": "string",
            "Sales": "float", "Quantity": "int", "Profit": "float",
            "Profit_Margin": "float (derived)", "Quarter": "string (derived)",
        }
        for col_name, dtype in schema.items():
            st.markdown(f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #1e2240">'
                         f'<span style="color:#c5cae9;font-size:.85rem">{col_name}</span>'
                         f'<span style="color:#7c83fd;font-size:.82rem">{dtype}</span></div>',
                         unsafe_allow_html=True)