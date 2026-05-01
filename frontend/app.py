# frontend/app.py
# Streamlit dashboard — complete rewrite with all charts, filters, and animated components.

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import os
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
PORT = os.getenv("BACKEND_PORT", "8000")
BASE = f"http://{HOST}:{PORT}"

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Retail Sales Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Remove sidebar toggle button via JS ──────────────────────────────────────
components.html("""
<script>
(function fixStreamlitIcons() {
    function injectFont() {
        const parent = window.parent.document;
        if (!parent.querySelector('link[href*="Material+Icons"]')) {
            ['Material+Icons', 'Material+Icons+Round', 'Material+Icons+Outlined'].forEach(family => {
                const link = parent.createElement('link');
                link.rel  = 'stylesheet';
                link.href = `https://fonts.googleapis.com/icon?family=${family}`;
                parent.head.appendChild(link);
            });
        }
    }
    injectFont();
    new MutationObserver(injectFont).observe(
        window.parent.document.body,
        { childList: true, subtree: true }
    );
})();
</script>
""", height=0)

# ─── Custom CSS + React-style animations ──────────────────────────────────────
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

    /* ── Animated metric cards ── */
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
        border: 1px solid #252a48;
        border-radius: 14px;
        padding: 22px 18px;
        text-align: center;
        box-shadow: 0 4px 24px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.04);
        animation: fadeSlideUp 0.45s ease both;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative; overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 2px;
        background: linear-gradient(90deg, transparent, #7c83fd, transparent);
        background-size: 200% auto;
        animation: shimmer 3s linear infinite;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(124,131,253,.2);
    }
    .metric-value {
        font-size: 1.85rem; font-weight: 700;
        background: linear-gradient(135deg, #7c83fd, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .metric-label { font-size: .78rem; color: #6b7290; margin-top: 6px; letter-spacing: .04em; text-transform: uppercase; }
    .metric-delta { font-size: .82rem; margin-top: 4px; }
    .delta-pos { color: #4ade80; }
    .delta-neg { color: #f87171; }

    /* ── Section headers ── */
    .section-header {
        font-size: 1.05rem; font-weight: 600; color: #c5cae9;
        border-left: 3px solid #7c83fd; padding-left: 12px;
        margin: 28px 0 14px;
    }
    .section-sub {
        font-size: .82rem; color: #6b7290; margin-top: -10px; margin-bottom: 14px; padding-left: 15px;
    }

    /* ── Chat ── */
    .chat-wrap { max-height: 480px; overflow-y: auto; padding: 4px 0; scroll-behavior: smooth; }
    .chat-msg-user {
        background: linear-gradient(135deg, #2a2d4a, #323565);
        border: 1px solid #3a3f6a;
        border-radius: 14px 14px 4px 14px; padding: 12px 16px;
        margin: 6px 0 6px 60px; color: #e0e4f7; font-size: .91rem; line-height: 1.55;
        animation: fadeSlideUp .25s ease both;
    }
    .chat-msg-ai {
        background: linear-gradient(135deg, #13162b, #1a1e35);
        border: 1px solid #7c83fd44;
        border-radius: 14px 14px 14px 4px; padding: 12px 16px;
        margin: 6px 60px 6px 0; color: #c5cae9; font-size: .91rem; line-height: 1.6;
        animation: fadeSlideUp .25s ease both;
    }
    .chat-label-user { text-align:right; font-size:.72rem; color:#6b7290; margin:4px 4px 0 0; }
    .chat-label-ai   { font-size:.72rem; color:#7c83fd; margin:4px 0 0 4px; }

    /* ── Quality badge ── */
    .quality-bar { background: #1a1e35; border-radius: 8px; height: 8px; overflow: hidden; margin-top: 4px; }
    .quality-fill { height: 100%; border-radius: 8px; background: linear-gradient(90deg, #7c83fd, #4ade80); transition: width .8s ease; }

    /* ── Sidebar filter group ── */
    .filter-label { font-size: .75rem; color: #7c83fd; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; font-weight: 600; }

    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] *,
    section[data-testid="stSidebarCollapsedControl"],
    button[aria-label="Close sidebar"],
    button[aria-label="Open sidebar"] { display: none !important; visibility: hidden !important; }
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

# ─── API helper ────────────────────────────────────────────────────────────────
def api(path: str, method="GET", json=None, params=None):
    try:
        r = requests.request(method, f"{BASE}{path}", json=json, params=params, timeout=20)
        try:
            data = r.json()
        except Exception:
            data = {"detail": r.text[:300] or f"HTTP {r.status_code}"}
        if r.status_code >= 400:
            st.error(f"❌ API {r.status_code}: {data.get('detail', data)}")
            return None
        return data
    except requests.exceptions.ConnectionError:
        st.error(
            "❌ Cannot reach the FastAPI backend.\n\n"
            "```\nuvicorn backend.main:app --reload --host 127.0.0.1 --port 8000\n```"
        )
        st.stop()
    except requests.exceptions.Timeout:
        st.error("❌ Request timed out.")
        return None
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None

def build_params(date_from=None, date_to=None, categories=None, regions=None):
    p = {}
    if date_from:  p["date_from"]  = str(date_from)
    if date_to:    p["date_to"]    = str(date_to)
    if categories: p["categories"] = ",".join(categories)
    if regions:    p["regions"]    = ",".join(regions)
    return p or None

# ─── Health check ──────────────────────────────────────────────────────────────
health = api("/health")
if not health:
    st.stop()

ALL_CATS    = health.get("categories", [])
ALL_REGIONS = health.get("regions", [])
DATE_MIN    = health.get("date_min", "2023-01-01")
DATE_MAX    = health.get("date_max", "2023-12-31")

# ─── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🛒 Retail Sales")
    st.markdown(
        f'<span class="status-ok">● Backend online</span><br>'
        f'<span style="color:#6b7290;font-size:.8rem">{health["rows_loaded"]:,} rows · {DATE_MIN} → {DATE_MAX}</span>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown('<div class="filter-label">📅 Date Range</div>', unsafe_allow_html=True)
    d_from = st.date_input("From", value=date.fromisoformat(DATE_MIN), min_value=date.fromisoformat(DATE_MIN), max_value=date.fromisoformat(DATE_MAX), label_visibility="collapsed", key="d_from")
    d_to   = st.date_input("To",   value=date.fromisoformat(DATE_MAX), min_value=date.fromisoformat(DATE_MIN), max_value=date.fromisoformat(DATE_MAX), label_visibility="collapsed", key="d_to")
    st.markdown('<div class="filter-label" style="margin-top:12px">🏷️ Categories</div>', unsafe_allow_html=True)
    sel_cats = st.multiselect("Categories", ALL_CATS, default=ALL_CATS, label_visibility="collapsed", key="sel_cats")
    st.markdown('<div class="filter-label" style="margin-top:12px">🌐 Regions</div>', unsafe_allow_html=True)
    sel_regs = st.multiselect("Regions", ALL_REGIONS, default=ALL_REGIONS, label_visibility="collapsed", key="sel_regs")
    if st.button("↺ Reset Filters", use_container_width=True):
        for k in ["d_from", "d_to", "sel_cats", "sel_regs"]:
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()
    st.markdown("---")
    st.markdown('<div style="font-size:.75rem;color:#6b7290">FastAPI + Streamlit + Gemini AI<br>All charts respond to filters above.</div>', unsafe_allow_html=True)

# Guard: empty selection
if not sel_cats or not sel_regs:
    st.warning("Please select at least one Category and one Region in the sidebar.")
    st.stop()

f_cats = sel_cats if len(sel_cats) < len(ALL_CATS) else None
f_regs = sel_regs if len(sel_regs) < len(ALL_REGIONS) else None
PARAMS = build_params(d_from, d_to, f_cats, f_regs)

# ─── Cached data fetchers ──────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch(endpoint, params_key):
    return api(endpoint, params=dict(params_key) if params_key else None)

def p_key(p): return tuple(sorted(p.items())) if p else ()

kpis_raw    = fetch("/analytics/kpis",      p_key(PARAMS))
cats_raw    = fetch("/analytics/categories", p_key(build_params(d_from, d_to, None, f_regs)))
regs_raw    = fetch("/analytics/regions",    p_key(build_params(d_from, d_to, f_cats, None)))
monthly_raw = fetch("/analytics/monthly",    p_key(PARAMS))
daily_raw   = fetch("/analytics/daily",      p_key(PARAMS))
weekly_raw  = fetch("/analytics/weekly",     p_key(PARAMS))
dow_raw     = fetch("/analytics/dayofweek",  p_key(PARAMS))
quarterly_raw = fetch("/analytics/quarterly", p_key(PARAMS))
heatmap_raw = fetch("/analytics/heatmap",    p_key(build_params(d_from, d_to)))
quality_raw = fetch("/analytics/quality",    None)

df_cats     = pd.DataFrame(cats_raw     or [])
df_regs     = pd.DataFrame(regs_raw     or [])
df_monthly  = pd.DataFrame(monthly_raw  or [])
df_daily    = pd.DataFrame(daily_raw    or [])
df_weekly   = pd.DataFrame(weekly_raw   or [])
df_dow      = pd.DataFrame(dow_raw      or [])
df_qtr      = pd.DataFrame(quarterly_raw or [])
df_heatmap  = pd.DataFrame(heatmap_raw  or [])

# ─── Page title ────────────────────────────────────────────────────────────────
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
    if kpis_raw:
        kpis = kpis_raw
        delays = ["0.05s","0.12s","0.19s","0.26s","0.33s","0.40s"]
        metrics = [
            ("💰", "Total Sales",     f"${kpis['total_sales']:,.0f}"),
            ("📈", "Total Profit",    f"${kpis['total_profit']:,.0f}"),
            ("📦", "Units Sold",      f"{kpis['total_quantity']:,.0f}"),
            ("🎯", "Avg Margin",      f"{kpis['avg_margin']:.1f}%"),
            ("🧾", "Transactions",    f"{kpis['total_transactions']:,}"),
            ("🛍️","Avg Order Value",  f"${kpis['avg_order_value']:,.2f}"),
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
        if not df_cats.empty:
            fig = px.pie(df_cats, values="total_sales", names="category",
                         hole=0.5, color_discrete_sequence=PALETTE)
            fig.update_traces(textposition="outside", textinfo="percent+label",
                              pull=[0.04]*len(df_cats))
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Monthly Revenue vs Profit</div>', unsafe_allow_html=True)
        if not df_monthly.empty:
            fig = go.Figure()
            fig.add_bar(x=df_monthly["month"], y=df_monthly["sales"],  name="Sales",  marker_color="#7c83fd", opacity=0.85)
            fig.add_bar(x=df_monthly["month"], y=df_monthly["profit"], name="Profit", marker_color="#f7797d", opacity=0.85)
            fig.update_layout(**PLOTLY_BASE, barmode="group", legend=dict(orientation="h", y=1.12, x=0))
            st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">Sales by Region</div>', unsafe_allow_html=True)
        if not df_regs.empty:
            fig = px.bar(df_regs.sort_values("total_sales"), x="total_sales", y="region",
                         orientation="h", color="total_sales",
                         color_continuous_scale=["#1a1e35","#7c83fd"], text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, coloraxis_showscale=False, yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Profit by Category</div>', unsafe_allow_html=True)
        if not df_cats.empty:
            fig = px.bar(df_cats.sort_values("total_profit"), x="total_profit", y="category",
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
        # 7-day rolling average
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
                x=df_weekly["week"], y=df_weekly["sales"],
                name="Sales", marker_color="#7c83fd", opacity=0.8
            ))
            fig.add_trace(go.Scatter(
                x=df_weekly["week"], y=df_weekly["sales"].rolling(4, center=True).mean(),
                name="4-wk MA", mode="lines", line=dict(color="#f7797d", width=2.5)
            ))
            fig.update_layout(**PLOTLY_BASE, xaxis_title="ISO Week",
                               legend=dict(orientation="h", y=1.12, x=0))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">Quarterly Performance</div>', unsafe_allow_html=True)
    if not df_qtr.empty:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=df_qtr["quarter"], y=df_qtr["sales"],
                             name="Sales", marker_color="#7c83fd", opacity=0.85), secondary_y=False)
        fig.add_trace(go.Bar(x=df_qtr["quarter"], y=df_qtr["profit"],
                             name="Profit", marker_color="#f7797d", opacity=0.85), secondary_y=False)
        fig.add_trace(go.Scatter(x=df_qtr["quarter"], y=df_qtr["avg_margin"],
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
            fig = px.pie(df_qtr, values="sales", names="quarter",
                         hole=0.45, color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo="percent+label", pull=[0.04]*len(df_qtr))
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown('<div class="section-header">Quarterly Margin Trend</div>', unsafe_allow_html=True)
        if not df_qtr.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_qtr["quarter"], y=df_qtr["avg_margin"],
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
    if not df_cats.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Sales by Category</div>', unsafe_allow_html=True)
            fig = px.bar(df_cats.sort_values("total_sales", ascending=True),
                         x="total_sales", y="category", orientation="h",
                         color="category", color_discrete_sequence=PALETTE, text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Average Profit Margin</div>', unsafe_allow_html=True)
            fig = px.bar(df_cats.sort_values("avg_margin", ascending=True),
                         x="avg_margin", y="category", orientation="h",
                         color="avg_margin", color_continuous_scale="RdYlGn")
            fig.update_layout(**PLOTLY_BASE,
                               coloraxis_colorbar=dict(title="Margin%", thickness=12))
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Sales vs Profit Bubble Chart</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-sub">Bubble size = number of transactions</div>', unsafe_allow_html=True)
        fig = px.scatter(df_cats, x="total_sales", y="total_profit", size="transactions",
                         color="category", text="category",
                         color_discrete_sequence=PALETTE, size_max=70)
        fig.update_traces(textposition="top center")
        fig.update_layout(**PLOTLY_BASE, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Category vs Monthly Sales (Area)</div>', unsafe_allow_html=True)
        if not df_daily.empty:
            dd_raw = fetch("/analytics/deepdive", p_key(build_params(d_from, d_to, f_cats, f_regs)))
            if dd_raw:
                dd = pd.DataFrame(dd_raw)
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
        disp = df_cats.copy()
        disp["total_sales"]  = disp["total_sales"].map("${:,.0f}".format)
        disp["total_profit"] = disp["total_profit"].map("${:,.0f}".format)
        disp["avg_margin"]   = disp["avg_margin"].map("{:.1f}%".format)
        disp.columns = ["Category","Total Sales","Total Profit","Avg Margin","Transactions"]
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 · REGIONS
# ══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    if not df_regs.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Revenue Share by Region</div>', unsafe_allow_html=True)
            fig = px.pie(df_regs, names="region", values="total_sales",
                         hole=0.45, color_discrete_sequence=PALETTE)
            fig.update_traces(textinfo="percent+label", pull=[0.04]*len(df_regs))
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Profit vs Transactions by Region</div>', unsafe_allow_html=True)
            fig = px.scatter(df_regs, x="transactions", y="total_profit",
                             size="total_sales", color="region", text="region",
                             color_discrete_sequence=PALETTE, size_max=60)
            fig.update_traces(textposition="top center")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="section-header">Sales by Region (Bar)</div>', unsafe_allow_html=True)
            fig = px.bar(df_regs, x="region", y="total_sales",
                         color="region", color_discrete_sequence=PALETTE, text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="section-header">Profit by Region (Bar)</div>', unsafe_allow_html=True)
            fig = px.bar(df_regs, x="region", y="total_profit",
                         color="region", color_discrete_sequence=PALETTE, text_auto=".2s")
            fig.update_layout(**PLOTLY_BASE, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="section-header">Region Summary Table</div>', unsafe_allow_html=True)
        disp = df_regs.copy()
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
            colorscale="Jet",
            hoverongaps=False,
            text=pivot.values,
            texttemplate="%{text:,.0f}",
            textfont=dict(size=12),
        ))
        fig.update_layout(**PLOTLY_BASE, xaxis_title="Region", yaxis_title="Category",
                           height=380)
        st.plotly_chart(fig, use_container_width=True)

        # Ranked bar by category for chosen metric
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

    dd_params = build_params(
        d_from, d_to,
        [dd_cat] if dd_cat != "All" else None,
        [dd_reg] if dd_reg != "All" else None,
    )
    @st.cache_data(ttl=60)
    def fetch_dd(pk):
        return api("/analytics/deepdive", params=dict(pk) if pk else None)

    dd_raw2 = fetch_dd(p_key(dd_params))
    df_dd = pd.DataFrame(dd_raw2 or [])

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
        disp["sales"]   = disp["sales"].map("${:,.0f}".format)
        disp["profit"]  = disp["profit"].map("${:,.0f}".format)
        disp.columns = [c.capitalize() for c in disp.columns]
        st.dataframe(disp, use_container_width=True, hide_index=True, height=300)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 · AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="section-header">🤖 AI Sales Analyst — Powered by Gemini</div>', unsafe_allow_html=True)
    st.caption("Each browser tab gets its own private session. Gemini answers from real data only.")

    if "session_id" not in st.session_state:
        res = api("/session/new", method="POST")
        if res:
            st.session_state.session_id  = res["session_id"]
            st.session_state.chat_history = []

    sid = st.session_state.get("session_id", "")

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

    if not st.session_state.get("chat_history"):
        st.markdown("**💡 Quick questions:**")
        cols = st.columns(4)
        for i, s in enumerate(suggestions):
            with cols[i % 4]:
                if st.button(s, key=f"sugg_{i}", use_container_width=True):
                    st.session_state.pending_message = s
                    st.rerun()

    # Render history
    chat_html = '<div class="chat-wrap">'
    for msg in st.session_state.get("chat_history", []):
        if msg["role"] == "user":
            chat_html += f'<div class="chat-label-user">You</div><div class="chat-msg-user">{msg["text"]}</div>'
        else:
            chat_html += f'<div class="chat-label-ai">🤖 Gemini Analyst</div><div class="chat-msg-ai">{msg["text"]}</div>'
    chat_html += "</div>"
    if st.session_state.get("chat_history"):
        st.markdown(chat_html, unsafe_allow_html=True)

    # Send pending message
    pending = st.session_state.pop("pending_message", None)
    if pending and sid:
        with st.spinner("Gemini is thinking…"):
            res = api("/chat", method="POST", json={"session_id": sid, "message": pending})
            if res:
                st.session_state.chat_history = res["history"]
                st.rerun()

    st.markdown("---")
    col_inp, col_send, col_clr = st.columns([7, 1, 1])
    with col_inp:
        user_input = st.text_input("msg", placeholder="Ask anything about your sales data…",
                                   label_visibility="collapsed",
                                   key=f"inp_{len(st.session_state.get('chat_history',[]))}")
    with col_send:
        send = st.button("Send ➤", use_container_width=True)
    with col_clr:
        if st.button("Clear 🗑️", use_container_width=True) and sid:
            api(f"/session/{sid}", method="DELETE")
            st.session_state.chat_history = []
            st.rerun()

    if send and user_input.strip():
        st.session_state.pending_message = user_input.strip()
        st.rerun()

    with st.expander("🔍 Session info"):
        st.code(f"Session ID : {sid}\nMessages   : {len(st.session_state.get('chat_history', []))}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 9 · RAW DATA
# ══════════════════════════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="section-header">Raw Transaction Data</div>', unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([2,2,2])
    with col_a:
        sort_col = st.selectbox("Sort by", ["Date","Sales","Profit","Quantity"], index=0)
    with col_b:
        sort_dir = st.radio("Direction", ["Descending","Ascending"], horizontal=True)
    with col_c:
        page_size = st.select_slider("Rows per page", [50, 100, 200, 500], value=100)

    if "raw_offset" not in st.session_state:
        st.session_state.raw_offset = 0

    raw_params = {**(PARAMS or {}),
                  "sort_by": sort_col,
                  "sort_dir": "asc" if sort_dir=="Ascending" else "desc"}
    raw = api(f"/analytics/raw?limit={page_size}&offset={st.session_state.raw_offset}", params=raw_params)

    if raw:
        total = raw["total"]
        start = st.session_state.raw_offset + 1
        end   = min(st.session_state.raw_offset + page_size, total)
        st.caption(f"Showing rows **{start:,}–{end:,}** of **{total:,}** (filtered)")
        df_raw = pd.DataFrame(raw["data"])
        if not df_raw.empty:
            # Highlight profit with color
            def color_profit(val):
                try:
                    v = float(val)
                    return "color: #4ade80" if v > 0 else "color: #f87171"
                except:
                    return ""
            st.dataframe(df_raw.style.applymap(color_profit, subset=["Profit"] if "Profit" in df_raw.columns else []),
                         use_container_width=True, height=420)

        c1, c2, c3 = st.columns([1,1,5])
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
                page_num = st.session_state.raw_offset // page_size + 1
                total_pages = (total + page_size - 1) // page_size
                st.markdown(f'<span style="color:#6b7290;font-size:.82rem">Page {page_num} of {total_pages}</span>',
                             unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 10 · DATA QUALITY
# ══════════════════════════════════════════════════════════════════════════════
with tabs[9]:
    st.markdown('<div class="section-header">🩺 Data Quality Report</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Profiling of the loaded dataset after cleaning</div>', unsafe_allow_html=True)

    if quality_raw:
        q = quality_raw
        completeness = round(q["complete_rows"] / q["total_rows"] * 100, 1) if q["total_rows"] else 0

        c1, c2, c3, c4 = st.columns(4)
        for col, icon, label, val in [
            (c1, "📋", "Total Rows",       f"{q['total_rows']:,}"),
            (c2, "✅", "Complete Rows",    f"{q['complete_rows']:,}"),
            (c3, "🔁", "Duplicate Rows",   f"{q['duplicate_rows']:,}"),
            (c4, "📅", "Date Range",       f"{q['date_min']} → {q['date_max']}"),
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

        # Missing values
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
            if not df_daily.empty:
                # Fetch raw for histogram
                raw_h = api("/analytics/raw", params={"limit": 2000, "offset": 0})
                if raw_h and raw_h.get("data"):
                    df_hist = pd.DataFrame(raw_h["data"])
                    fig = px.histogram(df_hist, x="Sales", nbins=40,
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