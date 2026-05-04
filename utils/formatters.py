"""UI helper formatters — color badges, score bars, formatted numbers."""

import numpy as np


def pct_color(val: float) -> str:
    """Return a color string for positive/negative %."""
    if val > 0:
        return "green"
    elif val < 0:
        return "red"
    return "gray"


def color_badge(label: str, color: str) -> str:
    bg_map = {
        "green":  "#1a6632",
        "red":    "#8b1a1a",
        "orange": "#7a4a00",
        "yellow": "#5a5a00",
        "gray":   "#3a3a3a",
        "blue":   "#0a3d6b",
        "purple": "#4a0e8f",
    }
    bg = bg_map.get(color, "#3a3a3a")
    return (
        f'<span style="background:{bg};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.82em;font-weight:600;">{label}</span>'
    )


def action_color(action: str) -> str:
    action_lower = action.lower()
    if "strong add" in action_lower or "strong accumulate" in action_lower:
        return "green"
    elif "add slowly" in action_lower or "accumulate" in action_lower:
        return "green"
    elif "hold" in action_lower and "not" not in action_lower:
        return "blue"
    elif "hold" in action_lower and "not" in action_lower:
        return "orange"
    elif "reduce" in action_lower:
        return "orange"
    elif "exit" in action_lower or "avoid" in action_lower:
        return "red"
    elif "buy" in action_lower:
        return "green"
    elif "short" in action_lower or "bearish" in action_lower:
        return "purple"
    return "gray"


def regime_color(regime: str) -> str:
    if "Strong Bullish" in regime:
        return "green"
    elif "Mild Bullish" in regime:
        return "green"
    elif "Rangebound" in regime:
        return "blue"
    elif "Weak Bearish" in regime:
        return "orange"
    elif "Strong Bearish" in regime:
        return "red"
    elif "Risk-Off" in regime or "Volatility" in regime:
        return "red"
    elif "Event" in regime:
        return "orange"
    return "gray"


def risk_color(risk: str) -> str:
    if "Very High" in risk:
        return "red"
    elif "High" in risk:
        return "orange"
    elif "Moderate" in risk:
        return "yellow"
    else:
        return "green"


def quality_color(quality: str) -> str:
    if "High Quality" in quality:
        return "green"
    elif "Good Quality" in quality:
        return "green"
    elif "Cyclical" in quality:
        return "blue"
    elif "Turnaround" in quality:
        return "orange"
    elif "Speculative" in quality:
        return "orange"
    elif "Weak" in quality:
        return "red"
    return "gray"


def sentiment_color(sentiment: str) -> str:
    if "Strong Bullish" in sentiment:
        return "green"
    elif "Mild Bullish" in sentiment:
        return "green"
    elif "Strong Bearish" in sentiment:
        return "red"
    elif "Bearish" in sentiment:
        return "orange"
    elif "Event" in sentiment:
        return "orange"
    return "gray"


def fmt_crore(val: float) -> str:
    if not np.isfinite(val) or val == 0:
        return "N/A"
    if val >= 1_00_000:
        return f"₹{val/1_00_000:.1f}L Cr"
    elif val >= 1000:
        return f"₹{val/1000:.1f}K Cr"
    return f"₹{val:.0f} Cr"


def fmt_pct(val: float, default="N/A") -> str:
    if not np.isfinite(val):
        return default
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.1f}%"


def fmt_price(val: float) -> str:
    if not np.isfinite(val) or val == 0:
        return "N/A"
    return f"₹{val:,.2f}"


def fmt_ratio(val: float, default="N/A") -> str:
    if not np.isfinite(val) or val == 0:
        return default
    return f"{val:.1f}x"


def score_bar_html(score: int, max_score: int = 100,
                   color: str = "#4CAF50", label: str = "") -> str:
    pct = max(0, min(100, score / max_score * 100))
    if color == "auto":
        if pct >= 65:
            color = "#4CAF50"
        elif pct >= 45:
            color = "#FFC107"
        else:
            color = "#F44336"
    return (
        f'<div style="margin:4px 0">'
        f'<div style="font-size:0.78em;color:#aaa;margin-bottom:2px;">{label}</div>'
        f'<div style="background:#333;border-radius:4px;height:10px;width:100%">'
        f'<div style="background:{color};width:{pct:.0f}%;height:10px;border-radius:4px;'
        f'transition:width 0.5s ease;"></div></div>'
        f'<div style="font-size:0.78em;color:#ccc;text-align:right">{score}/{max_score}</div>'
        f'</div>'
    )


def rr_badge(ratio: float) -> str:
    if ratio >= 3:
        return color_badge(f"R:R = {ratio:.1f}x ✓", "green")
    elif ratio >= 2:
        return color_badge(f"R:R = {ratio:.1f}x", "blue")
    elif ratio >= 1:
        return color_badge(f"R:R = {ratio:.1f}x", "orange")
    else:
        return color_badge(f"R:R = {ratio:.1f}x ✗", "red")
