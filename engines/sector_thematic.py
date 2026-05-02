"""
Layer 6 — Sector & Thematic Engine
Maps each stock to its sector, evaluates sector momentum
from index performance, and classifies the thematic tailwind.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
import yfinance as yf
from utils.config import SECTOR_MAP
from engines.technical import compute_ema, compute_rsi


# NSE sectoral indices mapped to yfinance tickers
SECTOR_INDICES = {
    "IT":           "^CNXIT",
    "Pharma":       "^CNXPHARMA",
    "Auto":         "^CNXAUTO",
    "FMCG":         "^CNXFMCG",
    "Metals":       "^CNXMETAL",
    "Realty":       "^CNXREALTY",
    "Energy":       "^CNXENERGY",
    "PSE":          "^CNXPSE",
    "Banking":      "^NSEBANK",
    "Infrastructure": "^CNXINFRA",
    "Media":        "^CNXMEDIA",
    "MNC":          "^CNXMNC",
}

# Human-readable thematic scores (based on market cycle knowledge)
# Updated May 2025 thematic view — adjust as cycle evolves
THEMATIC_VIEW = {
    "Banking":        ("Selective Buy",    60, "Rate cut cycle; NIM pressure but credit growth steady"),
    "NBFC":           ("Selective Buy",    58, "Retail credit expansion; watch asset quality"),
    "IT":             ("Neutral",          50, "US spending recovery; rupee tailwind; margin watch"),
    "Pharma":         ("Selective Buy",    65, "Domestic formulations strong; US generics improving"),
    "Defence":        ("Strong Overweight",80, "Multi-year government capex; indigenisation push"),
    "Infra/Railways": ("Strong Overweight",78, "Budget allocation; order book visibility high"),
    "Power":          ("Overweight",       72, "Renewables + transmission build-out"),
    "Capital Goods":  ("Overweight",       70, "Private capex revival; PLI beneficiaries"),
    "Cement":         ("Selective Buy",    55, "Volume growth; coal cost benefit; pricing stable"),
    "Auto":           ("Selective Buy",    58, "EV transition; SUV premiumisation; rural demand"),
    "FMCG":           ("Neutral",          48, "Rural recovery gradual; urban slowdown risk"),
    "Metals":         ("Neutral",          45, "China demand uncertain; domestic infra offset"),
    "Chemicals":      ("Selective Buy",    55, "China+1 opportunity; margin recovery in specialty"),
    "Real Estate":    ("Selective Buy",    60, "Residential cycle strong; commercial REITs growing"),
    "Oil & Gas":      ("Neutral",          48, "Crude volatility; downstream OMC margin pressure"),
    "Consumption":    ("Mild Bullish",     58, "Premiumisation trend; discretionary recovery"),
    "PSU":            ("Neutral",          50, "Capex-linked PSUs good; trading PSUs expensive"),
}


@dataclass
class SectorThematicResult:
    sector_name: str = "Unknown"
    sector_view: str = "Unknown"
    sector_score: int = 50
    sector_momentum: str = "Unknown"
    thematic_tailwind: str = "Unknown"
    thematic_rationale: str = ""
    government_policy_support: bool = False
    global_demand_sensitivity: str = "Low"
    commodity_exposure: str = "None"
    earnings_cycle: str = "Unknown"
    details: dict = field(default_factory=dict)


def _detect_sector(symbol: str, info_sector: str = "") -> str:
    sym_upper = symbol.upper().replace(".NS", "").replace(".BO", "")
    for sector, stocks in SECTOR_MAP.items():
        if sym_upper in stocks:
            return sector

    sec_lower = info_sector.lower()
    if "bank" in sec_lower or "financial" in sec_lower:
        return "Banking"
    if "pharma" in sec_lower or "health" in sec_lower:
        return "Pharma"
    if "technology" in sec_lower or "software" in sec_lower:
        return "IT"
    if "auto" in sec_lower:
        return "Auto"
    if "consumer" in sec_lower or "fmcg" in sec_lower:
        return "FMCG"
    if "metal" in sec_lower or "material" in sec_lower:
        return "Metals"
    if "energy" in sec_lower or "power" in sec_lower:
        return "Power"
    if "real estate" in sec_lower:
        return "Real Estate"
    if "chemical" in sec_lower:
        return "Chemicals"
    if "defence" in sec_lower or "defense" in sec_lower:
        return "Defence"
    if "cement" in sec_lower:
        return "Cement"
    if "capital goods" in sec_lower or "engineering" in sec_lower:
        return "Capital Goods"
    if "oil" in sec_lower or "gas" in sec_lower:
        return "Oil & Gas"
    if "infra" in sec_lower or "construct" in sec_lower:
        return "Infra/Railways"
    return "Diversified"


def _sector_momentum_from_index(sector: str) -> tuple[str, float]:
    """Check sectoral index 3-month performance."""
    idx_ticker = SECTOR_INDICES.get(sector)
    if not idx_ticker:
        return "No Index Data", 50.0

    try:
        df = yf.download(idx_ticker, period="6mo", interval="1d",
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        if df.empty or len(df) < 20:
            return "No Index Data", 50.0

        close = df["Close"].squeeze()
        ret_3m = (float(close.iloc[-1]) - float(close.iloc[-63])) / float(close.iloc[-63]) * 100 if len(close) >= 63 else 0
        ret_1m = (float(close.iloc[-1]) - float(close.iloc[-22])) / float(close.iloc[-22]) * 100 if len(close) >= 22 else 0

        ema20 = float(compute_ema(close, 20).iloc[-1])
        ema50 = float(compute_ema(close, 50).iloc[-1]) if len(close) >= 50 else ema20
        cur   = float(close.iloc[-1])

        if cur > ema20 > ema50 and ret_3m > 5:
            return f"Strong Momentum (3M: +{ret_3m:.1f}%)", 80.0
        elif cur > ema50 and ret_3m > 0:
            return f"Positive Momentum (3M: +{ret_3m:.1f}%)", 65.0
        elif ret_3m < -5 and cur < ema50:
            return f"Weak (3M: {ret_3m:.1f}%)", 30.0
        elif ret_3m < 0:
            return f"Slightly Weak (3M: {ret_3m:.1f}%)", 42.0
        else:
            return f"Neutral (3M: {ret_3m:.1f}%)", 50.0
    except Exception:
        return "No Index Data", 50.0


def analyze_sector_thematic(symbol: str, info_sector: str = "") -> SectorThematicResult:
    result = SectorThematicResult()

    sector = _detect_sector(symbol, info_sector)
    result.sector_name = sector

    # ── Thematic view ──────────────────────────────────────────────────────────
    view_data = THEMATIC_VIEW.get(sector, ("Neutral", 50, "No specific thematic view"))
    result.sector_view       = view_data[0]
    result.sector_score      = view_data[1]
    result.thematic_rationale = view_data[2]

    # ── Government policy support ─────────────────────────────────────────────
    policy_sectors = {"Defence", "Infra/Railways", "Power", "Capital Goods", "Pharma", "Chemicals"}
    result.government_policy_support = sector in policy_sectors

    # ── Commodity exposure ────────────────────────────────────────────────────
    commodity_map = {
        "Metals":   "High (Direct metal prices)",
        "Cement":   "Moderate (Coal, power costs)",
        "Chemicals":"Moderate (Crude derivatives)",
        "Auto":     "Moderate (Steel, aluminium input)",
        "Oil & Gas":"High (Direct crude exposure)",
        "Pharma":   "Low (API inputs — manageable)",
        "Power":    "Moderate (Fuel costs)",
        "FMCG":     "Low-Medium (Palm oil, packaging)",
    }
    result.commodity_exposure = commodity_map.get(sector, "Low")

    # ── Global demand sensitivity ─────────────────────────────────────────────
    global_map = {
        "IT":        "High (US/EU revenue)",
        "Metals":    "High (China-linked)",
        "Chemicals": "High (Export-driven)",
        "Pharma":    "Medium (US generics, EU)",
        "Auto":      "Low-Medium (Exports growing)",
        "Oil & Gas": "High (Crude import dependent)",
        "FMCG":      "Low (Domestic)",
        "Banking":   "Low (Domestic)",
    }
    result.global_demand_sensitivity = global_map.get(sector, "Low")

    # ── Earnings cycle ────────────────────────────────────────────────────────
    earnings_map = {
        "Banking":    "Mid-cycle — rate normalisation phase",
        "IT":         "Early recovery — deal wins improving",
        "Pharma":     "Upcycle — domestic + US improving",
        "Defence":    "Early upcycle — multi-year order visibility",
        "Capital Goods":"Upcycle — capex + PLI driven",
        "Metals":     "Volatile — China demand uncertain",
        "FMCG":       "Slow recovery — rural lagging",
        "Auto":       "Mid-cycle — premiumisation driving",
        "Cement":     "Mid-cycle — volume growth, cost easing",
        "Power":      "Upcycle — massive capacity addition",
        "Infra/Railways": "Upcycle — government spending high",
        "Real Estate":"Upcycle — residential demand robust",
        "Chemicals":  "Recovery — margins bottoming out",
    }
    result.earnings_cycle = earnings_map.get(sector, "Uncertain")

    # ── Sector momentum from NSE index ────────────────────────────────────────
    momentum_label, momentum_score = _sector_momentum_from_index(sector)
    result.sector_momentum = momentum_label

    # Blend static thematic score with live momentum
    result.sector_score = int((result.sector_score * 0.6 + momentum_score * 0.4))

    # ── View label refinement ─────────────────────────────────────────────────
    if result.sector_score >= 75:
        result.thematic_tailwind = "Strong Tailwind"
    elif result.sector_score >= 60:
        result.thematic_tailwind = "Positive Tailwind"
    elif result.sector_score >= 45:
        result.thematic_tailwind = "Neutral"
    elif result.sector_score >= 30:
        result.thematic_tailwind = "Headwind"
    else:
        result.thematic_tailwind = "Strong Headwind"

    result.details = {
        "sector": sector,
        "view": result.sector_view,
        "score": result.sector_score,
        "momentum": momentum_label,
        "policy_support": result.government_policy_support,
        "commodity_exposure": result.commodity_exposure,
        "global_sensitivity": result.global_demand_sensitivity,
    }

    return result
