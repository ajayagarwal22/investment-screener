"""
Layer 3 — Technical Analysis Engine
Full suite: EMA, RSI, MACD, Bollinger Bands, VWAP, ATR,
support/resistance, breakout detection, relative strength.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from utils.config import (
    EMA_PERIODS, RSI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BB_PERIOD, BB_STD, ATR_PERIOD, VOLUME_MA,
    RSI_OVERSOLD, RSI_OVERBOUGHT, RSI_NEUTRAL_LOW, RSI_NEUTRAL_HIGH,
)


# ── Pure indicator functions (used by other engines too) ─────────────────────

def compute_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta  = series.diff()
    gain   = delta.clip(lower=0)
    loss   = (-delta).clip(lower=0)
    avg_g  = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_l  = loss.ewm(alpha=1/period, adjust=False).mean()
    rs     = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series,
                 fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL
                 ) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast   = compute_ema(series, fast)
    ema_slow   = compute_ema(series, slow)
    macd_line  = ema_fast - ema_slow
    signal_line = compute_ema(macd_line, signal)
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger(series: pd.Series,
                      period=BB_PERIOD, std_dev=BB_STD
                      ) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid   = series.rolling(period).mean()
    std   = series.rolling(period).std()
    upper = mid + std_dev * std
    lower = mid - std_dev * std
    return upper, mid, lower


def compute_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series:
    high  = df["High"].squeeze()
    low   = df["Low"].squeeze()
    close = df["Close"].squeeze()
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["High"].squeeze() + df["Low"].squeeze() + df["Close"].squeeze()) / 3
    vol     = df["Volume"].squeeze()
    cum_tv  = (typical * vol).cumsum()
    cum_v   = vol.cumsum()
    return cum_tv / cum_v


def volume_ma(df: pd.DataFrame, period=VOLUME_MA) -> pd.Series:
    return df["Volume"].squeeze().rolling(period).mean()


# ── Support / Resistance ─────────────────────────────────────────────────────

def find_support_resistance(close: pd.Series, window: int = 20, n_levels: int = 3
                            ) -> tuple[list, list]:
    """Returns (support_levels, resistance_levels) from recent pivot highs/lows."""
    highs  = close.rolling(window, center=True).max()
    lows   = close.rolling(window, center=True).min()

    pivots_high = close[close == highs].dropna()
    pivots_low  = close[close == lows].dropna()

    resistance = sorted(pivots_high.values, reverse=True)[:n_levels]
    support    = sorted(pivots_low.values)[:n_levels]
    return [round(float(s), 2) for s in support], [round(float(r), 2) for r in resistance]


# ── Main technical analysis dataclass ───────────────────────────────────────

@dataclass
class TechnicalResult:
    setup: str = "Unknown"
    setup_score: int = 0       # -100 to +100
    trend_direction: str = "Unknown"
    price: float = 0.0

    ema20: float = 0.0
    ema50: float = 0.0
    ema100: float = 0.0
    ema200: float = 0.0
    rsi: float = 50.0
    macd_signal: str = "Neutral"
    macd_histogram: float = 0.0
    bb_position: str = "Middle"
    vwap: float = 0.0
    atr: float = 0.0
    atr_pct: float = 0.0
    volume_vs_avg: float = 1.0
    volume_signal: str = "Normal"

    supports: list = field(default_factory=list)
    resistances: list = field(default_factory=list)

    intraday_buy_zone: tuple = field(default_factory=tuple)
    swing_buy_zone: tuple = field(default_factory=tuple)
    stop_loss_intraday: float = 0.0
    stop_loss_swing: float = 0.0
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0

    breakout_detected: bool = False
    breakdown_detected: bool = False
    is_higher_high: bool = False
    is_lower_low: bool = False
    relative_strength_vs_nifty: str = "Neutral"

    weekly_trend: str = "Unknown"
    monthly_trend: str = "Unknown"

    details: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def analyze_technicals(daily_df: pd.DataFrame, weekly_df: pd.DataFrame = None,
                        monthly_df: pd.DataFrame = None,
                        nifty_df: pd.DataFrame = None) -> TechnicalResult:
    result = TechnicalResult()

    if daily_df is None or daily_df.empty or len(daily_df) < 30:
        result.setup = "Insufficient Data"
        return result

    close  = daily_df["Close"].squeeze()
    high   = daily_df["High"].squeeze()
    low    = daily_df["Low"].squeeze()
    volume = daily_df["Volume"].squeeze()

    price = float(close.iloc[-1])
    result.price = price

    # ── EMAs ──────────────────────────────────────────────────────────────────
    ema_vals = {}
    for p in EMA_PERIODS:
        if len(close) >= p:
            ema_vals[p] = float(compute_ema(close, p).iloc[-1])
        else:
            ema_vals[p] = None

    result.ema20  = ema_vals.get(20,  0.0) or 0.0
    result.ema50  = ema_vals.get(50,  0.0) or 0.0
    result.ema100 = ema_vals.get(100, 0.0) or 0.0
    result.ema200 = ema_vals.get(200, 0.0) or 0.0

    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi_series = compute_rsi(close, RSI_PERIOD)
    result.rsi = round(float(rsi_series.iloc[-1]), 1)

    # ── MACD ──────────────────────────────────────────────────────────────────
    macd_line, sig_line, histogram = compute_macd(close)
    hist_val  = float(histogram.iloc[-1])
    hist_prev = float(histogram.iloc[-2]) if len(histogram) > 1 else 0
    result.macd_histogram = round(hist_val, 4)

    if hist_val > 0 and hist_val > hist_prev:
        result.macd_signal = "Strong Bullish"
    elif hist_val > 0:
        result.macd_signal = "Bullish (Weakening)"
    elif hist_val < 0 and hist_val < hist_prev:
        result.macd_signal = "Strong Bearish"
    elif hist_val < 0:
        result.macd_signal = "Bearish (Easing)"
    else:
        result.macd_signal = "Neutral"

    # ── Bollinger Bands ───────────────────────────────────────────────────────
    bb_up, bb_mid, bb_lo = compute_bollinger(close)
    bb_width = float(bb_up.iloc[-1]) - float(bb_lo.iloc[-1])
    bb_pos   = (price - float(bb_lo.iloc[-1])) / bb_width if bb_width > 0 else 0.5

    if bb_pos > 0.85:
        result.bb_position = "Near Upper Band (Overbought)"
    elif bb_pos < 0.15:
        result.bb_position = "Near Lower Band (Oversold)"
    elif bb_pos > 0.6:
        result.bb_position = "Upper Half"
    elif bb_pos < 0.4:
        result.bb_position = "Lower Half"
    else:
        result.bb_position = "Middle Band"

    # ── VWAP ──────────────────────────────────────────────────────────────────
    try:
        vwap_series = compute_vwap(daily_df)
        result.vwap = round(float(vwap_series.iloc[-1]), 2)
    except Exception:
        result.vwap = price

    # ── ATR ───────────────────────────────────────────────────────────────────
    atr_series = compute_atr(daily_df)
    atr_val    = float(atr_series.iloc[-1])
    result.atr     = round(atr_val, 2)
    result.atr_pct = round(atr_val / price * 100, 2)

    # ── Volume ────────────────────────────────────────────────────────────────
    vol_ma    = float(volume_ma(daily_df).iloc[-1])
    vol_today = float(volume.iloc[-1])
    ratio     = vol_today / vol_ma if vol_ma > 0 else 1.0
    result.volume_vs_avg = round(ratio, 2)

    price_up = price > float(close.iloc[-2])
    if ratio > 2.0 and price_up:
        result.volume_signal = "High Volume Breakout"
    elif ratio > 2.0 and not price_up:
        result.volume_signal = "High Volume Breakdown / Distribution"
    elif ratio > 1.4 and price_up:
        result.volume_signal = "Above Average Buying"
    elif ratio > 1.4:
        result.volume_signal = "Above Average Selling"
    elif ratio < 0.6:
        result.volume_signal = "Low Volume (Weak Move)"
    else:
        result.volume_signal = "Normal Volume"

    # ── Support / Resistance ──────────────────────────────────────────────────
    raw_supports, raw_resistances = find_support_resistance(close)
    # Keep levels that make directional sense; sort so index 0 is always nearest price
    result.supports    = sorted([s for s in raw_supports    if s < price * 0.999], reverse=True)[:3]  # nearest below first
    result.resistances = sorted([r for r in raw_resistances if r > price * 1.001])[:3]                # nearest above first
    result.details["52w_high"] = round(float(high.rolling(252).max().iloc[-1]), 2) if len(high) >= 252 else round(float(high.max()), 2)
    result.details["52w_low"]  = round(float(low.rolling(252).min().iloc[-1]),  2) if len(low)  >= 252 else round(float(low.min()), 2)

    # ── Breakout / Breakdown ──────────────────────────────────────────────────
    prev_20d_high = float(high.iloc[-21:-1].max()) if len(high) > 21 else float(high.max())
    prev_20d_low  = float(low.iloc[-21:-1].min())  if len(low)  > 21 else float(low.min())

    if price > prev_20d_high and ratio > 1.3:
        result.breakout_detected = True
    if price < prev_20d_low and ratio > 1.3:
        result.breakdown_detected = True

    # ── Higher High / Lower Low ───────────────────────────────────────────────
    if len(high) >= 40:
        prev_peak    = float(high.iloc[-40:-20].max())
        current_peak = float(high.iloc[-20:].max())
        prev_trough    = float(low.iloc[-40:-20].min())
        current_trough = float(low.iloc[-20:].min())
        result.is_higher_high = current_peak > prev_peak
        result.is_lower_low   = current_trough < prev_trough

    # ── Relative Strength vs Nifty ────────────────────────────────────────────
    if nifty_df is not None and not nifty_df.empty and len(nifty_df) >= 20:
        try:
            nifty_close = nifty_df["Close"].squeeze()
            stock_ret   = (price - float(close.iloc[-20])) / float(close.iloc[-20]) * 100
            nifty_ret   = (float(nifty_close.iloc[-1]) - float(nifty_close.iloc[-20])) / float(nifty_close.iloc[-20]) * 100
            rs_diff     = stock_ret - nifty_ret
            if rs_diff > 5:
                result.relative_strength_vs_nifty = f"Strong Outperformer (+{rs_diff:.1f}% vs Nifty)"
            elif rs_diff > 1:
                result.relative_strength_vs_nifty = f"Mild Outperformer (+{rs_diff:.1f}% vs Nifty)"
            elif rs_diff < -5:
                result.relative_strength_vs_nifty = f"Underperformer ({rs_diff:.1f}% vs Nifty)"
            elif rs_diff < -1:
                result.relative_strength_vs_nifty = f"Mild Underperformer ({rs_diff:.1f}% vs Nifty)"
            else:
                result.relative_strength_vs_nifty = f"In Line with Nifty ({rs_diff:+.1f}%)"
        except Exception:
            pass

    # ── Weekly / Monthly trend ────────────────────────────────────────────────
    if weekly_df is not None and not weekly_df.empty and len(weekly_df) >= 20:
        wclose = weekly_df["Close"].squeeze()
        w_ema20 = float(compute_ema(wclose, 20).iloc[-1])
        w_ema50 = float(compute_ema(wclose, 50).iloc[-1]) if len(wclose) >= 50 else None
        w_price = float(wclose.iloc[-1])
        if w_price > w_ema20 and (w_ema50 is None or w_price > w_ema50):
            result.weekly_trend = "Bullish"
        elif w_price < w_ema20 and (w_ema50 is None or w_price < w_ema50):
            result.weekly_trend = "Bearish"
        else:
            result.weekly_trend = "Mixed"

    if monthly_df is not None and not monthly_df.empty and len(monthly_df) >= 12:
        mclose = monthly_df["Close"].squeeze()
        m_ema12 = float(compute_ema(mclose, 12).iloc[-1])
        m_price = float(mclose.iloc[-1])
        if m_price > m_ema12:
            result.monthly_trend = "Long-Term Bullish"
        else:
            result.monthly_trend = "Long-Term Bearish"

    # ── Scoring ───────────────────────────────────────────────────────────────
    score = 0

    # Price vs EMAs
    if ema_vals.get(20)  and price > ema_vals[20]:  score += 15
    else: score -= 10
    if ema_vals.get(50)  and price > ema_vals[50]:  score += 20
    else: score -= 15
    if ema_vals.get(200) and price > ema_vals[200]: score += 20
    else: score -= 20

    # RSI
    if 50 <= result.rsi <= RSI_NEUTRAL_HIGH:
        score += 15
    elif result.rsi > RSI_NEUTRAL_HIGH:
        score += 8
    elif result.rsi < RSI_OVERSOLD:
        score -= 20
    elif result.rsi < RSI_NEUTRAL_LOW:
        score -= 10

    # MACD
    if "Strong Bullish" in result.macd_signal:   score += 15
    elif "Bullish" in result.macd_signal:        score += 8
    elif "Strong Bearish" in result.macd_signal: score -= 15
    elif "Bearish" in result.macd_signal:        score -= 8

    # Volume
    if result.volume_signal == "High Volume Breakout": score += 15
    elif result.volume_signal == "Above Average Buying": score += 8
    elif result.volume_signal == "High Volume Breakdown / Distribution": score -= 15

    # Breakout/Breakdown
    if result.breakout_detected:  score += 10
    if result.breakdown_detected: score -= 10

    result.setup_score = max(-100, min(100, score))

    # ── Setup label ───────────────────────────────────────────────────────────
    if result.setup_score >= 60:
        result.setup = "Strong Bullish Setup"
    elif result.setup_score >= 30:
        result.setup = "Mild Bullish Setup"
    elif result.setup_score >= 10:
        result.setup = "Cautiously Bullish"
    elif result.setup_score >= -10:
        result.setup = "Neutral / Rangebound"
    elif result.setup_score >= -30:
        result.setup = "Mild Bearish Setup"
    elif result.setup_score >= -60:
        result.setup = "Bearish Setup"
    else:
        result.setup = "Strong Bearish Setup"

    # ── Trend direction ───────────────────────────────────────────────────────
    ema_above_count = sum(1 for p in [20, 50, 200]
                          if ema_vals.get(p) and price > ema_vals[p])
    if ema_above_count == 3:
        result.trend_direction = "Strong Uptrend"
    elif ema_above_count == 2:
        result.trend_direction = "Uptrend"
    elif ema_above_count == 0:
        result.trend_direction = "Strong Downtrend"
    elif ema_above_count == 1:
        result.trend_direction = "Downtrend"
    else:
        result.trend_direction = "Mixed"

    # ── Trade zones ───────────────────────────────────────────────────────────
    atr2 = atr_val * 2
    if result.vwap > 0:
        intra_buy_low  = round(min(price * 0.995, result.vwap * 0.998), 2)
        intra_buy_high = round(max(price * 1.003, result.vwap * 1.002), 2)
    else:
        intra_buy_low  = round(price - atr_val * 0.5, 2)
        intra_buy_high = round(price + atr_val * 0.3, 2)

    result.intraday_buy_zone    = (intra_buy_low, intra_buy_high)
    result.stop_loss_intraday   = round(price - atr_val * 1.0, 2)

    # Swing zones — use nearest support below price for stop loss
    if result.supports:
        swing_sl = max(result.supports[0], price - atr2)
    else:
        swing_sl = price - atr2
    result.swing_buy_zone  = (round(price - atr_val * 0.5, 2), round(price + atr_val * 0.3, 2))
    result.stop_loss_swing = round(swing_sl, 2)

    # Targets — always above current price, always ascending T1 < T2 < T3
    # result.resistances is already sorted ascending (nearest above price first)
    result.target_1 = round(price + atr2,     2)
    result.target_2 = round(price + atr2 * 2, 2)
    result.target_3 = round(price + atr2 * 3, 2)
    if len(result.resistances) >= 1:
        result.target_1 = round(result.resistances[0], 2)
    if len(result.resistances) >= 2:
        result.target_2 = round(result.resistances[1], 2)
    elif result.target_2 <= result.target_1:          # fallback if only one resistance
        result.target_2 = round(result.target_1 + atr2, 2)
    if result.target_3 <= result.target_2:
        result.target_3 = round(result.target_2 + atr2, 2)

    # ── Warnings ──────────────────────────────────────────────────────────────
    if result.rsi > 75:
        result.warnings.append(f"RSI at {result.rsi} — Overbought, risk of pullback")
    if result.rsi < 25:
        result.warnings.append(f"RSI at {result.rsi} — Deeply oversold, potential dead-cat bounce risk")
    if result.breakdown_detected:
        result.warnings.append("Breakdown on volume — potential falling knife, avoid averaging")
    if "Underperformer" in result.relative_strength_vs_nifty:
        result.warnings.append("Relative weakness vs Nifty — avoid unless strong catalyst")
    if result.volume_signal == "High Volume Breakdown / Distribution":
        result.warnings.append("High-volume selling detected — smart money may be exiting")

    return result
