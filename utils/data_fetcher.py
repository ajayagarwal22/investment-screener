"""Data fetching layer — wraps yfinance with caching and NSE helpers."""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
import feedparser
from datetime import datetime, timedelta
from functools import lru_cache
import warnings
warnings.filterwarnings("ignore")

from utils.config import NSE_SUFFIX, BSE_SUFFIX, NIFTY50, BANKNIFTY, INDIA_VIX, USDINR, CRUDE_OIL, US10Y


def nse_ticker(symbol: str) -> str:
    symbol = symbol.upper().strip()
    if symbol.endswith(NSE_SUFFIX) or symbol.endswith(BSE_SUFFIX):
        return symbol
    return symbol + NSE_SUFFIX


def fetch_price_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    ticker = nse_ticker(symbol)
    try:
        df = yf.download(ticker, period=period, interval=interval,
                         auto_adjust=True, progress=False)
        if df.empty:
            df = yf.download(symbol + BSE_SUFFIX, period=period, interval=interval,
                             auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.dropna(inplace=True)
        return df
    except Exception:
        return pd.DataFrame()


def fetch_intraday(symbol: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    return fetch_price_history(symbol, period=period, interval=interval)


def fetch_stock_info(symbol: str) -> dict:
    ticker = nse_ticker(symbol)
    try:
        info = yf.Ticker(ticker).info
        return info if info else {}
    except Exception:
        return {}


def fetch_financials(symbol: str) -> dict:
    ticker_obj = yf.Ticker(nse_ticker(symbol))
    result = {}
    try:
        result["income_stmt"] = ticker_obj.financials
        result["balance_sheet"] = ticker_obj.balance_sheet
        result["cashflow"] = ticker_obj.cashflow
        result["quarterly_income"] = ticker_obj.quarterly_financials
        result["quarterly_cashflow"] = ticker_obj.quarterly_cashflow
    except Exception:
        pass
    return result


def fetch_news(symbol: str) -> list[dict]:
    ticker_obj = yf.Ticker(nse_ticker(symbol))
    try:
        news = ticker_obj.news or []
        return news[:10]
    except Exception:
        return []


def fetch_index_data(period: str = "6mo") -> dict:
    indices = {
        "nifty50": NIFTY50,
        "banknifty": BANKNIFTY,
        "india_vix": INDIA_VIX,
        "usdinr": USDINR,
        "crude": CRUDE_OIL,
        "us10y": US10Y,
    }
    result = {}
    for name, ticker in indices.items():
        try:
            df = yf.download(ticker, period=period, interval="1d",
                             auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            if not df.empty:
                result[name] = df
        except Exception:
            pass
    return result


def fetch_multiple_stocks(symbols: list[str], period: str = "1y") -> dict:
    data = {}
    for sym in symbols:
        df = fetch_price_history(sym, period=period)
        if not df.empty:
            data[sym] = df
    return data


def safe_float(val, default=np.nan) -> float:
    try:
        v = float(val)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def pct_change_safe(series: pd.Series, periods: int = 1) -> pd.Series:
    return series.pct_change(periods=periods).replace([np.inf, -np.inf], np.nan)
