"""
Layer 1 — Market Regime Engine
Classifies current market state using Nifty, BankNifty, VIX,
breadth, macro proxies and outputs an actionable market stance.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from utils.data_fetcher import fetch_index_data, fetch_price_history, safe_float
from engines.technical import compute_ema, compute_rsi, compute_atr


@dataclass
class MarketRegimeResult:
    regime: str = "Unknown"
    regime_score: int = 0          # -100 (extreme bear) to +100 (extreme bull)
    nifty_trend: str = "Unknown"
    banknifty_trend: str = "Unknown"
    vix_level: str = "Unknown"
    vix_value: float = 0.0
    breadth: str = "Unknown"
    macro_outlook: str = "Unknown"
    usdinr_trend: str = "Stable"
    crude_trend: str = "Neutral"
    us_yield_trend: str = "Neutral"
    action_stance: str = "Neutral"
    details: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def _classify_trend(df: pd.DataFrame, label: str = "") -> tuple[str, float]:
    """Return (trend_label, score 0-100) for a price series."""
    if df is None or df.empty or len(df) < 50:
        return "Insufficient Data", 50

    close = df["Close"].squeeze()
    ema20  = compute_ema(close, 20).iloc[-1]
    ema50  = compute_ema(close, 50).iloc[-1]
    ema200 = compute_ema(close, 200).iloc[-1] if len(close) >= 200 else None
    price  = float(close.iloc[-1])
    rsi    = float(compute_rsi(close, 14).iloc[-1])

    score = 50
    trend_parts = []

    if price > ema20:
        score += 10
        trend_parts.append("above EMA20")
    else:
        score -= 10

    if price > ema50:
        score += 15
        trend_parts.append("above EMA50")
    else:
        score -= 15
        trend_parts.append("below EMA50")

    if ema200 is not None:
        if price > ema200:
            score += 20
            trend_parts.append("above EMA200")
        else:
            score -= 20
            trend_parts.append("below EMA200")

    # RSI contribution
    if rsi > 60:
        score += 10
    elif rsi < 40:
        score -= 10

    # 20-day momentum
    if len(close) >= 20:
        mom = (price - float(close.iloc[-20])) / float(close.iloc[-20]) * 100
        if mom > 3:
            score += 10
        elif mom < -3:
            score -= 10

    score = max(0, min(100, score))

    if score >= 75:
        trend = "Strong Uptrend"
    elif score >= 60:
        trend = "Mild Uptrend"
    elif score >= 45:
        trend = "Rangebound"
    elif score >= 30:
        trend = "Mild Downtrend"
    else:
        trend = "Strong Downtrend"

    return trend, score


def _classify_vix(vix_df: pd.DataFrame) -> tuple[str, float]:
    if vix_df is None or vix_df.empty:
        return "Unknown", 15.0
    val = float(vix_df["Close"].iloc[-1])
    if val < 12:
        label = "Extremely Low (Complacency Risk)"
    elif val < 16:
        label = "Low (Calm Market)"
    elif val < 20:
        label = "Moderate"
    elif val < 25:
        label = "Elevated (Caution)"
    elif val < 35:
        label = "High (Fear)"
    else:
        label = "Extreme Fear (Crisis)"
    return label, val


def _macro_signals(index_data: dict) -> dict:
    signals = {}

    # USD/INR
    if "usdinr" in index_data:
        usdinr = index_data["usdinr"]["Close"].squeeze()
        chg_1m = (float(usdinr.iloc[-1]) - float(usdinr.iloc[-22])) / float(usdinr.iloc[-22]) * 100 if len(usdinr) >= 22 else 0
        if chg_1m > 1.5:
            signals["usdinr"] = ("Depreciating INR (Bearish FII)", -15)
        elif chg_1m < -1.5:
            signals["usdinr"] = ("Appreciating INR (Bullish FII)", +10)
        else:
            signals["usdinr"] = ("USDINR Stable", 0)

    # Crude oil
    if "crude" in index_data:
        crude = index_data["crude"]["Close"].squeeze()
        chg_1m = (float(crude.iloc[-1]) - float(crude.iloc[-22])) / float(crude.iloc[-22]) * 100 if len(crude) >= 22 else 0
        if chg_1m > 8:
            signals["crude"] = ("Crude Spiking — Inflation Risk", -10)
        elif chg_1m > 3:
            signals["crude"] = ("Crude Rising — Watch Inflation", -5)
        elif chg_1m < -8:
            signals["crude"] = ("Crude Falling — Positive for India", +8)
        else:
            signals["crude"] = ("Crude Stable", 0)

    # US 10Y yield
    if "us10y" in index_data:
        y10 = index_data["us10y"]["Close"].squeeze()
        val = float(y10.iloc[-1])
        chg = float(y10.iloc[-1]) - float(y10.iloc[-22]) if len(y10) >= 22 else 0
        if val > 4.5 and chg > 0.2:
            signals["us10y"] = (f"US Yields High & Rising ({val:.2f}%) — FII Outflow Risk", -15)
        elif val > 4.5:
            signals["us10y"] = (f"US Yields Elevated ({val:.2f}%)", -8)
        elif chg < -0.2:
            signals["us10y"] = (f"US Yields Falling ({val:.2f}%) — EM Positive", +10)
        else:
            signals["us10y"] = (f"US Yields Stable ({val:.2f}%)", 0)

    return signals


def analyze_market_regime() -> MarketRegimeResult:
    result = MarketRegimeResult()
    index_data = fetch_index_data(period="1y")

    # ── Nifty & BankNifty trend ──────────────────────────────────────────────
    nifty_trend, nifty_score   = _classify_trend(index_data.get("nifty50"),   "Nifty50")
    bnk_trend,   bnk_score     = _classify_trend(index_data.get("banknifty"), "BankNifty")
    result.nifty_trend    = nifty_trend
    result.banknifty_trend = bnk_trend

    # ── VIX ─────────────────────────────────────────────────────────────────
    vix_label, vix_val = _classify_vix(index_data.get("india_vix"))
    result.vix_level = vix_label
    result.vix_value = vix_val

    # ── Macro signals ────────────────────────────────────────────────────────
    macro = _macro_signals(index_data)
    macro_score = sum(v[1] for v in macro.values())

    if "usdinr" in macro:
        result.usdinr_trend = macro["usdinr"][0]
    if "crude" in macro:
        result.crude_trend = macro["crude"][0]
    if "us10y" in macro:
        result.us_yield_trend = macro["us10y"][0]

    result.details["macro_signals"] = {k: v[0] for k, v in macro.items()}

    # ── Composite score ──────────────────────────────────────────────────────
    # Nifty trend (40%), BankNifty (30%), macro (30%)
    raw_score = (nifty_score * 0.40 + bnk_score * 0.30 + (50 + macro_score) * 0.30)

    # VIX penalty
    if vix_val > 25:
        raw_score -= 15
    elif vix_val > 20:
        raw_score -= 8
    elif vix_val < 13:
        raw_score -= 5   # complacency risk

    raw_score = max(0, min(100, raw_score))
    result.regime_score = int(raw_score)

    # ── Regime label ─────────────────────────────────────────────────────────
    if vix_val > 30:
        result.regime = "High Volatility Risk-Off"
        result.action_stance = "Avoid New Exposure — Preserve Capital"
    elif raw_score >= 75:
        result.regime = "Strong Bullish"
        result.action_stance = "Fresh Buying Favoured — Deploy Capital"
    elif raw_score >= 62:
        result.regime = "Mild Bullish"
        result.action_stance = "Partial Buying — Stock Specific Approach"
    elif raw_score >= 48:
        result.regime = "Rangebound"
        result.action_stance = "Hold — Buy at Dips, Book at Highs"
    elif raw_score >= 35:
        result.regime = "Weak Bearish"
        result.action_stance = "Defensive — Reduce Weak Positions"
    elif raw_score >= 20:
        result.regime = "Strong Bearish"
        result.action_stance = "Profit Booking — Avoid Fresh Longs"
    else:
        result.regime = "Strong Bearish"
        result.action_stance = "Cash is King — Exit Weak Holdings"

    # ── Warnings ─────────────────────────────────────────────────────────────
    if vix_val > 20:
        result.warnings.append(f"India VIX at {vix_val:.1f} — heightened risk, tighten stop losses")
    if "Depreciating INR" in result.usdinr_trend:
        result.warnings.append("INR weakness may trigger FII outflows")
    if "High & Rising" in result.us_yield_trend:
        result.warnings.append("Rising US yields — risk of FII selling in EMs")
    if "Spiking" in result.crude_trend:
        result.warnings.append("Crude oil spike — CAD pressure, inflation risk")
    if nifty_trend in ("Strong Downtrend", "Mild Downtrend") and bnk_trend in ("Strong Downtrend", "Mild Downtrend"):
        result.warnings.append("Both Nifty and BankNifty in downtrend — broad market weakness")

    result.details["nifty_score"]    = nifty_score
    result.details["banknifty_score"] = bnk_score
    result.details["macro_score"]    = macro_score
    result.details["composite_score"] = raw_score

    # Nifty recent price
    if "nifty50" in index_data and not index_data["nifty50"].empty:
        result.details["nifty_price"]  = float(index_data["nifty50"]["Close"].iloc[-1])
        result.details["nifty_52w_h"]  = float(index_data["nifty50"]["Close"].max())
        result.details["nifty_52w_l"]  = float(index_data["nifty50"]["Close"].min())

    return result
