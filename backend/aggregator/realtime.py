"""Realtime-Kurse: Alpha Vantage (Top-Ticker) + yfinance (Rest)."""
import time
import httpx
import yfinance as yf
import redis
import json
from core.config import get_settings

settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

CACHE_TTL = 60  # 1 Minute Cache


def get_realtime_quote_av(symbol: str) -> dict | None:
    """Echtzeit-Kurs via Alpha Vantage GLOBAL_QUOTE."""
    if not settings.alpha_vantage_api_key:
        return None

    # Rate-Limit Check (max 25/Tag, 5/Min)
    minute_key = f"av_calls:{int(time.time() // 60)}"
    day_key = f"av_calls_day:{time.strftime('%Y-%m-%d')}"
    minute_count = int(redis_client.get(minute_key) or 0)
    day_count = int(redis_client.get(day_key) or 0)

    if minute_count >= 5 or day_count >= 25:
        return None

    try:
        resp = httpx.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": settings.alpha_vantage_api_key,
            },
            timeout=10,
        )
        data = resp.json().get("Global Quote", {})
        if not data:
            return None

        pipe = redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 120)
        pipe.incr(day_key)
        pipe.expire(day_key, 86400)
        pipe.execute()

        return {
            "price": float(data.get("05. price", 0)),
            "open": float(data.get("02. open", 0)),
            "high": float(data.get("03. high", 0)),
            "low": float(data.get("04. low", 0)),
            "volume": int(data.get("06. volume", 0)),
            "prev_close": float(data.get("08. previous close", 0)),
            "change": float(data.get("09. change", 0)),
            "change_pct": float(data.get("10. change percent", "0").replace("%", "")),
            "source": "alphavantage",
        }
    except Exception:
        return None


def get_realtime_quote_yf(symbol: str) -> dict | None:
    """Echtzeit-Kurs via yfinance (fast_info)."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        price = info.get("lastPrice") or info.get("previousClose")
        prev = info.get("previousClose") or price

        if not price:
            return None

        change = price - prev if prev else 0
        change_pct = (change / prev * 100) if prev else 0

        return {
            "price": round(float(price), 2),
            "open": round(float(info.get("open", price)), 2),
            "high": round(float(info.get("dayHigh", price)), 2),
            "low": round(float(info.get("dayLow", price)), 2),
            "volume": int(info.get("lastVolume", 0)),
            "prev_close": round(float(prev), 2),
            "change": round(float(change), 2),
            "change_pct": round(float(change_pct), 2),
            "source": "yfinance",
        }
    except Exception:
        return None


def get_realtime_quote(symbol: str, priority: bool = False) -> dict | None:
    """
    Hole Echtzeit-Kurs mit Redis-Cache.
    priority=True → Alpha Vantage bevorzugt (für offene Positionen + Top-Signale)
    """
    cache_key = f"quote:{symbol}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    quote = None
    if priority:
        quote = get_realtime_quote_av(symbol)

    if not quote:
        quote = get_realtime_quote_yf(symbol)

    if quote:
        redis_client.setex(cache_key, CACHE_TTL, json.dumps(quote))

    return quote


def get_bulk_quotes(symbols: list[str], priority_symbols: set[str] | None = None) -> dict[str, dict]:
    """Hole Kurse für mehrere Symbole. Priority-Symbole via Alpha Vantage."""
    results = {}
    priority_symbols = priority_symbols or set()

    for sym in symbols:
        quote = get_realtime_quote(sym, priority=sym in priority_symbols)
        if quote:
            results[sym] = quote

    return results
