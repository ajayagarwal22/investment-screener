"""
Central orchestrator — fetches all data and runs all 8 layers
for a given NSE stock symbol.
"""

import yfinance as yf
import pandas as pd
import streamlit as st

from utils.data_fetcher import (
    fetch_price_history, fetch_intraday, fetch_stock_info,
    fetch_index_data, nse_ticker,
)
from engines.market_regime   import analyze_market_regime
from engines.fundamental     import analyze_fundamentals
from engines.technical       import analyze_technicals
from engines.news_sentiment  import analyze_news_sentiment
from engines.institutional   import analyze_institutional
from engines.sector_thematic import analyze_sector_thematic
from engines.decision        import build_full_analysis, StockAnalysis


@st.cache_data(ttl=600, show_spinner=False)
def get_market_regime():
    return analyze_market_regime()


@st.cache_data(ttl=300, show_spinner=False)
def get_nifty_daily():
    return fetch_price_history("^NSEI", period="1y", interval="1d")


@st.cache_data(ttl=60, show_spinner=False)
def run_full_analysis(symbol: str) -> StockAnalysis:
    """Run all 8 analysis layers and return a complete StockAnalysis."""
    clean_sym = symbol.upper().strip().replace(".NS", "").replace(".BO", "")

    # ── Fetch price data ──────────────────────────────────────────────────────
    daily_df   = fetch_price_history(clean_sym, period="2y",   interval="1d")
    weekly_df  = fetch_price_history(clean_sym, period="5y",   interval="1wk")
    monthly_df = fetch_price_history(clean_sym, period="10y",  interval="1mo")
    nifty_df   = get_nifty_daily()

    # ── Fetch company info ────────────────────────────────────────────────────
    info = fetch_stock_info(clean_sym)
    company_name = info.get("longName") or info.get("shortName") or clean_sym

    # ── Run layers ────────────────────────────────────────────────────────────
    market_regime   = get_market_regime()
    fundamental     = analyze_fundamentals(clean_sym)
    technical       = analyze_technicals(daily_df, weekly_df, monthly_df, nifty_df)
    news_sentiment  = analyze_news_sentiment(clean_sym)
    institutional   = analyze_institutional(clean_sym)
    sector_thematic = analyze_sector_thematic(clean_sym, fundamental.sector)

    # ── Build final decision ──────────────────────────────────────────────────
    analysis = build_full_analysis(
        symbol          = clean_sym,
        company_name    = company_name,
        market_regime   = market_regime,
        fundamental     = fundamental,
        technical       = technical,
        news_sentiment  = news_sentiment,
        institutional   = institutional,
        sector_thematic = sector_thematic,
    )

    return analysis


@st.cache_data(ttl=300, show_spinner=False)
def run_batch_screen(symbols: list[str]) -> list[StockAnalysis]:
    """Screen multiple stocks and return list sorted by confidence."""
    results = []
    for sym in symbols:
        try:
            result = run_full_analysis(sym)
            results.append(result)
        except Exception as e:
            pass
    results.sort(key=lambda x: x.confidence_score, reverse=True)
    return results
