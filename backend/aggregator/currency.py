"""Währungserkennung + EUR-Umrechnung mit Redis-Cache."""
import structlog
from aggregator.yf_session import yf_safe_ticker
import redis
import json
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

CACHE_TTL = 3600  # 1 Stunde

# Ticker-Suffix → Währung
SUFFIX_CURRENCY = {
    ".DE": "EUR",
    ".PA": "EUR",
    ".AS": "EUR",
    ".MI": "EUR",
    ".MC": "EUR",
    ".BR": "EUR",
    ".HE": "EUR",
    ".IR": "EUR",
    ".SW": "CHF",
    ".L": "GBP",
    ".TO": "CAD",
    ".AX": "AUD",
    ".HK": "HKD",
    ".T": "JPY",
}

# Forex-Paare für Umrechnung nach EUR (Yahoo Finance Format)
FOREX_TO_EUR = {
    "USD": "EURUSD=X",  # 1 EUR = X USD → Preis / Rate = EUR
    "CHF": "EURCHF=X",
    "GBP": "EURGBP=X",
    "CAD": "EURCAD=X",
    "AUD": "EURAUD=X",
    "HKD": "EURHKD=X",
    "JPY": "EURJPY=X",
}


def get_ticker_currency(symbol: str) -> str:
    """Bestimme die Währung eines Tickers anhand des Suffixes."""
    for suffix, currency in SUFFIX_CURRENCY.items():
        if symbol.upper().endswith(suffix):
            return currency
    return "USD"  # Default: US-Aktien


def get_exchange_rate(from_currency: str) -> float | None:
    """Hole Wechselkurs von from_currency nach EUR. Cached in Redis."""
    if from_currency == "EUR":
        return 1.0

    cache_key = f"fx:{from_currency}_EUR"
    cached = redis_client.get(cache_key)
    if cached:
        val = cached.decode() if isinstance(cached, bytes) else str(cached)
        if val == "FAILED":
            return None
        return float(val)

    pair = FOREX_TO_EUR.get(from_currency)
    if not pair:
        return None

    try:
        ticker = yf_safe_ticker(pair)
        rate = ticker.fast_info.get("lastPrice")
        if rate and rate > 0:
            redis_client.setex(cache_key, CACHE_TTL, str(rate))
            return float(rate)
    except Exception as e:
        logger.warning("exchange_rate_fetch_failed", pair=pair, error=str(e))

    # Negative cache: fehlgeschlagene Lookups 5 Min nicht wiederholen
    redis_client.setex(cache_key, 300, "FAILED")
    return None


def convert_to_eur(price: float, from_currency: str) -> float | None:
    """Konvertiere einen Preis in EUR."""
    if from_currency == "EUR":
        return price

    rate = get_exchange_rate(from_currency)
    if rate is None or rate == 0:
        return None

    return round(price / rate, 2)


CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "CHF": "CHF ",
    "GBP": "£",
    "CAD": "C$",
    "AUD": "A$",
    "JPY": "¥",
    "HKD": "HK$",
}


def get_currency_symbol(currency: str) -> str:
    return CURRENCY_SYMBOLS.get(currency, currency + " ")
