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

# US-ETFs die in EU fuer Privatanleger NICHT direkt kaufbar sind (PRIIPs-Verordnung)
# Mapping auf UCITS-Aequivalente die bei Trade Republic, Scalable etc. handelbar sind
US_ETF_TO_UCITS = {
    # Broad Market
    "SPY":  {"ucits": "SXR8.DE", "name": "iShares Core S&P 500 UCITS"},
    "VOO":  {"ucits": "SXR8.DE", "name": "iShares Core S&P 500 UCITS"},
    "IVV":  {"ucits": "SXR8.DE", "name": "iShares Core S&P 500 UCITS"},
    "QQQ":  {"ucits": "SXRV.DE", "name": "Invesco Nasdaq-100 UCITS"},
    "IWM":  {"ucits": "XRS2.DE", "name": "Xtrackers Russell 2000 UCITS"},
    "DIA":  {"ucits": "EXI2.DE", "name": "iShares Dow Jones Industrial UCITS"},
    # International
    "VGK":  {"ucits": "EXSA.DE", "name": "iShares STOXX Europe 600 UCITS"},
    "EEM":  {"ucits": "IEMM.DE", "name": "iShares MSCI EM UCITS"},
    # Sector ETFs (SPDR Select Sector)
    "XLK":  {"ucits": "QDVE.DE", "name": "iShares S&P 500 Info Tech UCITS"},
    "XLF":  {"ucits": "QDVH.DE", "name": "iShares S&P 500 Financials UCITS"},
    "XLV":  {"ucits": "QDVG.DE", "name": "iShares S&P 500 Health Care UCITS"},
    "XLE":  {"ucits": "QDVI.DE", "name": "iShares S&P 500 Energy UCITS"},
    "XLI":  {"ucits": "QDVB.DE", "name": "iShares S&P 500 Industrials UCITS"},
    "XLP":  {"ucits": "QDVD.DE", "name": "iShares S&P 500 Consumer Staples UCITS"},
    "XLY":  {"ucits": "QDVK.DE", "name": "iShares S&P 500 Consumer Discret. UCITS"},
    "XLU":  {"ucits": "QDVF.DE", "name": "iShares S&P 500 Utilities UCITS"},
    "XLC":  {"ucits": "QDVX.DE", "name": "iShares S&P 500 Communication UCITS"},
    "XLRE": {"ucits": "IUSP.DE", "name": "iShares US Property Yield UCITS"},
    "XLB":  {"ucits": "QDVJ.DE", "name": "iShares S&P 500 Materials UCITS"},
    "SOXX": {"ucits": "SXRS.DE", "name": "iShares Semiconductor UCITS"},
    # Commodities
    "USO":  {"ucits": "OD7F.DE", "name": "WisdomTree WTI Crude Oil"},
    "UNG":  {"ucits": "OD7U.DE", "name": "WisdomTree Natural Gas"},
    "DBA":  {"ucits": "OD7L.DE", "name": "WisdomTree Agriculture"},
    "COPX": {"ucits": "2B7K.DE", "name": "Global X Copper Miners UCITS"},
    "GDX":  {"ucits": "IE3G.DE", "name": "iShares Gold Producers UCITS"},
    "XBI":  {"ucits": "IBBB.DE", "name": "iShares Nasdaq US Biotech UCITS"},
    # Crypto
    "IBIT": {"ucits": "BTCE.DE", "name": "BTCetc Physical Bitcoin ETP"},
    "ETHA": {"ucits": "ZETH.DE", "name": "21Shares Ethereum ETP"},
}

# Leveraged ETFs sind in EU komplett verboten fuer Retail
US_LEVERAGED_NOT_EU_TRADEABLE = set(LEVERAGED_PRODUCTS.keys())


def is_eu_tradeable(symbol: str) -> bool:
    """True wenn der Ticker fuer EU-Privatanleger direkt kaufbar ist."""
    sym = symbol.upper()
    # Leveraged ETFs: komplett verboten in EU
    if sym in US_LEVERAGED_NOT_EU_TRADEABLE:
        return False
    # US-ETFs: nicht direkt kaufbar
    if sym in US_ETF_TO_UCITS:
        return False
    return True


def get_ucits_alternative(symbol: str) -> dict | None:
    """UCITS-Aequivalent fuer US-ETF."""
    return US_ETF_TO_UCITS.get(symbol.upper())


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
