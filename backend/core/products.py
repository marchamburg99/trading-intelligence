"""Produkt-Registry: Leveraged ETFs, Crypto ETFs, Commodity ETFs."""

LEVERAGED_PRODUCTS = {
    "TQQQ": {"leverage": 3, "direction": "LONG", "underlying": "QQQ", "name": "3x Nasdaq 100"},
    "SPXL": {"leverage": 3, "direction": "LONG", "underlying": "SPY", "name": "3x S&P 500"},
    "UPRO": {"leverage": 3, "direction": "LONG", "underlying": "SPY", "name": "3x S&P 500"},
    "SOXL": {"leverage": 3, "direction": "LONG", "underlying": "SOXX", "name": "3x Semiconductors"},
    "TNA":  {"leverage": 3, "direction": "LONG", "underlying": "IWM", "name": "3x Russell 2000"},
    "FAS":  {"leverage": 3, "direction": "LONG", "underlying": "XLF", "name": "3x Financials"},
    "LABU": {"leverage": 3, "direction": "LONG", "underlying": "XBI", "name": "3x Biotech"},
    "NUGT": {"leverage": 2, "direction": "LONG", "underlying": "GDX", "name": "2x Gold Miners"},
    "JNUG": {"leverage": 2, "direction": "LONG", "underlying": "GDXJ", "name": "2x Jr. Gold Miners"},
    "BOIL": {"leverage": 2, "direction": "LONG", "underlying": "UNG", "name": "2x Natural Gas"},
    "SQQQ": {"leverage": 3, "direction": "SHORT", "underlying": "QQQ", "name": "3x Inverse Nasdaq"},
    "SPXS": {"leverage": 3, "direction": "SHORT", "underlying": "SPY", "name": "3x Inverse S&P 500"},
    "SOXS": {"leverage": 3, "direction": "SHORT", "underlying": "SOXX", "name": "3x Inverse Semis"},
    "TZA":  {"leverage": 3, "direction": "SHORT", "underlying": "IWM", "name": "3x Inverse Russell"},
    "FAZ":  {"leverage": 3, "direction": "SHORT", "underlying": "XLF", "name": "3x Inverse Financials"},
    "KOLD": {"leverage": 2, "direction": "SHORT", "underlying": "UNG", "name": "2x Inverse Gas"},
    "UVXY": {"leverage": 1.5, "direction": "LONG", "underlying": "VIX", "name": "1.5x VIX"},
    "SVXY": {"leverage": 0.5, "direction": "SHORT", "underlying": "VIX", "name": "0.5x Inverse VIX"},
}

CRYPTO_ETFS = {"IBIT": "Bitcoin ETF", "ETHA": "Ethereum ETF"}
COMMODITY_ETFS = {"USO": "Crude Oil", "COPX": "Copper Miners", "UNG": "Natural Gas", "DBA": "Agriculture"}

ALL_SPECIAL_SYMBOLS = set(LEVERAGED_PRODUCTS) | set(CRYPTO_ETFS) | set(COMMODITY_ETFS)


def is_leveraged(symbol: str) -> bool:
    return symbol in LEVERAGED_PRODUCTS


def get_leverage(symbol: str) -> float:
    info = LEVERAGED_PRODUCTS.get(symbol)
    return info["leverage"] if info else 1.0


def get_product_info(symbol: str) -> dict | None:
    if symbol in LEVERAGED_PRODUCTS:
        return {**LEVERAGED_PRODUCTS[symbol], "type": "leveraged"}
    if symbol in CRYPTO_ETFS:
        return {"leverage": 1, "direction": "LONG", "name": CRYPTO_ETFS[symbol], "type": "crypto"}
    if symbol in COMMODITY_ETFS:
        return {"leverage": 1, "direction": "LONG", "name": COMMODITY_ETFS[symbol], "type": "commodity"}
    return None
