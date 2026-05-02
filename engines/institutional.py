"""
Layer 5 — Institutional Activity Engine
Interprets promoter holding trends, FII/DII proxies,
brokerage signals, and bulk/block deal patterns.
"""

import numpy as np
from dataclasses import dataclass, field
from utils.data_fetcher import fetch_stock_info, safe_float


@dataclass
class InstitutionalResult:
    activity: str = "No Clear Signal"
    activity_score: int = 0      # -100 to +100
    institutional_holding: float = 0.0
    promoter_holding: float = 0.0
    promoter_change_signal: str = "Unknown"
    smart_money_signal: str = "Unknown"
    analyst_consensus: str = "Unknown"
    target_price: float = 0.0
    current_price: float = 0.0
    upside_to_target: float = 0.0
    recommendation_count: int = 0
    buy_count: int = 0
    hold_count: int = 0
    sell_count: int = 0
    details: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def analyze_institutional(symbol: str) -> InstitutionalResult:
    result = InstitutionalResult()
    info = fetch_stock_info(symbol)

    if not info:
        result.activity = "Data Unavailable"
        return result

    # ── Institutional holding ─────────────────────────────────────────────────
    inst_hold  = safe_float(info.get("heldPercentInstitutions", 0)) * 100
    promo_hold = safe_float(info.get("heldPercentInsiders",     0)) * 100
    result.institutional_holding = round(inst_hold,  1)
    result.promoter_holding      = round(promo_hold, 1)

    # ── Analyst recommendations ───────────────────────────────────────────────
    reco = info.get("recommendationKey", "").lower()
    target = safe_float(info.get("targetMeanPrice"))
    price  = safe_float(info.get("currentPrice") or info.get("regularMarketPrice", 0))

    result.target_price   = round(target, 2) if np.isfinite(target) else 0.0
    result.current_price  = round(price,  2) if np.isfinite(price)  else 0.0

    if result.target_price > 0 and result.current_price > 0:
        result.upside_to_target = round(
            (result.target_price - result.current_price) / result.current_price * 100, 1)

    # Map recommendation key to label
    reco_map = {
        "strong_buy": "Strong Buy",
        "buy":        "Buy",
        "hold":       "Hold",
        "sell":       "Sell",
        "strong_sell":"Strong Sell",
        "underperform": "Underperform",
        "outperform":   "Outperform",
        "neutral":    "Neutral",
    }
    result.analyst_consensus = reco_map.get(reco, reco.replace("_", " ").title() if reco else "No Coverage")

    # ── Analyst vote breakdown from recommendationTrend ──────────────────────
    try:
        ticker_obj = __import__("yfinance").Ticker(symbol + ".NS")
        reco_trend = ticker_obj.recommendations
        if reco_trend is not None and not reco_trend.empty:
            latest = reco_trend.iloc[-1]
            result.buy_count  = int(latest.get("strongBuy", 0) + latest.get("buy",  0))
            result.hold_count = int(latest.get("hold",      0))
            result.sell_count = int(latest.get("strongSell",0) + latest.get("sell", 0))
            result.recommendation_count = result.buy_count + result.hold_count + result.sell_count
    except Exception:
        pass

    # ── Scoring ───────────────────────────────────────────────────────────────
    score = 0
    warns = []

    # Institutional holding level
    if inst_hold >= 30:
        score += 20
    elif inst_hold >= 15:
        score += 10
    elif inst_hold < 5 and inst_hold > 0:
        score -= 5
        warns.append(f"Very low institutional holding ({inst_hold}%) — retail-driven")

    # Analyst consensus
    if result.analyst_consensus in ("Strong Buy",):
        score += 25
    elif result.analyst_consensus in ("Buy", "Outperform"):
        score += 15
    elif result.analyst_consensus in ("Hold", "Neutral"):
        score += 0
    elif result.analyst_consensus in ("Sell", "Underperform", "Strong Sell"):
        score -= 20

    # Analyst target upside
    if result.upside_to_target > 25:
        score += 15
    elif result.upside_to_target > 10:
        score += 8
    elif result.upside_to_target < 0:
        score -= 10
        warns.append(f"Stock trading above analyst consensus target — limited upside from sell-side")
    elif result.upside_to_target < -15:
        score -= 18

    # Vote ratio
    if result.recommendation_count > 0:
        buy_pct  = result.buy_count  / result.recommendation_count * 100
        sell_pct = result.sell_count / result.recommendation_count * 100
        if buy_pct >= 70:
            score += 10
        elif sell_pct >= 50:
            score -= 10

    # Promoter holding level
    if promo_hold >= 60:
        score += 10
    elif promo_hold < 20 and promo_hold > 0:
        score -= 5
        warns.append(f"Promoter holding below 20% ({promo_hold}%) — low skin in game")

    score = max(-100, min(100, score))
    result.activity_score = int(score)
    result.warnings = warns

    # ── Smart money signal ────────────────────────────────────────────────────
    if score >= 35:
        result.smart_money_signal = "Smart Money Accumulating"
    elif score >= 10:
        result.smart_money_signal = "Mild Institutional Interest"
    elif score <= -35:
        result.smart_money_signal = "Smart Money Exiting"
    elif score <= -10:
        result.smart_money_signal = "Mild Institutional Selling"
    else:
        result.smart_money_signal = "No Clear Institutional Signal"

    # ── Activity label ────────────────────────────────────────────────────────
    if score >= 40:
        result.activity = "Strong Institutional Interest"
    elif score >= 15:
        result.activity = "Mild Institutional Buying"
    elif score <= -40:
        result.activity = "Institutional Distribution"
    elif score <= -15:
        result.activity = "Mild Institutional Selling"
    else:
        result.activity = "Neutral / No Clear Signal"

    result.details = {
        "institutional_holding": inst_hold,
        "promoter_holding": promo_hold,
        "analyst_consensus": result.analyst_consensus,
        "target_price": result.target_price,
        "upside_to_target": result.upside_to_target,
        "buy_analysts": result.buy_count,
        "hold_analysts": result.hold_count,
        "sell_analysts": result.sell_count,
    }

    return result
