"""
Fetches and caches the complete NSE + BSE equity list including SME/Emerge.
Provides symbol → company name lookup for autocomplete.
"""

import time
import requests
import pandas as pd
from io import StringIO
from pathlib import Path

# Local cache files (stored in project root, gitignored)
_NSE_CACHE     = Path(__file__).parent.parent / ".nse_equity_list.csv"
_BSE_CACHE     = Path(__file__).parent.parent / ".bse_equity_list.csv"
_NSE_SME_CACHE = Path(__file__).parent.parent / ".nse_sme_list.csv"
_BSE_SME_CACHE = Path(__file__).parent.parent / ".bse_sme_list.csv"
_CACHE_TTL     = 7 * 24 * 3600   # refresh once a week

# NSE official equity list (main board EQ series)
_NSE_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

# BSE active equity list via BSE API
_BSE_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
)

# BSE SME/Emerge segment
_BSE_SME_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=SME&status=Active"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _fresh(path: Path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < _CACHE_TTL


def _save_cache(path: Path, data: dict[str, str]) -> None:
    pd.DataFrame({"SYMBOL": list(data.keys()), "NAME": list(data.values())}).to_csv(path, index=False)


def _load_cache(path: Path) -> dict[str, str]:
    try:
        df = pd.read_csv(path)
        return dict(zip(df["SYMBOL"].astype(str).str.strip().str.upper(),
                        df["NAME"].astype(str).str.strip()))
    except Exception:
        return {}


# ── NSE main board fetcher ────────────────────────────────────────────────────

def _fetch_nse() -> dict[str, str]:
    try:
        resp = requests.get(_NSE_URL, headers={**_HEADERS, "Referer": "https://www.nseindia.com/"},
                            timeout=15)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text))

        sym_col  = next((c for c in df.columns if "SYMBOL" in c.upper()), None)
        name_col = next((c for c in df.columns if "NAME" in c.upper() and "COMPANY" in c.upper()), None)
        ser_col  = next((c for c in df.columns if "SERIES" in c.upper()), None)

        if not sym_col or not name_col:
            return {}

        # Main board series (EQ = regular, BE/BZ = trade-to-trade, IL/IV = bonds)
        VALID_SERIES = {"EQ", "BE", "BZ", "IL", "IV"}
        if ser_col:
            df = df[df[ser_col].astype(str).str.strip().str.upper().isin(VALID_SERIES)]

        result: dict[str, str] = {}
        for _, row in df.iterrows():
            s = str(row[sym_col]).strip().upper()
            n = str(row[name_col]).strip().title()
            if s and s not in ("Nan", "NAN", ""):
                result[s] = n

        if result:
            _save_cache(_NSE_CACHE, result)
        return result
    except Exception:
        return {}


# ── NSE Emerge/SME fetcher ────────────────────────────────────────────────────

def _create_nse_session() -> requests.Session:
    """Establish a session with NSE to obtain cookies for API access."""
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=_HEADERS, timeout=15)
    except Exception:
        pass
    return session


def _fetch_nse_sme() -> dict[str, str]:
    """
    Fetch NSE Emerge/SME stocks.
    Tries multiple NSE endpoints in order; falls back to alphabetic
    autocomplete search (A-Z) if bulk endpoints are unavailable.
    """
    result: dict[str, str] = {}
    try:
        session = _create_nse_session()
        nse_headers = {**_HEADERS, "Referer": "https://www.nseindia.com/emerge"}

        # ── Attempt 1: NSE Emerge index constituents ──────────────────────────
        emerge_index_urls = [
            "https://www.nseindia.com/api/equity-stockIndices?index=EMERGE%20BOARD%20IND",
            "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20EMERGE%20BOARD%20IND",
            "https://www.nseindia.com/api/allSymbols?marketType=EMERGE",
        ]
        for url in emerge_index_urls:
            try:
                resp = session.get(url, headers=nse_headers, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    stocks = data if isinstance(data, list) else data.get(
                        "data", data.get("records", data.get("Table", [])))
                    for item in (stocks if isinstance(stocks, list) else []):
                        if not isinstance(item, dict):
                            continue
                        il = {k.lower(): v for k, v in item.items()}
                        sym = str(il.get("symbol", il.get("scripid", ""))).strip().upper()
                        name = str(il.get("companyname", il.get("scripname",
                               il.get("issuer_name", "")))).strip().title()
                        if sym and name and sym not in ("Nan", "NAN", ""):
                            result[sym] = name
                    if result:
                        break
            except Exception:
                continue

        # ── Attempt 2: Alphabetic autocomplete search ─────────────────────────
        # Each query returns up to 10 results; 26 queries ≈ 260 SME stocks min
        if not result:
            for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                try:
                    resp = session.get(
                        f"https://www.nseindia.com/api/search/autocomplete?q={char}",
                        headers=nse_headers,
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        for item in resp.json().get("data", []):
                            if item.get("result_sub_type") == "sme":
                                sym  = str(item.get("symbol", "")).strip().upper()
                                name = str(item.get("symbol_info", "")).strip()
                                if sym and name:
                                    result[sym] = name
                    time.sleep(0.25)
                except Exception:
                    continue

    except Exception:
        pass

    if result:
        _save_cache(_NSE_SME_CACHE, result)
    return result


# ── BSE main board fetcher ────────────────────────────────────────────────────

def _fetch_bse() -> dict[str, str]:
    try:
        resp = requests.get(_BSE_URL, headers={**_HEADERS, "Referer": "https://www.bseindia.com/"},
                            timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        # BSE API may wrap in {"Table": [...]} or return a list directly
        items = raw if isinstance(raw, list) else raw.get("Table", raw.get("data", []))

        result: dict[str, str] = {}
        for item in items:
            # Use case-insensitive key lookup to handle BSE's mixed-case keys
            item_lower = {k.lower(): v for k, v in item.items()}
            sym  = str(item_lower.get("scrip_id",   "")).strip().upper()
            name = str(item_lower.get("scrip_name", item_lower.get("issuer_name", ""))).strip().title()
            # Strip trailing $ or - from suspended/delisted markers
            name = name.rstrip(" $-").strip()
            if sym and name and sym not in ("Nan", "NAN", ""):
                result[sym] = name

        if result:
            _save_cache(_BSE_CACHE, result)
        return result
    except Exception:
        return {}


# ── BSE SME/Emerge fetcher ────────────────────────────────────────────────────

def _fetch_bse_sme() -> dict[str, str]:
    """Fetch BSE SME/Emerge segment stocks (segment=SME)."""
    try:
        resp = requests.get(_BSE_SME_URL,
                            headers={**_HEADERS, "Referer": "https://www.bseindia.com/"},
                            timeout=15)
        resp.raise_for_status()
        raw = resp.json()

        items = raw if isinstance(raw, list) else raw.get("Table", raw.get("data", []))

        result: dict[str, str] = {}
        for item in items:
            item_lower = {k.lower(): v for k, v in item.items()}
            sym  = str(item_lower.get("scrip_id",   "")).strip().upper()
            name = str(item_lower.get("scrip_name", item_lower.get("issuer_name", ""))).strip().title()
            name = name.rstrip(" $-").strip()
            if sym and name and sym not in ("Nan", "NAN", ""):
                result[sym] = name

        if result:
            _save_cache(_BSE_SME_CACHE, result)
        return result
    except Exception:
        return {}


# ── Public API ────────────────────────────────────────────────────────────────

def get_nse_symbol_map() -> dict[str, str]:
    """
    Returns {SYMBOL: "Company Name"} merging NSE + BSE equity lists
    including SME/Emerge segments.
    Uses local cache refreshed weekly; falls back to built-in list if
    downloads fail.
    """
    # NSE main board
    nse = _load_cache(_NSE_CACHE) if _fresh(_NSE_CACHE) else _fetch_nse()
    if not nse:
        nse = _load_cache(_NSE_CACHE)

    # BSE main board
    bse = _load_cache(_BSE_CACHE) if _fresh(_BSE_CACHE) else _fetch_bse()
    if not bse:
        bse = _load_cache(_BSE_CACHE)

    # BSE SME/Emerge
    bse_sme = _load_cache(_BSE_SME_CACHE) if _fresh(_BSE_SME_CACHE) else _fetch_bse_sme()
    if not bse_sme:
        bse_sme = _load_cache(_BSE_SME_CACHE)

    # NSE SME/Emerge
    nse_sme = _load_cache(_NSE_SME_CACHE) if _fresh(_NSE_SME_CACHE) else _fetch_nse_sme()
    if not nse_sme:
        nse_sme = _load_cache(_NSE_SME_CACHE)

    # Merge priority (highest wins): curated > NSE main > BSE main > NSE SME > BSE SME
    merged = {**bse_sme, **nse_sme, **bse, **nse}

    if not merged:
        from utils.config import NSE_SYMBOL_MAP
        return dict(NSE_SYMBOL_MAP)

    # Overlay hand-curated names for known stocks
    from utils.config import NSE_SYMBOL_MAP
    merged.update(NSE_SYMBOL_MAP)

    return merged


def get_search_options(symbol_map: dict[str, str]) -> list[str]:
    """Return sorted 'SYMBOL — Company Name' strings for the selectbox."""
    return sorted(f"{sym} — {name}" for sym, name in symbol_map.items())


def symbol_from_option(option: str) -> str:
    """Extract the NSE/BSE symbol from a selectbox option string."""
    return option.split(" — ")[0].strip()


def nse_live_search(query: str) -> list[str]:
    """
    Live NSE symbol search including SME/Emerge stocks.
    Uses NSE session-based autocomplete API.
    Returns list of 'SYMBOL — Company Name' strings.
    """
    q = query.strip()
    if len(q) < 2:
        return []
    try:
        session = _create_nse_session()
        resp = session.get(
            f"https://www.nseindia.com/api/search/autocomplete?q={q}",
            headers={**_HEADERS, "Referer": "https://www.nseindia.com/"},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        items = resp.json().get("symbols", [])
        results = []
        for item in items:
            if item.get("result_type") == "symbol":
                sym  = str(item.get("symbol", "")).strip().upper()
                name = str(item.get("symbol_info", "")).strip()
                sub  = item.get("result_sub_type", "")
                tag  = " [SME]" if sub == "sme" else ""
                if sym and name:
                    results.append(f"{sym} — {name}{tag}")
        return results
    except Exception:
        return []
