"""
Fetches and caches the complete NSE + BSE equity list.
Provides symbol → company name lookup for autocomplete and live NSE search.
"""

import time
import requests
import pandas as pd
from io import StringIO
from pathlib import Path

# Local cache files (stored in project root, gitignored)
_NSE_CACHE = Path(__file__).parent.parent / ".nse_equity_list.csv"
_BSE_CACHE = Path(__file__).parent.parent / ".bse_equity_list.csv"
_CACHE_TTL  = 7 * 24 * 3600   # refresh once a week

# NSE official equity list (main board EQ/BE/BZ series)
_NSE_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

# BSE active equity list via BSE API
_BSE_URL = (
    "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
    "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
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


# ── Public API ────────────────────────────────────────────────────────────────

def get_nse_symbol_map() -> dict[str, str]:
    """
    Returns {SYMBOL: "Company Name"} merging NSE + BSE main board equity lists.
    Uses local cache refreshed weekly; falls back to built-in list if downloads fail.
    For SME/Emerge stocks use nse_live_search() instead.
    """
    # NSE main board
    nse = _load_cache(_NSE_CACHE) if _fresh(_NSE_CACHE) else _fetch_nse()
    if not nse:
        nse = _load_cache(_NSE_CACHE)

    # BSE main board
    bse = _load_cache(_BSE_CACHE) if _fresh(_BSE_CACHE) else _fetch_bse()
    if not bse:
        bse = _load_cache(_BSE_CACHE)

    # Merge: NSE names take priority for same symbol (better formatted)
    merged = {**bse, **nse}

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


def _create_nse_session() -> requests.Session:
    """Establish a session with NSE to obtain cookies for authenticated API access."""
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=_HEADERS, timeout=15)
    except Exception:
        pass
    return session


def nse_live_search(query: str) -> list[str]:
    """
    Live NSE symbol search using the NSE autocomplete API.
    Covers all stocks including SME/Emerge (e.g. FRESHARA) not in the static list.
    Returns list of 'SYMBOL — Company Name' or 'SYMBOL — Company Name [SME]' strings.
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
                tag  = " [SME]" if item.get("result_sub_type") == "sme" else ""
                if sym and name:
                    results.append(f"{sym} — {name}{tag}")
        return results
    except Exception:
        return []
