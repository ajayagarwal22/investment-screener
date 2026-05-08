"""
NSE/BSE Professional Equity Screener & Alerting System
Senior-grade 8-layer analysis: VST / ST / LT horizons
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

from engines.orchestrator import run_full_analysis, run_batch_screen, get_market_regime
from engines.technical import compute_ema, compute_rsi, compute_macd, compute_bollinger
from utils.config import POPULAR_STOCKS, SECTOR_MAP, SCREENER_PRESETS
from utils.nse_symbols import get_nse_symbol_map, get_search_options, symbol_from_option, nse_live_search
from utils.formatters import (
    color_badge, action_color, regime_color, risk_color, quality_color,
    sentiment_color, fmt_crore, fmt_pct, fmt_price, fmt_ratio,
    score_bar_html, rr_badge,
)

# ── NSE symbol list — cached for the session, refreshed weekly ────────────────
@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def _load_search_options() -> tuple[list[str], dict[str, str]]:
    sym_map = get_nse_symbol_map()
    options = get_search_options(sym_map)
    return options, sym_map


@st.cache_data(ttl=300, show_spinner=False)
def _nse_live_search(query: str) -> list[str]:
    """Cached wrapper around NSE live search — includes SME/Emerge stocks."""
    return nse_live_search(query)


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Pro Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Base dark theme refinements */
  .main { background-color: #0e1117; }
  .block-container { padding-top: 1rem; padding-bottom: 2rem; }

  /* Metric cards */
  .metric-card {
    background: #1c2333;
    border: 1px solid #2d3748;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 4px 0;
  }
  .metric-label { font-size: 0.75em; color: #8892a4; text-transform: uppercase; letter-spacing: 0.05em; }
  .metric-value { font-size: 1.4em; font-weight: 700; color: #e2e8f0; margin-top: 2px; }
  .metric-sub   { font-size: 0.78em; color: #a0aec0; margin-top: 2px; }

  /* Section headers */
  .section-header {
    font-size: 0.85em;
    font-weight: 700;
    color: #4a9eff;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    border-bottom: 1px solid #2d3748;
    padding-bottom: 4px;
    margin: 16px 0 10px 0;
  }

  /* Action pill */
  .action-pill {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 700;
    font-size: 1.0em;
    letter-spacing: 0.03em;
  }

  /* Warning box */
  .warning-box {
    background: #2d1b00;
    border-left: 3px solid #ff9800;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 0.83em;
    color: #ffd080;
    margin: 4px 0;
  }
  .red-flag-box {
    background: #2d0000;
    border-left: 3px solid #f44336;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 0.83em;
    color: #ff8080;
    margin: 4px 0;
  }
  .bull-box {
    background: #001a0d;
    border-left: 3px solid #4caf50;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 0.83em;
    color: #80e080;
    margin: 4px 0;
  }

  /* Table styling */
  .screener-table th {
    background: #1c2333 !important;
    color: #4a9eff !important;
    font-size: 0.8em !important;
  }

  /* Sidebar */
  .sidebar .sidebar-content { background: #141923; }

  /* Ticker badge */
  .ticker-badge {
    font-size: 2em;
    font-weight: 800;
    color: #e2e8f0;
    letter-spacing: 0.05em;
  }
  .price-display {
    font-size: 2.2em;
    font-weight: 700;
    color: #4caf50;
  }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Draw candlestick with EMA + RSI + Volume
# ─────────────────────────────────────────────────────────────────────────────

def draw_chart(df: pd.DataFrame, symbol: str,
               label: str = "Daily",
               ema_periods: list = None,
               max_bars: int = 1260,
               interval: str = "1d",
               init_bars: int = 120) -> go.Figure:
    if df is None or df.empty:
        return go.Figure()
    if ema_periods is None:
        ema_periods = [20, 50, 200]

    close  = df["Close"].squeeze()
    high   = df["High"].squeeze()
    low    = df["Low"].squeeze()
    open_  = df["Open"].squeeze()
    volume = df["Volume"].squeeze()
    dates  = df.index

    n = min(len(df), max_bars)
    close  = close.iloc[-n:]
    high   = high.iloc[-n:]
    low    = low.iloc[-n:]
    open_  = open_.iloc[-n:]
    volume = volume.iloc[-n:]
    dates  = dates[-n:]

    is_intraday = interval in ("5m", "15m", "1h", "60m")

    # Always use category axis — prevents empty space when zooming out on all timeframes
    if is_intraday:
        x = [pd.Timestamp(d).strftime("%d/%m %H:%M") for d in dates]
        tickvals, ticktext = [], []
        prev_date = None
        for i, d in enumerate(dates):
            ts = pd.Timestamp(d)
            is_new_day = ts.date() != prev_date
            if is_new_day or ts.minute == 0:
                tickvals.append(x[i])
                ticktext.append(
                    f"{ts.strftime('%H:%M')}<br>{ts.strftime('%d %b')}" if is_new_day
                    else ts.strftime("%H:%M")
                )
                prev_date = ts.date()
    elif interval in ("1wk", "1mo"):
        fmt = "%b '%y"
        x = [pd.Timestamp(d).strftime(fmt) for d in dates]
        tickvals = x[::max(1, len(x)//20)]
        ticktext = tickvals
    else:
        # Daily — show "DD Mon" ticks, one per month boundary
        x = [pd.Timestamp(d).strftime("%d %b '%y") for d in dates]
        tickvals, ticktext = [], []
        prev_month = None
        for i, d in enumerate(dates):
            ts = pd.Timestamp(d)
            if ts.month != prev_month:
                tickvals.append(x[i])
                ticktext.append(ts.strftime("%b '%y"))
                prev_month = ts.month
    x_rev = x[::-1]

    ema_colors = ["#FFA726", "#42A5F5", "#EF5350"]
    emas = [(p, compute_ema(close, p), ema_colors[i % 3])
            for i, p in enumerate(ema_periods) if len(close) >= p]

    rsi = compute_rsi(close, 14)
    bb_up, bb_mid, bb_lo = compute_bollinger(close)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        row_heights=[0.6, 0.2, 0.2],
        vertical_spacing=0.02,
        subplot_titles=("", "Volume", "RSI (14)"),
    )

    # ── Candlestick ───────────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=x, open=open_.values, high=high.values, low=low.values, close=close.values,
        name="Price",
        increasing_line_color="#4caf50", decreasing_line_color="#f44336",
        increasing_fillcolor="#4caf50",  decreasing_fillcolor="#f44336",
    ), row=1, col=1)

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(
        x=x + x_rev,
        y=list(bb_up.values) + list(bb_lo.values[::-1]),
        fill="toself", fillcolor="rgba(74,158,255,0.06)",
        line=dict(color="rgba(0,0,0,0)"),
        name="Bollinger Band", showlegend=False,
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=bb_up.values,  line=dict(color="rgba(74,158,255,0.4)", width=1, dash="dot"), name="BB Upper", showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=bb_mid.values, line=dict(color="rgba(74,158,255,0.3)", width=1, dash="dot"), name="BB Mid",   showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=bb_lo.values,  line=dict(color="rgba(74,158,255,0.4)", width=1, dash="dot"), name="BB Lower", showlegend=False), row=1, col=1)

    # ── EMAs ──────────────────────────────────────────────────────────────────
    for period, ema_vals, color in emas:
        width = 2.0 if period == ema_periods[-1] else 1.5
        fig.add_trace(go.Scatter(x=x, y=ema_vals.values,
                                 line=dict(color=color, width=width),
                                 name=f"EMA {period}"), row=1, col=1)

    # ── Volume ────────────────────────────────────────────────────────────────
    colors = ["#4caf50" if c >= o else "#f44336"
              for c, o in zip(close.values, open_.values)]
    fig.add_trace(go.Bar(x=x, y=volume.values, name="Volume",
                         marker_color=colors, opacity=0.7, showlegend=False), row=2, col=1)

    # ── RSI ───────────────────────────────────────────────────────────────────
    fig.add_trace(go.Scatter(x=x, y=rsi.values, line=dict(color="#CE93D8", width=1.5),
                             name="RSI", showlegend=False), row=3, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="rgba(244,67,54,0.6)",  row=3, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="rgba(76,175,80,0.6)",  row=3, col=1)
    fig.add_hline(y=50, line_dash="dot", line_color="rgba(158,158,158,0.3)", row=3, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        margin=dict(l=0, r=0, t=30, b=0),
        height=650,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=11)),
        xaxis_rangeslider_visible=False,
        title=dict(text=f"{symbol} — {label} Chart", font=dict(size=14, color="#8892a4")),
        dragmode="pan",
    )

    n_bars = len(x)
    init_view = min(init_bars, n_bars)
    fig.update_xaxes(
        type="category",
        tickmode="array", tickvals=tickvals, ticktext=ticktext,
        tickangle=-45,
        range=[n_bars - init_view - 0.5, n_bars - 0.5],
        gridcolor="#1c2333", showgrid=True, fixedrange=False,
    )
    fig.update_yaxes(gridcolor="#1c2333", showgrid=True, fixedrange=False)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# MARKET REGIME BANNER
# ─────────────────────────────────────────────────────────────────────────────

def render_market_regime_banner(regime):
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        badge = color_badge(regime.regime, regime_color(regime.regime))
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Market Regime</div>
          <div style="margin-top:4px">{badge}</div>
          <div class="metric-sub">{regime.action_stance[:40]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        nc = "green" if "Uptrend" in regime.nifty_trend else "red" if "Downtrend" in regime.nifty_trend else "gray"
        nifty_price = regime.details.get("nifty_price", 0)
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Nifty 50</div>
          <div class="metric-value" style="font-size:1.1em">{nifty_price:,.0f}</div>
          <div class="metric-sub">{color_badge(regime.nifty_trend, nc)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        vc = "green" if regime.vix_value < 15 else "orange" if regime.vix_value < 22 else "red"
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">India VIX</div>
          <div class="metric-value" style="color:{'#f44336' if regime.vix_value>22 else '#4caf50'}">{regime.vix_value:.1f}</div>
          <div class="metric-sub">{color_badge(regime.vix_level[:20], vc)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">USD/INR Signal</div>
          <div class="metric-value" style="font-size:0.85em">{regime.usdinr_trend[:30]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Crude Oil</div>
          <div class="metric-value" style="font-size:0.85em">{regime.crude_trend[:30]}</div>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">US 10Y Yield</div>
          <div class="metric-value" style="font-size:0.85em">{regime.us_yield_trend[:30]}</div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# STOCK ANALYSIS PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render_stock_header(sa):
    fund = sa.fundamental
    tech = sa.technical
    ac = action_color(sa.final_action)
    ac_colors = {"green": "#4caf50", "red": "#f44336", "orange": "#ff9800",
                 "blue": "#42a5f5", "gray": "#9e9e9e", "purple": "#ab47bc"}
    pill_color = ac_colors.get(ac, "#9e9e9e")

    c1, c2, c3 = st.columns([2, 3, 2])
    with c1:
        st.markdown(f"""
        <div class="metric-card" style="border-left:4px solid {pill_color}">
          <div class="ticker-badge">{sa.symbol}</div>
          <div style="color:#8892a4;font-size:0.85em;margin-top:2px">{sa.company_name}</div>
          <div class="price-display" style="margin-top:8px">{fmt_price(sa.current_price)}</div>
          <div style="margin-top:8px">{color_badge(sa.sector, 'blue')} &nbsp; {color_badge(sa.market_cap_category, 'gray')}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="metric-card" style="text-align:center;padding:20px">
          <div style="font-size:0.82em;color:#8892a4;margin-bottom:8px">FINAL ACTION</div>
          <div class="action-pill" style="background:{pill_color}22;border:2px solid {pill_color};color:{pill_color}">{sa.final_action}</div>
          <br>
          <div style="margin-top:10px">
            {color_badge("VST: " + sa.vst_action[:28], action_color(sa.vst_action))}
            &nbsp;&nbsp;
            {color_badge("ST: " + sa.st_action[:28], action_color(sa.st_action))}
            &nbsp;&nbsp;
            {color_badge("LT: " + sa.lt_action[:28], action_color(sa.lt_action))}
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Confidence</div>
          {score_bar_html(sa.confidence_score, 100, "auto", "")}
          <div class="metric-label" style="margin-top:8px">Risk Level</div>
          <div style="margin-top:4px">{color_badge(sa.risk_level, risk_color(sa.risk_level))}</div>
          <div class="metric-label" style="margin-top:8px">Risk-to-Reward</div>
          <div style="margin-top:4px">{rr_badge(sa.risk_reward_ratio)}</div>
        </div>
        """, unsafe_allow_html=True)


def render_layer_scores(sa):
    st.markdown('<div class="section-header">Layer Scores</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    layers = [
        ("Market Regime",    sa.market_regime.regime_score,   100,  regime_color(sa.market_regime.regime)),
        ("Fundamentals",     sa.fundamental.quality_score,    100,  quality_color(sa.fundamental.quality)),
        ("Technicals",       (sa.technical.setup_score + 100) // 2, 100, "auto"),
        ("News/Sentiment",   (sa.news_sentiment.sentiment_score + 100) // 2, 100, "auto"),
        ("Institutional",    (sa.institutional.activity_score + 100) // 2,  100, "auto"),
        ("Sector/Thematic",  sa.sector_thematic.sector_score, 100,  "auto"),
    ]
    for i, (label, score, max_s, color) in enumerate(layers):
        with cols[i]:
            st.markdown(score_bar_html(score, max_s, color, label), unsafe_allow_html=True)


def render_trade_params(sa):
    st.markdown('<div class="section-header">Trade Parameters</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Buy Zone</div>
        <div class="metric-value" style="font-size:1em">{fmt_price(sa.buy_zone_low)} – {fmt_price(sa.buy_zone_high)}</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Stop Loss</div>
        <div class="metric-value" style="color:#f44336">{fmt_price(sa.stop_loss)}</div>
        <div class="metric-sub">-{sa.max_loss_pct:.1f}%</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Target 1</div>
        <div class="metric-value" style="color:#4caf50">{fmt_price(sa.target_1)}</div>
        <div class="metric-sub">+{sa.upside_pct:.1f}%</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Target 2</div>
        <div class="metric-value" style="color:#4caf50">{fmt_price(sa.target_2)}</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">6M Target</div>
        <div class="metric-value" style="color:#66bb6a">{fmt_price(sa.target_6m)}</div></div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">1Y Target</div>
        <div class="metric-value" style="color:#66bb6a">{fmt_price(sa.target_1y)}</div>
        <div class="metric-sub">Position Size: {sa.position_size_pct}% of portfolio</div></div>""", unsafe_allow_html=True)


def render_fundamental_panel(fund):
    st.markdown('<div class="section-header">Fundamental Analysis — Layer 2</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Quality Classification</div>
          <div style="margin-top:6px">{color_badge(fund.quality, quality_color(fund.quality))}</div>
          <div class="metric-sub" style="margin-top:8px">{fund.moat_assessment}</div>
          <hr style="border-color:#2d3748;margin:8px 0">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:0.82em">
            <div><span style="color:#8892a4">PE Ratio</span><br><b>{fmt_ratio(fund.pe_ratio)}</b></div>
            <div><span style="color:#8892a4">PB Ratio</span><br><b>{fmt_ratio(fund.pb_ratio)}</b></div>
            <div><span style="color:#8892a4">EV/EBITDA</span><br><b>{fmt_ratio(fund.ev_ebitda)}</b></div>
            <div><span style="color:#8892a4">Div Yield</span><br><b>{fmt_pct(fund.div_yield)}</b></div>
          </div>
          <div style="margin-top:8px;font-size:0.82em">
            <span style="color:#8892a4">Valuation: </span>
            {color_badge(fund.valuation_view, "green" if "Value" in fund.valuation_view or "Attractive" in fund.valuation_view else "red" if "Expensive" in fund.valuation_view else "gray")}
          </div>
          <div style="margin-top:6px;font-size:0.8em;color:#8892a4">Market Cap: {fmt_crore(fund.market_cap_cr)}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        rv_color = "#4caf50" if fund.revenue_growth_yoy > 0 else "#f44336"
        pf_color = "#4caf50" if fund.profit_growth_yoy  > 0 else "#f44336"
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Profitability & Growth</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px;font-size:0.84em">
            <div><span style="color:#8892a4">ROE</span><br><b style="color:#e2e8f0">{fmt_pct(fund.roe)}</b></div>
            <div><span style="color:#8892a4">ROCE</span><br><b style="color:#e2e8f0">{fmt_pct(fund.roce)}</b></div>
            <div><span style="color:#8892a4">Net Margin</span><br><b style="color:#e2e8f0">{fmt_pct(fund.net_margin)}</b></div>
            <div><span style="color:#8892a4">Op Margin</span><br><b style="color:#e2e8f0">{fmt_pct(fund.operating_margin)}</b></div>
            <div><span style="color:#8892a4">Rev Growth</span><br><b style="color:{rv_color}">{fmt_pct(fund.revenue_growth_yoy)}</b></div>
            <div><span style="color:#8892a4">PAT Growth</span><br><b style="color:{pf_color}">{fmt_pct(fund.profit_growth_yoy)}</b></div>
          </div>
          <hr style="border-color:#2d3748;margin:8px 0">
          <div style="font-size:0.82em">
            <span style="color:#8892a4">Debt/Equity: </span><b>{fmt_ratio(fund.debt_equity)}</b>
            &nbsp;&nbsp;
            <span style="color:#8892a4">Int Coverage: </span><b>{fmt_ratio(fund.interest_coverage)}</b>
          </div>
          <div style="font-size:0.82em;margin-top:4px">
            <span style="color:#8892a4">FCF Yield: </span><b>{fmt_pct(fund.fcf_yield)}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Ownership & Governance</div>
          <div style="margin-top:8px;font-size:0.84em">
            <div style="margin-bottom:8px">
              <span style="color:#8892a4">Promoter Holding</span><br>
              <b style="font-size:1.3em">{fund.promoter_holding:.1f}%</b>
            </div>
            {score_bar_html(int(fund.promoter_holding), 75, "#42a5f5", "Promoter %")}
            <div style="margin-top:8px">
              <span style="color:#8892a4">Institutional Holding</span><br>
              <b style="font-size:1.3em">{fund.institutional_holding:.1f}%</b>
            </div>
            {score_bar_html(int(fund.institutional_holding), 60, "#ab47bc", "Institutional %")}
          </div>
          <div style="margin-top:8px;font-size:0.8em;color:#8892a4">
            Sector: {fund.sector} | {fund.industry[:30]}
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Warnings
    if fund.warnings:
        st.markdown('<div class="section-header" style="font-size:0.78em">Fundamental Warnings</div>', unsafe_allow_html=True)
        for w in fund.warnings:
            st.markdown(f'<div class="warning-box">⚠ {w}</div>', unsafe_allow_html=True)


def render_technical_panel(tech):
    st.markdown('<div class="section-header">Technical Analysis — Layer 3</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    with c1:
        setup_c = action_color(tech.setup)
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Setup</div>
          <div style="margin-top:6px">{color_badge(tech.setup, setup_c)}</div>
          <div class="metric-sub" style="margin-top:4px">Trend: <b>{tech.trend_direction}</b></div>
          <hr style="border-color:#2d3748;margin:8px 0">
          <div style="font-size:0.82em">
            <div><span style="color:#8892a4">Weekly: </span><b>{tech.weekly_trend}</b></div>
            <div style="margin-top:4px"><span style="color:#8892a4">Monthly: </span><b>{tech.monthly_trend}</b></div>
            <div style="margin-top:4px"><span style="color:#8892a4">vs Nifty: </span><span style="font-size:0.9em">{tech.relative_strength_vs_nifty}</span></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        p = tech.price
        ema_rows = []
        for ema_p, ema_v, name in [(20, tech.ema20, "EMA 20"), (50, tech.ema50, "EMA 50"),
                                    (100, tech.ema100, "EMA 100"), (200, tech.ema200, "EMA 200")]:
            if ema_v > 0:
                diff = (p - ema_v) / ema_v * 100
                col  = "#4caf50" if p > ema_v else "#f44336"
                ema_rows.append(f"""<div style="display:flex;justify-content:space-between;margin:3px 0">
                  <span style="color:#8892a4">{name}</span>
                  <span><b style="color:{col}">{ema_v:,.1f}</b> <span style="color:{col};font-size:0.85em">({diff:+.1f}%)</span></span>
                </div>""")
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">EMA Levels</div>
          <div style="margin-top:8px;font-size:0.83em">{''.join(ema_rows)}</div>
          <hr style="border-color:#2d3748;margin:8px 0">
          <div style="font-size:0.82em">
            <div><span style="color:#8892a4">VWAP: </span><b>{fmt_price(tech.vwap)}</b></div>
            <div style="margin-top:4px"><span style="color:#8892a4">ATR: </span><b>{fmt_price(tech.atr)} ({tech.atr_pct:.1f}%)</b></div>
            <div style="margin-top:4px"><span style="color:#8892a4">52W H/L: </span>
              <b style="color:#4caf50">{fmt_price(tech.details.get('52w_high', 0))}</b> /
              <b style="color:#f44336">{fmt_price(tech.details.get('52w_low', 0))}</b>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        rsi_c = "#f44336" if tech.rsi > 70 else "#4caf50" if tech.rsi < 35 else "#FFA726"
        macd_c = "green" if "Bullish" in tech.macd_signal else "red" if "Bearish" in tech.macd_signal else "gray"
        vol_c  = "green" if "Breakout" in tech.volume_signal else "red" if "Breakdown" in tech.volume_signal or "Selling" in tech.volume_signal else "gray"
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Momentum Indicators</div>
          <div style="margin-top:8px">
            <div style="margin-bottom:8px">
              <span style="color:#8892a4;font-size:0.82em">RSI (14)</span>
              <div style="font-size:1.8em;font-weight:700;color:{rsi_c}">{tech.rsi:.1f}</div>
            </div>
            {score_bar_html(int(tech.rsi), 100, rsi_c, "RSI")}
            <div style="margin-top:8px;font-size:0.83em">
              <span style="color:#8892a4">MACD: </span>{color_badge(tech.macd_signal, macd_c)}
            </div>
            <div style="margin-top:6px;font-size:0.83em">
              <span style="color:#8892a4">BB Position: </span><b>{tech.bb_position}</b>
            </div>
            <div style="margin-top:6px;font-size:0.83em">
              <span style="color:#8892a4">Volume: </span>{color_badge(tech.volume_signal, vol_c)}
              <span style="color:#8892a4;margin-left:6px">{tech.volume_vs_avg:.1f}x avg</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Breakout / S&R
    c4, c5 = st.columns(2)
    with c4:
        flags = []
        if tech.breakout_detected:
            flags.append('<div class="bull-box">✓ Volume Breakout Detected</div>')
        if tech.breakdown_detected:
            flags.append('<div class="red-flag-box">⚠ Volume Breakdown Detected</div>')
        if tech.is_higher_high:
            flags.append('<div class="bull-box">✓ Higher High Pattern</div>')
        if tech.is_lower_low:
            flags.append('<div class="warning-box">↓ Lower Low Pattern</div>')
        if flags:
            st.markdown('<div class="section-header" style="font-size:0.78em">Pattern Signals</div>', unsafe_allow_html=True)
            for f in flags:
                st.markdown(f, unsafe_allow_html=True)
    with c5:
        if tech.supports or tech.resistances:
            supp_str = " | ".join([fmt_price(s) for s in tech.supports[:3]])
            res_str  = " | ".join([fmt_price(r) for r in tech.resistances[:3]])
            st.markdown(f"""
            <div class="metric-card" style="font-size:0.83em">
              <div class="metric-label">Support Levels</div>
              <div style="color:#4caf50;font-weight:600">{supp_str}</div>
              <div class="metric-label" style="margin-top:8px">Resistance Levels</div>
              <div style="color:#f44336;font-weight:600">{res_str}</div>
            </div>
            """, unsafe_allow_html=True)

    if tech.warnings:
        for w in tech.warnings:
            st.markdown(f'<div class="warning-box">⚠ {w}</div>', unsafe_allow_html=True)


def render_news_institutional(news, inst):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="section-header">News & Sentiment — Layer 4</div>', unsafe_allow_html=True)
        nc = sentiment_color(news.sentiment)
        st.markdown(f"""
        <div class="metric-card">
          <div style="margin-bottom:8px">{color_badge(news.sentiment, nc)}</div>
          <div style="font-size:0.82em;color:#8892a4">Score: {news.sentiment_score:+d} | Headlines: {news.headline_count}</div>
          <div style="margin-top:6px;font-size:0.82em;color:#8892a4">
            Bullish: {news.bullish_count} &nbsp; Bearish: {news.bearish_count} &nbsp; Events: {news.event_count}
          </div>
        </div>
        """, unsafe_allow_html=True)
        if news.key_catalysts:
            st.markdown('<div style="font-size:0.78em;color:#4a9eff;margin:6px 0">Catalysts</div>', unsafe_allow_html=True)
            for cat in news.key_catalysts[:3]:
                st.markdown(f'<div class="bull-box">{cat[:100]}</div>', unsafe_allow_html=True)
        if news.key_risks:
            st.markdown('<div style="font-size:0.78em;color:#f44336;margin:6px 0">Risks</div>', unsafe_allow_html=True)
            for risk in news.key_risks[:3]:
                st.markdown(f'<div class="red-flag-box">{risk[:100]}</div>', unsafe_allow_html=True)
        if news.top_headlines:
            with st.expander("Recent Headlines"):
                for h in news.top_headlines[:6]:
                    st.markdown(f"• {h}")

    with c2:
        st.markdown('<div class="section-header">Institutional Activity — Layer 5</div>', unsafe_allow_html=True)
        ic = action_color(inst.activity)
        buy_total = inst.buy_count + inst.hold_count + inst.sell_count
        buy_pct   = inst.buy_count / buy_total * 100 if buy_total > 0 else 0
        sell_pct  = inst.sell_count / buy_total * 100 if buy_total > 0 else 0
        st.markdown(f"""
        <div class="metric-card">
          <div style="margin-bottom:6px">{color_badge(inst.activity, ic)}</div>
          <div style="margin-top:6px;font-size:0.82em;color:#8892a4">{inst.smart_money_signal}</div>
          <hr style="border-color:#2d3748;margin:8px 0">
          <div style="font-size:0.83em">
            <div><span style="color:#8892a4">Analyst Consensus: </span>
              {color_badge(inst.analyst_consensus, action_color(inst.analyst_consensus))}
            </div>
            <div style="margin-top:6px"><span style="color:#8892a4">Target Price: </span>
              <b style="color:#4caf50">{fmt_price(inst.target_price)}</b>
              {"  <b style='color:#4caf50'>+" + str(inst.upside_to_target) + "%</b>" if inst.upside_to_target > 0 else f"  <b style='color:#f44336'>{inst.upside_to_target}%</b>"}
            </div>
            <div style="margin-top:6px;display:flex;gap:12px">
              <span>🟢 Buy: <b>{inst.buy_count}</b></span>
              <span>🟡 Hold: <b>{inst.hold_count}</b></span>
              <span>🔴 Sell: <b>{inst.sell_count}</b></span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        if inst.warnings:
            for w in inst.warnings:
                st.markdown(f'<div class="warning-box">⚠ {w}</div>', unsafe_allow_html=True)


def render_sector_panel(sector):
    st.markdown('<div class="section-header">Sector & Thematic — Layer 6</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        view_c = "green" if "Overweight" in sector.sector_view or "Buy" in sector.sector_view else "orange" if "Neutral" in sector.sector_view else "red"
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Sector: {sector.sector_name}</div>
          <div style="margin-top:6px">{color_badge(sector.sector_view, view_c)}</div>
          {score_bar_html(sector.sector_score, 100, "auto", "Sector Score")}
          <div style="margin-top:6px;font-size:0.82em">
            <div>{color_badge(sector.thematic_tailwind, "green" if "Tailwind" in sector.thematic_tailwind and "Head" not in sector.thematic_tailwind else "red")}</div>
            <div style="margin-top:6px;color:#a0aec0">{sector.thematic_rationale}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        pol_badge = color_badge("Policy Supported ✓", "green") if sector.government_policy_support else color_badge("No Direct Policy", "gray")
        st.markdown(f"""
        <div class="metric-card">
          <div class="metric-label">Thematic Attributes</div>
          <div style="margin-top:8px;font-size:0.83em">
            <div style="margin-bottom:6px">{pol_badge}</div>
            <div><span style="color:#8892a4">Earnings Cycle: </span><b>{sector.earnings_cycle}</b></div>
            <div style="margin-top:4px"><span style="color:#8892a4">Sector Momentum: </span><span style="font-size:0.9em">{sector.sector_momentum}</span></div>
            <div style="margin-top:4px"><span style="color:#8892a4">Global Sensitivity: </span><b>{sector.global_demand_sensitivity}</b></div>
            <div style="margin-top:4px"><span style="color:#8892a4">Commodity Exposure: </span><b>{sector.commodity_exposure}</b></div>
          </div>
        </div>
        """, unsafe_allow_html=True)


def render_red_flags_rationale(sa):
    c1, c2 = st.columns(2)
    with c1:
        if sa.rationale:
            st.markdown('<div class="section-header" style="color:#4caf50">Bullish Rationale</div>', unsafe_allow_html=True)
            for r in sa.rationale:
                st.markdown(f'<div class="bull-box">✓ {r}</div>', unsafe_allow_html=True)
    with c2:
        if sa.red_flags:
            st.markdown('<div class="section-header" style="color:#f44336">Red Flags / Risks</div>', unsafe_allow_html=True)
            for r in sa.red_flags:
                st.markdown(f'<div class="red-flag-box">{r}</div>', unsafe_allow_html=True)


def render_decision_table(sa):
    st.markdown('<div class="section-header">Decision Summary Table</div>', unsafe_allow_html=True)
    data = {
        "Horizon": ["Very Short Term (Intraday–5D)", "Short Term (1W–3M)", "Long Term (6M–5Y+)"],
        "Action": [sa.vst_action, sa.st_action, sa.lt_action],
        "Buy Zone": [
            f"{fmt_price(sa.technical.intraday_buy_zone[0])} – {fmt_price(sa.technical.intraday_buy_zone[1])}",
            f"{fmt_price(sa.buy_zone_low)} – {fmt_price(sa.buy_zone_high)}",
            f"{fmt_price(sa.buy_zone_low)} – SIP on dips",
        ],
        "Stop Loss": [
            fmt_price(sa.technical.stop_loss_intraday),
            fmt_price(sa.stop_loss),
            f"Below {fmt_price(sa.technical.ema200)} (EMA200)",
        ],
        "Target": [
            fmt_price(sa.target_1),
            fmt_price(sa.target_2),
            f"{fmt_price(sa.target_6m)} / {fmt_price(sa.target_1y)} / {fmt_price(sa.target_3y)}",
        ],
        "R:R": [
            f"{_calc_rr(sa.current_price, sa.technical.stop_loss_intraday, sa.target_1):.1f}x",
            f"{sa.risk_reward_ratio:.1f}x",
            f"{_calc_rr(sa.current_price, sa.stop_loss, sa.target_1y):.1f}x",
        ],
        "Confidence": [
            f"{int(sa.confidence_score * 0.8)}/100",
            f"{sa.confidence_score}/100",
            f"{int(sa.confidence_score * 1.1)}/100",
        ],
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _calc_rr(price, stop, target):
    risk = abs(price - stop) if stop > 0 else price * 0.02
    reward = abs(target - price) if target > 0 else price * 0.05
    return reward / risk if risk > 0 else 0


# ─────────────────────────────────────────────────────────────────────────────
# SCREENER PAGE (multi-stock, paginated)
# ─────────────────────────────────────────────────────────────────────────────

BATCH_SIZE = 15


def _run_batch(symbols: list[str], prog_placeholder, status_placeholder) -> list:
    results = []
    for i, sym in enumerate(symbols):
        status_placeholder.text(f"Analyzing {sym}... ({i+1}/{len(symbols)})")
        try:
            results.append(run_full_analysis(sym))
        except Exception:
            pass
        prog_placeholder.progress((i + 1) / len(symbols))
    return results


def _render_results_table(results: list):
    rows = []
    for r in sorted(results, key=lambda x: x.confidence_score, reverse=True):
        rows.append({
            "Rank":       "",
            "Stock":      r.symbol,
            "Price":      fmt_price(r.current_price),
            "Cap":        r.market_cap_category,
            "Sector":     r.sector,
            "Quality":    r.fundamental.quality[:22],
            "Technical":  r.technical.setup[:22],
            "VST":        r.vst_action[:28],
            "ST":         r.st_action[:28],
            "LT":         r.lt_action[:28],
            "Action":     r.final_action,
            "Confidence": r.confidence_score,
            "Risk":       r.risk_level,
            "R:R":        f"{r.risk_reward_ratio:.1f}x",
            "Stop":       fmt_price(r.stop_loss),
            "T1":         fmt_price(r.target_1),
            "T2":         fmt_price(r.target_2),
        })
    df = pd.DataFrame(rows)
    df.index = range(1, len(df) + 1)
    df["Rank"] = df.index
    st.dataframe(df, use_container_width=True, hide_index=True)
    return df


def _render_confidence_chart(results: list, title: str = ""):
    sorted_r = sorted(results, key=lambda x: x.confidence_score, reverse=True)
    syms   = [r.symbol for r in sorted_r]
    scores = [r.confidence_score for r in sorted_r]
    fig = px.bar(
        x=syms, y=scores,
        color=scores,
        color_continuous_scale=[(0, "#f44336"), (0.45, "#FFA726"), (1, "#4caf50")],
        template="plotly_dark",
        labels={"x": "Stock", "y": "Confidence", "color": "Score"},
        title=title or f"Confidence Score — {len(results)} stocks analyzed",
        height=320,
    )
    fig.update_layout(paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                      coloraxis_showscale=False, margin=dict(t=40, b=0))
    st.plotly_chart(fig, use_container_width=True)


def _render_category_buckets(results: list):
    cats = {
        "Strong Add / Accumulate": [],
        "Add Slowly / Hold":       [],
        "Hold / Reduce":           [],
        "Exit / Avoid":            [],
    }
    for r in sorted(results, key=lambda x: x.confidence_score, reverse=True):
        a = r.final_action
        if "Strong Add" in a or "Strong Accumulate" in a:
            cats["Strong Add / Accumulate"].append(r.symbol)
        elif "Add" in a or "Accumulate" in a:
            cats["Add Slowly / Hold"].append(r.symbol)
        elif "Hold" in a or "Reduce" in a:
            cats["Hold / Reduce"].append(r.symbol)
        else:
            cats["Exit / Avoid"].append(r.symbol)

    clr_map    = {"Strong Add / Accumulate": "#001a0d", "Add Slowly / Hold": "#001220",
                  "Hold / Reduce": "#1a1200", "Exit / Avoid": "#1a0000"}
    border_map = {"Strong Add / Accumulate": "#4caf50", "Add Slowly / Hold": "#42a5f5",
                  "Hold / Reduce": "#ff9800", "Exit / Avoid": "#f44336"}
    for col, (cat, syms) in zip(st.columns(4), cats.items()):
        with col:
            syms_html = "".join([f"<div style='padding:2px 0'>{s}</div>" for s in syms]) or "<div style='color:#555'>—</div>"
            st.markdown(f"""
            <div style="background:{clr_map[cat]};border:1px solid {border_map[cat]};
                        border-radius:8px;padding:12px;min-height:80px">
              <div style="font-size:0.75em;color:{border_map[cat]};font-weight:700;margin-bottom:6px">{cat} ({len(syms)})</div>
              <div style="font-size:0.84em">{syms_html}</div>
            </div>
            """, unsafe_allow_html=True)


def render_screener_page():
    st.subheader("Multi-Stock Screener")

    # ── Session state init ─────────────────────────────────────────────────────
    if "sc_all_symbols"  not in st.session_state: st.session_state.sc_all_symbols  = []
    if "sc_offset"       not in st.session_state: st.session_state.sc_offset       = 0
    if "sc_results"      not in st.session_state: st.session_state.sc_results      = []
    if "sc_preset_label" not in st.session_state: st.session_state.sc_preset_label = ""

    # ── Preset selector ────────────────────────────────────────────────────────
    preset_options = (
        ["── By Index / Market Cap ──"]
        + ["Nifty 50", "Nifty Next 50 (Large Cap)", "All Large Cap (Nifty 100)",
           "Nifty Midcap 100", "Nifty Smallcap 100"]
        + ["── By Sector ──"]
        + [f"Sector — {k}" for k in SECTOR_MAP.keys()]
        + ["── Custom ──", "Enter Custom Stocks"]
    )

    col_sel, col_custom = st.columns([1, 2])
    with col_sel:
        preset = st.selectbox("Quick Preset", preset_options, key="sc_preset")

    # When the preset changes, push the new stock list into the text-input's session state
    # before the widget renders — this is the only reliable way to update a keyed text_input.
    last_preset = st.session_state.get("sc_last_preset", "")
    if preset != last_preset:
        st.session_state["sc_last_preset"] = preset
        if not preset.startswith("──") and preset != "Enter Custom Stocks":
            st.session_state["sc_custom_input"] = ", ".join(SCREENER_PRESETS.get(preset, []))
        else:
            st.session_state["sc_custom_input"] = ""

    with col_custom:
        custom_input = st.text_input(
            "Stocks (comma-separated, full list — screened in batches of 15)",
            placeholder="e.g. RELIANCE, HDFCBANK, TCS, INFY ...",
            key="sc_custom_input",
        )

    # Info strip
    if not preset.startswith("──") and preset != "Enter Custom Stocks":
        total = len(SCREENER_PRESETS.get(preset, []))
        st.caption(f"{preset}: {total} stocks · screened {BATCH_SIZE} at a time · results accumulate and rank automatically")

    # ── Action buttons ─────────────────────────────────────────────────────────
    analyzed  = len(st.session_state.sc_results)
    remaining = max(0, len(st.session_state.sc_all_symbols) - st.session_state.sc_offset)

    c_run, c_next, c_clear = st.columns([2, 2, 1])

    with c_run:
        start_clicked = st.button("▶  Start Screening (First 15)", type="primary",
                                  use_container_width=True, key="sc_start_btn")
    with c_next:
        next_clicked = st.button("⏭  Next 15", use_container_width=True,
                                 key="sc_next_btn",
                                 disabled=(remaining == 0 or not st.session_state.sc_all_symbols))
        if remaining > 0:
            st.caption(f"{remaining} stocks remaining")
    with c_clear:
        if st.button("✕ Reset", use_container_width=True, key="sc_reset_btn"):
            st.session_state.sc_all_symbols  = []
            st.session_state.sc_offset       = 0
            st.session_state.sc_results      = []
            st.session_state.sc_preset_label = ""
            st.rerun()

    # ── Start: reset state and run first batch ─────────────────────────────────
    if start_clicked:
        if preset.startswith("──"):
            st.warning("Select a valid preset or enter custom stocks")
            return
        symbols = [s.strip() for s in custom_input.split(",") if s.strip()]
        if not symbols:
            st.warning("Enter at least one stock symbol")
            return
        st.session_state.sc_all_symbols  = symbols
        st.session_state.sc_offset       = 0
        st.session_state.sc_results      = []
        st.session_state.sc_preset_label = preset

    # ── Execute pending batch ──────────────────────────────────────────────────
    trigger = start_clicked or next_clicked
    all_sym = st.session_state.sc_all_symbols

    if trigger and all_sym:
        offset  = st.session_state.sc_offset
        batch   = all_sym[offset : offset + BATCH_SIZE]

        if not batch:
            st.info("All stocks in this list have been analyzed.")
        else:
            prog    = st.progress(0)
            status  = st.empty()
            new_res = _run_batch(batch, prog, status)
            status.empty()
            prog.empty()

            # Merge — avoid duplicate symbols
            existing_syms = {r.symbol for r in st.session_state.sc_results}
            for r in new_res:
                if r.symbol not in existing_syms:
                    st.session_state.sc_results.append(r)
                    existing_syms.add(r.symbol)

            st.session_state.sc_offset = offset + BATCH_SIZE
            st.rerun()  # re-render so button states reflect updated offset/results

    # ── Results display ────────────────────────────────────────────────────────
    results = st.session_state.sc_results
    if not results:
        st.info("Select a preset and click **Start Screening** to begin.")
        return

    total_sym = len(all_sym) if all_sym else len(results)
    done_sym  = len(results)
    remaining = max(0, total_sym - st.session_state.sc_offset)

    # Progress bar across the full list
    progress_pct = min(1.0, done_sym / total_sym) if total_sym else 1.0
    st.markdown(f"""
    <div style="margin:8px 0 4px 0">
      <div style="display:flex;justify-content:space-between;font-size:0.8em;color:#8892a4;margin-bottom:4px">
        <span>Screened <b style="color:#e2e8f0">{done_sym}</b> of <b style="color:#e2e8f0">{total_sym}</b> stocks</span>
        <span>{remaining} remaining · results sorted best → worst</span>
      </div>
      <div style="background:#1c2333;border-radius:4px;height:8px">
        <div style="background:#4a9eff;width:{progress_pct*100:.1f}%;height:8px;border-radius:4px"></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # View toggle
    view_opts = ["All Analyzed", "Best 15 Only"]
    view = st.radio("Show", view_opts, horizontal=True, key="sc_view")
    display_results = (
        sorted(results, key=lambda x: x.confidence_score, reverse=True)[:15]
        if view == "Best 15 Only"
        else sorted(results, key=lambda x: x.confidence_score, reverse=True)
    )

    st.divider()

    # Table
    _render_results_table(display_results)

    # Chart
    _render_confidence_chart(display_results,
        title=f"{'Best 15' if view == 'Best 15 Only' else 'All ' + str(len(display_results))} — Confidence Score (Best → Worst)")

    # Category buckets
    st.markdown("---")
    _render_category_buckets(display_results)

    # Next-batch prompt if more remain
    if remaining > 0:
        st.markdown(f"""
        <div style="margin-top:16px;padding:12px 16px;background:#0d2040;border:1px solid #1a4a8a;
                    border-radius:8px;font-size:0.85em;color:#8892a4">
          ⏭ &nbsp;<b style="color:#4a9eff">{remaining} stocks</b> not yet analyzed.
          Click <b>Next 15</b> above to continue — results will merge and re-rank automatically.
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 📈 NSE Pro Screener")
        st.caption("8-Layer Institutional-Grade Analysis")
        st.divider()

        page = st.radio("Navigation", ["Stock Analysis", "Multi-Stock Screener", "Market Regime"])
        st.divider()

        if page == "Stock Analysis":
            st.markdown("**Search Stock**")
            st.caption("Type symbol or company name to filter")

            search_options, _ = _load_search_options()
            default_idx = next(
                (i for i, o in enumerate(search_options) if o.startswith("RELIANCE ")), 0
            )
            selected_option = st.selectbox(
                "",
                options=search_options,
                index=default_idx,
                key="stock_search",
                label_visibility="collapsed",
            )
            symbol_input = symbol_from_option(selected_option)

            # ── Live search for SME/Emerge and any unlisted stocks ────────────
            with st.expander("🔍 Search SME/Emerge or unlisted stocks"):
                st.caption("Covers all NSE Emerge/SME stocks not in the main list above")
                live_query = st.text_input(
                    "Type company name or symbol",
                    value="",
                    placeholder="e.g. Freshara, ZOMATO…",
                    key="live_search_input",
                )
                if live_query and len(live_query.strip()) >= 2:
                    with st.spinner("Searching NSE…"):
                        live_results = _nse_live_search(live_query.strip())
                    if live_results:
                        live_pick = st.selectbox(
                            "Select from results",
                            options=live_results,
                            key="live_search_pick",
                        )
                        # Selecting from live results overrides main selectbox
                        symbol_input = symbol_from_option(live_pick)
                    else:
                        st.caption("No NSE matches — trying symbol directly.")
                        symbol_input = live_query.strip().upper()

            if st.button("🔄 Clear Cache & Refresh", use_container_width=True,
                         help="Force fresh data — clears all cached analysis"):
                st.cache_data.clear()
                st.rerun()

            st.markdown("**Quick Pick**")
            cols = st.columns(2)
            popular_click = None
            for i, sym in enumerate(POPULAR_STOCKS[:16]):
                with cols[i % 2]:
                    if st.button(sym, key=f"pop_{sym}", use_container_width=True):
                        popular_click = sym
            if popular_click:
                symbol_input = popular_click

            st.divider()
            st.markdown("""
            <div style="font-size:0.75em;color:#8892a4;line-height:1.6">
            <b>Disclaimer:</b> This tool is for educational and informational purposes only.
            It is NOT investment advice. All investments are subject to market risk.
            Please consult a SEBI-registered advisor before investing.
            </div>
            """, unsafe_allow_html=True)

    # ── Market regime banner (always visible) ──────────────────────────────────
    with st.spinner("Loading market data..."):
        regime = get_market_regime()

    render_market_regime_banner(regime)

    if regime.warnings:
        with st.expander("Market Warnings", expanded=False):
            for w in regime.warnings:
                st.markdown(f'<div class="warning-box">⚠ {w}</div>', unsafe_allow_html=True)

    st.divider()

    # ── Pages ──────────────────────────────────────────────────────────────────
    if page == "Market Regime":
        st.subheader("Market Regime — Detailed View")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">Regime Classification</div>
              <div style="font-size:1.6em;font-weight:700;margin-top:6px">{regime.regime}</div>
              <div style="margin-top:8px;color:#a0aec0">{regime.action_stance}</div>
              <hr style="border-color:#2d3748;margin:10px 0">
              {score_bar_html(regime.regime_score, 100, "auto", "Composite Score")}
            </div>
            """, unsafe_allow_html=True)
        with c2:
            macro_data = regime.details.get("macro_signals", {})
            macro_html = "".join([f"<div style='margin:4px 0;font-size:0.83em'><span style='color:#8892a4'>{k}: </span>{v}</div>"
                                   for k, v in macro_data.items()])
            st.markdown(f"""
            <div class="metric-card">
              <div class="metric-label">Macro Signals</div>
              <div style="margin-top:8px">{macro_html}</div>
            </div>
            """, unsafe_allow_html=True)

        if regime.warnings:
            st.markdown('<div class="section-header">Active Warnings</div>', unsafe_allow_html=True)
            for w in regime.warnings:
                st.markdown(f'<div class="warning-box">⚠ {w}</div>', unsafe_allow_html=True)
        return

    if page == "Multi-Stock Screener":
        render_screener_page()
        return

    # ── Stock Analysis page ────────────────────────────────────────────────────
    if "symbol_input" not in dir():
        symbol_input = "RELIANCE"

    with st.spinner(f"Running 8-layer analysis on {symbol_input}..."):
        try:
            sa = run_full_analysis(symbol_input)
        except Exception as e:
            st.error(f"Analysis failed for {symbol_input}: {str(e)}")
            st.info("Try a different symbol or check your internet connection.")
            return

    if sa.current_price == 0:
        st.error(f"Could not fetch data for '{symbol_input}'. Verify the NSE symbol.")
        return

    # ── Stock header + confidence ─────────────────────────────────────────────
    render_stock_header(sa)
    st.markdown("")

    # ── Layer scores bar ──────────────────────────────────────────────────────
    render_layer_scores(sa)
    st.divider()

    # ── Chart ──────────────────────────────────────────────────────────────────
    _TF = {
        "5m":  ("5d",  "5m",  "5-Min",   [9, 21],       500,  75),
        "15m": ("5d",  "15m", "15-Min",  [9, 21],       200,  30),
        "1H":  ("60d", "1h",  "Hourly",  [9, 21, 50],   480,  48),
        "1D":  ("5y",  "1d",  "Daily",   [20, 50, 200], 1260, 120),
        "1W":  ("max", "1wk", "Weekly",  [10, 20, 50],  520,  78),
        "1M":  ("max", "1mo", "Monthly", [6, 12, 24],   240,  36),
    }
    tf = st.radio("", list(_TF.keys()), index=3, horizontal=True,
                  key="chart_tf", label_visibility="collapsed")
    period, interval, tf_label, ema_periods, max_bars, init_bars = _TF[tf]

    with st.spinner(f"Loading {tf_label.lower()} chart..."):
        from utils.data_fetcher import fetch_price_history
        chart_df = fetch_price_history(symbol_input, period=period, interval=interval)
        if not chart_df.empty:
            fig = draw_chart(chart_df, sa.symbol, tf_label, ema_periods, max_bars, interval, init_bars)
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    # ── Trade parameters ──────────────────────────────────────────────────────
    render_trade_params(sa)
    st.divider()

    # ── Tabs for layers ───────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Fundamentals", "📈 Technicals",
        "📰 News & Institutional", "🎯 Decision Table"
    ])

    with tab1:
        render_fundamental_panel(sa.fundamental)

    with tab2:
        render_technical_panel(sa.technical)

    with tab3:
        render_news_institutional(sa.news_sentiment, sa.institutional)
        st.divider()
        render_sector_panel(sa.sector_thematic)

    with tab4:
        render_red_flags_rationale(sa)
        st.divider()
        render_decision_table(sa)
        st.markdown(f"""
        <div style="margin-top:12px;padding:10px;background:#1c2333;border-radius:8px;font-size:0.8em;color:#8892a4">
        <b>Analysis Timestamp:</b> {datetime.now().strftime("%d %b %Y, %H:%M IST")} &nbsp;|&nbsp;
        <b>Data Source:</b> NSE via Yahoo Finance &nbsp;|&nbsp;
        <b>Model:</b> 8-Layer Institutional Screener v1.0<br>
        <b>⚠ DISCLAIMER:</b> This is for educational purposes only. NOT investment advice.
        Past performance is not indicative of future results. Invest at your own risk.
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
