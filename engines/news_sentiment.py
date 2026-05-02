"""
Layer 4 — News & Sentiment Engine
Pulls recent news from yfinance + RSS feeds, keyword-scores each headline,
and returns an aggregated sentiment with key highlights.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
import feedparser
from utils.data_fetcher import fetch_news
from utils.config import NEWS_RSS_FEEDS


BULLISH_KEYWORDS = [
    "order win", "contract win", "new order", "record revenue", "record profit",
    "beat estimates", "earnings beat", "upgrade", "buy rating", "target raised",
    "strong results", "margin expansion", "debt free", "acqui", "capex",
    "government contract", "launch", "partnership", "approval", "fda approval",
    "dividend", "buyback", "stock split", "bonus", "promoter buying",
    "capacity expansion", "export", "positive outlook", "guidance raised",
    "strong demand", "market share gain",
]

BEARISH_KEYWORDS = [
    "miss", "below estimate", "downgrade", "sell rating", "target cut",
    "profit warning", "revenue decline", "loss", "default", "npa", "fraud",
    "sebi notice", "investigation", "resignation", "pledging", "debt crisis",
    "regulatory", "ban", "recall", "slowdown", "plant shutdown", "strike",
    "promoter selling", "stake sale", "delisting", "insolvency", "nclt",
    "dividend cut", "guidance cut", "margin pressure", "competition",
    "tariff", "penalty", "fine", "raid",
]

EVENT_KEYWORDS = [
    "results", "earnings", "quarterly", "annual report", "rbi policy",
    "budget", "election", "merger", "acquisition", "ipo", "qip", "rights issue",
    "board meeting", "agm", "court", "verdict", "policy change",
]


@dataclass
class NewsSentimentResult:
    sentiment: str = "Neutral"
    sentiment_score: int = 0     # -100 to +100
    headline_count: int = 0
    bullish_count: int = 0
    bearish_count: int = 0
    event_count: int = 0
    top_headlines: list = field(default_factory=list)
    key_catalysts: list = field(default_factory=list)
    key_risks: list = field(default_factory=list)
    event_flags: list = field(default_factory=list)
    details: dict = field(default_factory=dict)


def _score_headline(text: str) -> int:
    text_lower = text.lower()
    score = 0
    for kw in BULLISH_KEYWORDS:
        if kw in text_lower:
            score += 10
    for kw in BEARISH_KEYWORDS:
        if kw in text_lower:
            score -= 10
    return max(-100, min(100, score))


def _extract_catalyst_or_risk(text: str) -> tuple[str, str]:
    """Returns ('catalyst'|'risk'|'event'|'neutral', cleaned text)."""
    score = _score_headline(text)
    text_lower = text.lower()
    for kw in EVENT_KEYWORDS:
        if kw in text_lower:
            return "event", text
    if score > 5:
        return "catalyst", text
    elif score < -5:
        return "risk", text
    return "neutral", text


def analyze_news_sentiment(symbol: str) -> NewsSentimentResult:
    result = NewsSentimentResult()

    # ── yfinance news ─────────────────────────────────────────────────────────
    raw_news = fetch_news(symbol)
    headlines = []
    for item in raw_news:
        title = item.get("title", "")
        link  = item.get("link", "")
        if title:
            headlines.append({"title": title, "link": link, "source": "Yahoo Finance"})

    # ── RSS feeds (symbol-agnostic but sector relevant) ───────────────────────
    for feed_url in NEWS_RSS_FEEDS[:2]:   # cap at 2 to keep latency low
        try:
            feed  = feedparser.parse(feed_url)
            sym_upper = symbol.upper().replace(".NS", "").replace(".BO", "")
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                if sym_upper in title.upper() or sym_upper.replace("&", "AND") in title.upper():
                    headlines.append({
                        "title": title,
                        "link":  entry.get("link", ""),
                        "source": feed.feed.get("title", "RSS"),
                    })
        except Exception:
            continue

    result.headline_count = len(headlines)

    if not headlines:
        result.sentiment = "No Recent News"
        result.details["note"] = "No news found — treat as neutral; verify manually"
        return result

    # ── Score each headline ───────────────────────────────────────────────────
    scores = []
    for h in headlines[:15]:
        s = _score_headline(h["title"])
        scores.append(s)
        htype, _ = _extract_catalyst_or_risk(h["title"])
        if htype == "catalyst":
            result.bullish_count += 1
            result.key_catalysts.append(h["title"])
        elif htype == "risk":
            result.bearish_count += 1
            result.key_risks.append(h["title"])
        elif htype == "event":
            result.event_count += 1
            result.event_flags.append(h["title"])

    result.top_headlines = [h["title"] for h in headlines[:8]]

    avg_score = sum(scores) / len(scores) if scores else 0
    result.sentiment_score = int(max(-100, min(100, avg_score)))

    # ── Sentiment label ───────────────────────────────────────────────────────
    if result.sentiment_score >= 40:
        result.sentiment = "Strong Bullish"
    elif result.sentiment_score >= 15:
        result.sentiment = "Mild Bullish"
    elif result.sentiment_score <= -40:
        result.sentiment = "Strong Bearish"
    elif result.sentiment_score <= -15:
        result.sentiment = "Mild Bearish"
    elif result.event_count >= 2:
        result.sentiment = "Event Risk — Outcome Uncertain"
    else:
        result.sentiment = "Neutral"

    # ── Sebi / governance red flags ───────────────────────────────────────────
    combined = " ".join(result.top_headlines).lower()
    red_flags = ["sebi", "fraud", "scam", "cbi", "ed raid", "npa", "default",
                 "insolvency", "nclt", "promoter pledge", "pledging"]
    for flag in red_flags:
        if flag in combined:
            result.key_risks.append(f"⚠ Potential governance/regulatory concern detected: '{flag}'")

    result.details = {
        "avg_score": round(avg_score, 1),
        "headlines_analyzed": min(len(headlines), 15),
    }

    return result
