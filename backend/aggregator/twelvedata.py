"""Twelve Data API Adapter: primaerer Datenprovider statt yfinance.

Free Tier: 800 Credits/Tag, 8 Requests/Minute.
Unterstuetzt internationale Ticker (.DE, .PA, .L, .SW etc.) nativ.
Docs: https://twelvedata.com/docs
"""
import time
import structlog
import httpx
import redis
from datetime import date, datetime
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

BASE_URL = "https://api.twelvedata.com"

# Mapping deutscher/europaeischer Suffixe zu Twelve-Data-Exchange-Parametern
# Twelve Data nutzt MIC-Codes oder Exchange-Kuerzel
EXCHANGE_MAP = {
    ".DE": "XETR",   # Xetra Frankfurt
    ".PA": "XPAR",   # Euronext Paris
    ".AS": "XAMS",   # Euronext Amsterdam
    ".MI": "XMIL",   # Borsa Italiana
    ".MC": "XMAD",   # Madrid
    ".SW": "XSWX",   # SIX Swiss
    ".L":  "XLON",   # London
    ".HE": "XHEL",   # Helsinki
    ".TO": "XTSE",   # Toronto
    ".AX": "XASX",   # Sydney
    ".HK": "XHKG",   # Hong Kong
    ".T":  "XTKS",   # Tokyo
}


def _parse_symbol(symbol: str) -> tuple[str, str | None]:
    """Extrahiere Basis-Symbol und Exchange aus 'AAPL' / 'DTE.DE' / 'TTE.PA'."""
    for suffix, exchange in EXCHANGE_MAP.items():
        if symbol.upper().endswith(suffix):
            return symbol[: -len(suffix)], exchange
    return symbol, None


def _is_rate_limited() -> bool:
    """Pruefe Tages-Limit (Redis-Counter)."""
    day_key = f"td_calls:{date.today().isoformat()}"
    count = int(redis_client.get(day_key) or 0)
    return count >= 750  # Sicherheitspuffer unter 800


def _increment_counter() -> None:
    day_key = f"td_calls:{date.today().isoformat()}"
    minute_key = f"td_calls_min:{int(time.time() // 60)}"
    pipe = redis_client.pipeline()
    pipe.incr(day_key)
    pipe.expire(day_key, 86400)
    pipe.incr(minute_key)
    pipe.expire(minute_key, 120)
    pipe.execute()


def is_available() -> bool:
    """Ist Twelve Data konfiguriert und nicht im Limit?"""
    return bool(settings.twelvedata_api_key) and not _is_rate_limited()


def fetch_time_series(symbol: str, days: int = 365) -> list[dict] | None:
    """Hole historische Tagesdaten. Returns Liste von {date, open, high, low, close, volume}."""
    if not settings.twelvedata_api_key:
        return None
    if _is_rate_limited():
        logger.warning("twelvedata.rate_limit_hit", symbol=symbol)
        return None

    base, exchange = _parse_symbol(symbol)
    params = {
        "symbol": base,
        "interval": "1day",
        "outputsize": min(days, 5000),
        "apikey": settings.twelvedata_api_key,
        "format": "JSON",
    }
    if exchange:
        params["exchange"] = exchange

    try:
        resp = httpx.get(f"{BASE_URL}/time_series", params=params, timeout=15)
        _increment_counter()
        data = resp.json()

        if data.get("status") == "error":
            logger.warning("twelvedata.error", symbol=symbol, message=data.get("message"))
            return None

        values = data.get("values", [])
        if not values:
            return None

        result = []
        for v in values:
            try:
                result.append({
                    "date": datetime.strptime(v["datetime"], "%Y-%m-%d").date(),
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                    "volume": int(float(v.get("volume", 0))),
                })
            except (ValueError, KeyError):
                continue

        # Twelve Data liefert neueste zuerst — wir brauchen aeltester zuerst fuer pandas-ta
        result.reverse()
        return result

    except Exception as e:
        logger.warning("twelvedata.request_failed", symbol=symbol, error=str(e))
        return None


def fetch_quote(symbol: str) -> dict | None:
    """Realtime-Kurs (oder letzter Kurs). Returns {price, change, change_pct, volume}."""
    if not settings.twelvedata_api_key:
        return None
    if _is_rate_limited():
        return None

    base, exchange = _parse_symbol(symbol)
    params = {
        "symbol": base,
        "apikey": settings.twelvedata_api_key,
    }
    if exchange:
        params["exchange"] = exchange

    try:
        resp = httpx.get(f"{BASE_URL}/quote", params=params, timeout=10)
        _increment_counter()
        data = resp.json()

        if data.get("status") == "error":
            return None

        return {
            "price": float(data.get("close", 0)),
            "open": float(data.get("open", 0)) if data.get("open") else None,
            "high": float(data.get("high", 0)) if data.get("high") else None,
            "low": float(data.get("low", 0)) if data.get("low") else None,
            "prev_close": float(data.get("previous_close", 0)) if data.get("previous_close") else None,
            "change": float(data.get("change", 0)) if data.get("change") else 0,
            "change_pct": float(data.get("percent_change", 0)) if data.get("percent_change") else 0,
            "volume": int(float(data.get("volume", 0))) if data.get("volume") else 0,
            "source": "twelvedata",
        }
    except Exception as e:
        logger.warning("twelvedata.quote_failed", symbol=symbol, error=str(e))
        return None


def fetch_ticker_info(symbol: str) -> dict:
    """Hole Ticker-Metadaten (Name, Sektor, etc.)."""
    if not settings.twelvedata_api_key:
        return {}
    if _is_rate_limited():
        return {}

    base, exchange = _parse_symbol(symbol)
    params = {
        "symbol": base,
        "apikey": settings.twelvedata_api_key,
    }
    if exchange:
        params["exchange"] = exchange

    try:
        resp = httpx.get(f"{BASE_URL}/profile", params=params, timeout=10)
        _increment_counter()
        data = resp.json()
        if data.get("status") == "error":
            return {}
        return {
            "name": data.get("name"),
            "sector": data.get("sector"),
            "industry": data.get("industry"),
            "exchange": data.get("exchange"),
            "country": data.get("country"),
        }
    except Exception:
        return {}
