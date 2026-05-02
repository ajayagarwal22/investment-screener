"""
Layer 7 + 8 — Tenure-wise Decision Engine + Risk Management
Aggregates all layer scores into probability-adjusted risk-to-reward
decisions for Very Short Term, Short Term, and Long Term.
"""

import numpy as np
from dataclasses import dataclass, field
from engines.market_regime   import MarketRegimeResult
from engines.fundamental     import FundamentalResult
from engines.technical       import TechnicalResult
from engines.news_sentiment  import NewsSentimentResult
from engines.institutional   import InstitutionalResult
from engines.sector_thematic import SectorThematicResult


# ── Data container for one full stock analysis ───────────────────────────────

@dataclass
class StockAnalysis:
    symbol: str = ""
    company_name: str = ""
    current_price: float = 0.0
    sector: str = ""
    market_cap_category: str = ""

    # Layer results
    market_regime:  MarketRegimeResult  = None
    fundamental:    FundamentalResult   = None
    technical:      TechnicalResult     = None
    news_sentiment: NewsSentimentResult = None
    institutional:  InstitutionalResult = None
    sector_thematic: SectorThematicResult = None

    # Final decisions
    vst_action: str = ""       # Very Short Term
    st_action:  str = ""       # Short Term
    lt_action:  str = ""       # Long Term
    final_action: str = ""     # Master action
    confidence_score: int = 0  # 0–100
    risk_level: str = ""
    risk_reward_ratio: float = 0.0

    # Trade parameters
    buy_zone_low:  float = 0.0
    buy_zone_high: float = 0.0
    stop_loss:     float = 0.0
    target_1:      float = 0.0
    target_2:      float = 0.0
    target_3:      float = 0.0
    target_6m:     float = 0.0
    target_1y:     float = 0.0
    target_3y:     float = 0.0

    # Risk metrics
    position_size_pct: float = 0.0
    max_loss_pct: float = 0.0
    upside_pct: float = 0.0
    downside_pct: float = 0.0

    rationale: list = field(default_factory=list)
    red_flags: list = field(default_factory=list)
    action_summary: str = ""


# ── Scoring weights by holding period ────────────────────────────────────────

VST_WEIGHTS = {
    "technical":   0.50,
    "news":        0.20,
    "institutional": 0.10,
    "market_regime": 0.15,
    "sector":      0.05,
}

ST_WEIGHTS = {
    "technical":     0.30,
    "fundamental":   0.20,
    "news":          0.15,
    "institutional": 0.20,
    "market_regime": 0.10,
    "sector":        0.05,
}

LT_WEIGHTS = {
    "fundamental":   0.40,
    "sector":        0.20,
    "institutional": 0.20,
    "technical":     0.10,
    "market_regime": 0.05,
    "news":          0.05,
}


def _normalize_score(raw: int | float, min_val=-100, max_val=100) -> float:
    """Map raw score to 0–100 range."""
    return max(0.0, min(100.0, (raw - min_val) / (max_val - min_val) * 100))


def _weighted_score(weights: dict, scores: dict) -> float:
    total_w = 0.0
    total   = 0.0
    for key, weight in weights.items():
        if key in scores:
            total   += scores[key] * weight
            total_w += weight
    return total / total_w if total_w > 0 else 50.0


def _score_to_action(score: float, horizon: str,
                     market_regime: str, tech: TechnicalResult = None) -> str:
    """Convert a 0–100 score to an action recommendation."""
    # Hard overrides
    if "Risk-Off" in market_regime or "Strong Bearish" in market_regime:
        if score < 65:
            return "Avoid Fresh Entry" if horizon != "Long Term" else "Accumulate Slowly on Dips"

    if tech and tech.breakdown_detected:
        return "Avoid — Breakdown in Progress"

    if horizon == "Very Short Term":
        if score >= 72:
            return "Intraday / Short Trade — Buy on Dips"
        elif score >= 60:
            return "Cautious Buy — Tight Stop Loss"
        elif score >= 45:
            return "Neutral — Wait for Setup"
        elif score >= 30:
            return "Avoid — Bearish Setup"
        else:
            return "Short Sell Setup (For Experienced Traders)"

    elif horizon == "Short Term":
        if score >= 72:
            return "Strong Add"
        elif score >= 60:
            return "Add Slowly"
        elif score >= 48:
            return "Hold — Do Not Add"
        elif score >= 35:
            return "Reduce on Bounce"
        else:
            return "Exit / Avoid"

    else:  # Long Term
        if score >= 75:
            return "Strong Accumulate — High Conviction"
        elif score >= 62:
            return "Accumulate on Dips"
        elif score >= 50:
            return "Hold"
        elif score >= 35:
            return "Hold but Do Not Add"
        elif score >= 20:
            return "Reduce Gradually"
        else:
            return "Exit"


def _risk_level(tech: TechnicalResult, fund: FundamentalResult,
                vix_val: float, market_regime: str) -> tuple[str, str]:
    """Returns (risk_label, explanation)."""
    risk_score = 0

    if vix_val > 25:
        risk_score += 30
    elif vix_val > 18:
        risk_score += 15

    if tech and tech.atr_pct > 4:
        risk_score += 20
    elif tech and tech.atr_pct > 2.5:
        risk_score += 10

    if fund and fund.debt_equity > 1.5:
        risk_score += 20
    elif fund and fund.debt_equity > 0.8:
        risk_score += 10

    if tech and tech.breakdown_detected:
        risk_score += 25

    if "Strong Bearish" in market_regime or "Risk-Off" in market_regime:
        risk_score += 20

    if fund and "Speculative" in fund.quality:
        risk_score += 20
    if fund and "Weak Fundamentals" in fund.quality:
        risk_score += 30

    if risk_score >= 60:
        return "Very High", "High volatility + weak fundamentals + adverse market — capital at risk"
    elif risk_score >= 40:
        return "High", "Multiple risk factors present — use strict stop loss"
    elif risk_score >= 20:
        return "Moderate", "Some risk factors — manageable with discipline"
    else:
        return "Low-Moderate", "No major risk flags — suitable for core portfolio"


def _position_size(risk_level: str, confidence: int) -> float:
    """Return suggested position size as % of portfolio."""
    base = {
        "Very High":   1.0,
        "High":        2.0,
        "Moderate":    3.5,
        "Low-Moderate": 5.0,
    }.get(risk_level, 2.5)
    # Scale down if confidence < 60
    if confidence < 50:
        base *= 0.5
    elif confidence < 65:
        base *= 0.75
    return round(min(base, 7.0), 1)


def _compute_rr_ratio(price: float, stop: float, target: float) -> float:
    risk   = abs(price - stop)
    reward = abs(target - price)
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def build_full_analysis(
    symbol: str,
    market_regime:  MarketRegimeResult,
    fundamental:    FundamentalResult,
    technical:      TechnicalResult,
    news_sentiment: NewsSentimentResult,
    institutional:  InstitutionalResult,
    sector_thematic: SectorThematicResult,
    company_name: str = "",
) -> StockAnalysis:

    sa = StockAnalysis()
    sa.symbol       = symbol.upper().replace(".NS", "")
    sa.company_name = company_name
    sa.current_price = technical.price if technical else fundamental.details.get("price", 0)
    sa.sector        = sector_thematic.sector_name if sector_thematic else fundamental.sector
    sa.market_cap_category = fundamental.market_cap_category if fundamental else "Unknown"

    # Store layer results
    sa.market_regime  = market_regime
    sa.fundamental    = fundamental
    sa.technical      = technical
    sa.news_sentiment = news_sentiment
    sa.institutional  = institutional
    sa.sector_thematic = sector_thematic

    # ── Normalize all layer scores to 0–100 ───────────────────────────────────
    scores = {}
    scores["market_regime"]  = _normalize_score(market_regime.regime_score,   0, 100)
    scores["fundamental"]    = _normalize_score(fundamental.quality_score,     0, 100)
    scores["technical"]      = _normalize_score(technical.setup_score,       -100, 100)
    scores["news"]           = _normalize_score(news_sentiment.sentiment_score, -100, 100)
    scores["institutional"]  = _normalize_score(institutional.activity_score, -100, 100)
    scores["sector"]         = _normalize_score(sector_thematic.sector_score,   0, 100)

    # ── Tenure-specific composite scores ──────────────────────────────────────
    vst_score = _weighted_score(VST_WEIGHTS, scores)
    st_score  = _weighted_score(ST_WEIGHTS,  scores)
    lt_score  = _weighted_score(LT_WEIGHTS,  scores)

    # ── Actions per tenure ────────────────────────────────────────────────────
    sa.vst_action = _score_to_action(vst_score, "Very Short Term",
                                     market_regime.regime, technical)
    sa.st_action  = _score_to_action(st_score,  "Short Term",
                                     market_regime.regime, technical)
    sa.lt_action  = _score_to_action(lt_score,  "Long Term",
                                     market_regime.regime, technical)

    # ── Master final action (weighted avg of all three) ───────────────────────
    master_score = vst_score * 0.15 + st_score * 0.35 + lt_score * 0.50
    sa.confidence_score = int(min(max(master_score, 0), 100))

    # ── Risk level ────────────────────────────────────────────────────────────
    risk_label, risk_reason = _risk_level(
        technical, fundamental, market_regime.vix_value, market_regime.regime)
    sa.risk_level = risk_label

    # ── Trade parameters from technical engine ────────────────────────────────
    price = sa.current_price
    if technical and price > 0:
        sa.buy_zone_low  = technical.swing_buy_zone[0] if technical.swing_buy_zone else price
        sa.buy_zone_high = technical.swing_buy_zone[1] if technical.swing_buy_zone else price
        sa.stop_loss     = technical.stop_loss_swing
        sa.target_1      = technical.target_1
        sa.target_2      = technical.target_2
        sa.target_3      = technical.target_3

        atr = technical.atr or price * 0.02
        sa.target_6m = round(price * (1 + max(atr * 8  / price, 0.12)), 2)
        sa.target_1y = round(price * (1 + max(atr * 15 / price, 0.20)), 2)
        sa.target_3y = round(price * (1 + max(atr * 30 / price, 0.50)), 2)

        # Use analyst target for 1Y only if it is meaningfully above the 6M target
        if institutional and institutional.target_price > 0:
            if institutional.target_price > sa.target_6m:
                sa.target_1y = round(institutional.target_price, 2)

        # Hard ordering guard — 6M ≤ 1Y ≤ 3Y always
        sa.target_1y = max(sa.target_1y, sa.target_6m)
        sa.target_3y = max(sa.target_3y, sa.target_1y)

    # ── Risk/reward metrics ───────────────────────────────────────────────────
    if price > 0 and sa.stop_loss > 0:
        sa.max_loss_pct = round(abs(price - sa.stop_loss) / price * 100, 1)
        sa.downside_pct = sa.max_loss_pct
    if price > 0 and sa.target_1 > 0:
        sa.upside_pct = round(abs(sa.target_1 - price) / price * 100, 1)
    if sa.max_loss_pct > 0:
        sa.risk_reward_ratio = _compute_rr_ratio(price, sa.stop_loss, sa.target_1)

    sa.position_size_pct = _position_size(risk_label, sa.confidence_score)

    # ── Final action label ─────────────────────────────────────────────────────
    if master_score >= 72:
        sa.final_action = "Strong Add"
    elif master_score >= 60:
        sa.final_action = "Add Slowly"
    elif master_score >= 50:
        sa.final_action = "Hold"
    elif master_score >= 40:
        sa.final_action = "Hold — Do Not Add"
    elif master_score >= 30:
        sa.final_action = "Reduce on Bounce"
    elif master_score >= 20:
        sa.final_action = "Exit"
    else:
        sa.final_action = "Avoid / Exit"

    # ── Rationale ─────────────────────────────────────────────────────────────
    rationale = []
    red_flags = []

    if fundamental.quality in ("High Quality Compounder", "Good Quality"):
        rationale.append(f"Fundamental quality: {fundamental.quality} (Score {fundamental.quality_score}/100)")
    if fundamental.roe >= 15:
        rationale.append(f"Strong ROE of {fundamental.roe}%")
    if technical.breakout_detected:
        rationale.append("Volume breakout detected — momentum building")
    if "Bullish" in technical.setup:
        rationale.append(f"Technical setup: {technical.setup}")
    if sector_thematic.government_policy_support:
        rationale.append(f"Government policy tailwind in {sector_thematic.sector_name}")
    if institutional.upside_to_target > 15:
        rationale.append(f"Analyst target implies {institutional.upside_to_target}% upside")
    if news_sentiment.key_catalysts:
        rationale.append(f"Catalyst: {news_sentiment.key_catalysts[0][:80]}")

    # Red flags
    all_warnings = (
        technical.warnings +
        fundamental.warnings +
        institutional.warnings +
        market_regime.warnings
    )
    red_flags = list(set(all_warnings))[:6]

    if fundamental.quality in ("Weak Fundamentals — Avoid", "Speculative"):
        red_flags.append(f"⚠ Fundamental concern: {fundamental.quality}")
    if technical.breakdown_detected:
        red_flags.append("⚠ Price breakdown — potential falling knife")
    if market_regime.regime in ("Strong Bearish", "High Volatility Risk-Off"):
        red_flags.append(f"⚠ Adverse market regime: {market_regime.regime}")
    if news_sentiment.key_risks:
        red_flags.append(f"⚠ News risk: {news_sentiment.key_risks[0][:80]}")

    sa.rationale = rationale[:5]
    sa.red_flags  = red_flags[:5]

    # ── Action summary sentence ────────────────────────────────────────────────
    sa.action_summary = (
        f"{sa.symbol} | {sa.final_action} | "
        f"Confidence: {sa.confidence_score}/100 | "
        f"Risk: {sa.risk_level} | "
        f"VST: {sa.vst_action[:30]} | "
        f"ST: {sa.st_action[:30]} | "
        f"LT: {sa.lt_action[:30]}"
    )

    return sa
