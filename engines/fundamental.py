"""
Layer 2 — Fundamental Quality Engine
Evaluates revenue growth, profitability, balance sheet strength,
valuation, and corporate governance from yfinance data.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from utils.data_fetcher import fetch_stock_info, fetch_financials, safe_float


@dataclass
class FundamentalResult:
    quality: str = "Unknown"
    quality_score: int = 0          # 0–100

    # Valuation
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    ev_ebitda: float = 0.0
    price_to_sales: float = 0.0
    div_yield: float = 0.0
    market_cap_cr: float = 0.0
    market_cap_category: str = "Unknown"

    # Profitability
    roe: float = 0.0
    roce: float = 0.0
    net_margin: float = 0.0
    operating_margin: float = 0.0
    revenue_growth_yoy: float = 0.0
    profit_growth_yoy: float = 0.0

    # Balance sheet
    debt_equity: float = 0.0
    current_ratio: float = 0.0
    interest_coverage: float = 0.0

    # Cash flow
    fcf_yield: float = 0.0
    operating_cf: float = 0.0

    # Promoter & governance
    promoter_holding: float = 0.0
    promoter_pledge: float = 0.0
    institutional_holding: float = 0.0

    # Sector
    sector: str = "Unknown"
    industry: str = "Unknown"

    # Valuation verdict
    valuation_view: str = "Unknown"
    moat_assessment: str = "Unknown"

    details: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def _safe_series_growth(stmt: pd.DataFrame, row_key: str) -> float:
    """Calculate YoY growth for an income statement row."""
    try:
        if stmt is None or stmt.empty:
            return np.nan
        matching = [c for c in stmt.index if row_key.lower() in str(c).lower()]
        if not matching:
            return np.nan
        row = stmt.loc[matching[0]]
        row = row.dropna()
        if len(row) >= 2:
            new_val = float(row.iloc[0])
            old_val = float(row.iloc[1])
            if old_val != 0 and np.isfinite(new_val) and np.isfinite(old_val):
                return (new_val - old_val) / abs(old_val) * 100
    except Exception:
        pass
    return np.nan


def _classify_market_cap(cap_cr: float) -> str:
    # SEBI-aligned thresholds (INR Crore)
    if cap_cr > 20_000:
        return "Large Cap"
    elif cap_cr > 5_000:
        return "Mid Cap"
    elif cap_cr > 1_000:
        return "Small Cap"
    else:
        return "Micro Cap"


def analyze_fundamentals(symbol: str) -> FundamentalResult:
    result = FundamentalResult()
    info = fetch_stock_info(symbol)
    fin  = fetch_financials(symbol)

    if not info:
        result.quality = "Data Unavailable"
        return result

    # ── Sector/Industry ──────────────────────────────────────────────────────
    result.sector   = info.get("sector",   "Unknown") or "Unknown"
    result.industry = info.get("industry", "Unknown") or "Unknown"

    # ── Market Cap ────────────────────────────────────────────────────────────
    # yfinance returns marketCap in the ticker's native currency.
    # For .NS tickers it is already in INR; divide by 1e7 to get INR Crore.
    mc_inr = safe_float(info.get("marketCap"))
    if np.isfinite(mc_inr) and mc_inr > 0:
        result.market_cap_cr = round(mc_inr / 1e7, 0)
    result.market_cap_category = _classify_market_cap(result.market_cap_cr)

    # ── Valuation multiples ───────────────────────────────────────────────────
    result.pe_ratio       = safe_float(info.get("trailingPE"))
    result.pb_ratio       = safe_float(info.get("priceToBook"))
    result.ev_ebitda      = safe_float(info.get("enterpriseToEbitda"))
    result.price_to_sales = safe_float(info.get("priceToSalesTrailingTwelveMonths"))
    result.div_yield      = round(safe_float(info.get("dividendYield", 0)) * 100, 2)

    # ── Profitability ─────────────────────────────────────────────────────────
    result.roe             = round(safe_float(info.get("returnOnEquity",   0)) * 100, 1)
    result.roce            = round(safe_float(info.get("returnOnAssets",   0)) * 100 * 1.5, 1)  # proxy
    result.net_margin      = round(safe_float(info.get("profitMargins",    0)) * 100, 1)
    result.operating_margin= round(safe_float(info.get("operatingMargins", 0)) * 100, 1)

    # ── Revenue / profit growth from financials ───────────────────────────────
    if fin.get("income_stmt") is not None and not fin["income_stmt"].empty:
        result.revenue_growth_yoy = round(
            _safe_series_growth(fin["income_stmt"], "Total Revenue"), 1)
        result.profit_growth_yoy  = round(
            _safe_series_growth(fin["income_stmt"], "Net Income"), 1)

    # ── Balance sheet ─────────────────────────────────────────────────────────
    result.debt_equity    = round(safe_float(info.get("debtToEquity", 0)) / 100, 2)  # yf gives %, convert
    result.current_ratio  = round(safe_float(info.get("currentRatio",  0)), 2)

    # Interest coverage proxy: EBIT / Interest Expense
    if fin.get("income_stmt") is not None and not fin["income_stmt"].empty:
        try:
            stmt = fin["income_stmt"]
            ebit_rows    = [c for c in stmt.index if "ebit" in str(c).lower() and "ebitda" not in str(c).lower()]
            int_rows     = [c for c in stmt.index if "interest expense" in str(c).lower()]
            if ebit_rows and int_rows:
                ebit = float(stmt.loc[ebit_rows[0]].iloc[0])
                inte = abs(float(stmt.loc[int_rows[0]].iloc[0]))
                result.interest_coverage = round(ebit / inte, 1) if inte > 0 else 99.0
        except Exception:
            pass

    # ── Cash flow ─────────────────────────────────────────────────────────────
    result.operating_cf = safe_float(info.get("operatingCashflow", 0)) / 1e7  # → Cr
    result.fcf_yield    = round(safe_float(info.get("freeCashflow", 0)) /
                                 max(safe_float(info.get("marketCap", 1)), 1) * 100, 2)

    # ── Promoter & institutional ───────────────────────────────────────────────
    # yfinance gives heldPercentInsiders / heldPercentInstitutions
    result.promoter_holding      = round(safe_float(info.get("heldPercentInsiders",     0)) * 100, 1)
    result.institutional_holding = round(safe_float(info.get("heldPercentInstitutions", 0)) * 100, 1)

    # ── Scoring ───────────────────────────────────────────────────────────────
    score = 50
    warns = []

    # ROE
    if result.roe >= 20:
        score += 15
    elif result.roe >= 12:
        score += 8
    elif result.roe > 0:
        score += 2
    else:
        score -= 15
        warns.append(f"Negative ROE ({result.roe}%) — possible loss-making company")

    # Net margin
    if result.net_margin >= 20:
        score += 12
    elif result.net_margin >= 10:
        score += 6
    elif result.net_margin > 0:
        score += 2
    elif result.net_margin < 0:
        score -= 10
        warns.append("Negative net margins — unprofitable")

    # Revenue growth
    if np.isfinite(result.revenue_growth_yoy):
        if result.revenue_growth_yoy >= 20:
            score += 12
        elif result.revenue_growth_yoy >= 10:
            score += 6
        elif result.revenue_growth_yoy < 0:
            score -= 8
            warns.append(f"Revenue declining {result.revenue_growth_yoy:.1f}% YoY")

    # Profit growth
    if np.isfinite(result.profit_growth_yoy):
        if result.profit_growth_yoy >= 25:
            score += 10
        elif result.profit_growth_yoy >= 10:
            score += 5
        elif result.profit_growth_yoy < -20:
            score -= 12
            warns.append(f"Profit falling {result.profit_growth_yoy:.1f}% YoY")

    # Debt/equity
    if result.debt_equity <= 0.5:
        score += 10
    elif result.debt_equity <= 1.0:
        score += 4
    elif result.debt_equity > 2.0:
        score -= 12
        warns.append(f"High debt/equity ratio of {result.debt_equity:.1f}x")
    elif result.debt_equity > 1.5:
        score -= 6

    # Interest coverage
    if result.interest_coverage >= 5:
        score += 5
    elif 0 < result.interest_coverage < 2:
        score -= 10
        warns.append(f"Weak interest coverage of {result.interest_coverage}x — debt stress risk")

    # FCF yield
    if result.fcf_yield > 3:
        score += 5
    elif result.fcf_yield < 0:
        score -= 5

    # Promoter holding
    if result.promoter_holding >= 50:
        score += 5
    elif result.promoter_holding < 25 and result.promoter_holding > 0:
        score -= 3
        warns.append(f"Low promoter holding ({result.promoter_holding}%) — alignment risk")

    # PE-based valuation
    result.valuation_view = _assess_valuation(result, info)
    if result.valuation_view == "Expensive":
        score -= 5
    elif result.valuation_view in ("Fairly Valued", "Attractive"):
        score += 5
    elif result.valuation_view == "Value Pick":
        score += 10

    score = max(0, min(100, score))
    result.quality_score = int(score)
    result.warnings = warns

    # ── Quality label ─────────────────────────────────────────────────────────
    if score >= 80:
        result.quality = "High Quality Compounder"
    elif score >= 65:
        result.quality = "Good Quality"
    elif score >= 50:
        result.quality = "Cyclical Opportunity"
    elif score >= 35:
        result.quality = "Turnaround Candidate"
    elif score >= 20:
        result.quality = "Speculative"
    else:
        result.quality = "Weak Fundamentals — Avoid"

    # ── Moat assessment (proxy) ───────────────────────────────────────────────
    if result.roe >= 20 and result.net_margin >= 15 and result.debt_equity <= 0.5:
        result.moat_assessment = "Strong Moat (High ROE + Margin + Low Debt)"
    elif result.roe >= 15 and result.net_margin >= 8:
        result.moat_assessment = "Moderate Moat"
    elif result.net_margin < 5 and result.debt_equity > 1.5:
        result.moat_assessment = "No Moat — Commodity / Cyclical"
    else:
        result.moat_assessment = "Weak Moat"

    result.details = {
        "pe": result.pe_ratio,
        "pb": result.pb_ratio,
        "ev_ebitda": result.ev_ebitda,
        "roe": result.roe,
        "net_margin": result.net_margin,
        "operating_margin": result.operating_margin,
        "revenue_growth": result.revenue_growth_yoy,
        "profit_growth": result.profit_growth_yoy,
        "debt_equity": result.debt_equity,
        "market_cap_cr": result.market_cap_cr,
    }

    return result


def _assess_valuation(r: FundamentalResult, info: dict) -> str:
    pe = r.pe_ratio
    pb = r.pb_ratio
    sector = r.sector.lower()

    # Sector-adjusted PE benchmarks
    if "financial" in sector or "bank" in sector:
        fair_pe, rich_pe = 15, 25
    elif "technology" in sector or "software" in sector:
        fair_pe, rich_pe = 30, 50
    elif "pharma" in sector or "health" in sector:
        fair_pe, rich_pe = 25, 40
    elif "consumer" in sector or "fmcg" in sector.lower():
        fair_pe, rich_pe = 35, 60
    elif "utility" in sector or "power" in sector:
        fair_pe, rich_pe = 12, 20
    elif "material" in sector or "metal" in sector:
        fair_pe, rich_pe = 8, 15
    else:
        fair_pe, rich_pe = 20, 35

    if not np.isfinite(pe) or pe <= 0:
        return "Cannot Assess"
    if pe < fair_pe * 0.7:
        return "Value Pick"
    elif pe < fair_pe:
        return "Attractive"
    elif pe < rich_pe:
        return "Fairly Valued"
    elif pe < rich_pe * 1.5:
        return "Slightly Expensive"
    else:
        return "Expensive"
