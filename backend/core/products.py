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
# Mapping auf UCITS-Aequivalente mit ISIN fuer Trade Republic Deep-Links
US_ETF_TO_UCITS = {
    # Broad Market
    "SPY":  {"ucits": "SXR8.DE", "isin": "IE00B5BMR087", "name": "iShares Core S&P 500 UCITS"},
    "VOO":  {"ucits": "SXR8.DE", "isin": "IE00B5BMR087", "name": "iShares Core S&P 500 UCITS"},
    "IVV":  {"ucits": "SXR8.DE", "isin": "IE00B5BMR087", "name": "iShares Core S&P 500 UCITS"},
    "QQQ":  {"ucits": "SXRV.DE", "isin": "IE00B53SZB19", "name": "Invesco Nasdaq-100 UCITS"},
    "IWM":  {"ucits": "XRS2.DE", "isin": "IE00BJZ2DD79", "name": "Xtrackers Russell 2000 UCITS"},
    "DIA":  {"ucits": "EXI2.DE", "isin": "DE000A0D8Q31", "name": "iShares Dow Jones Industrial UCITS"},
    # International
    "VGK":  {"ucits": "EXSA.DE", "isin": "DE0002635307", "name": "iShares STOXX Europe 600 UCITS"},
    "EEM":  {"ucits": "IEMM.DE", "isin": "IE00B0M63177", "name": "iShares MSCI EM UCITS"},
    # Sector ETFs (SPDR Select Sector)
    "XLK":  {"ucits": "QDVE.DE", "isin": "IE00BM67HT60", "name": "iShares S&P 500 Info Tech UCITS"},
    "XLF":  {"ucits": "QDVH.DE", "isin": "IE00B4JNQZ49", "name": "iShares S&P 500 Financials UCITS"},
    "XLV":  {"ucits": "QDVG.DE", "isin": "IE00B43HR379", "name": "iShares S&P 500 Health Care UCITS"},
    "XLE":  {"ucits": "QDVI.DE", "isin": "IE00B42NKQ00", "name": "iShares S&P 500 Energy UCITS"},
    "XLI":  {"ucits": "QDVB.DE", "isin": "IE00B4LN9N13", "name": "iShares S&P 500 Industrials UCITS"},
    "XLP":  {"ucits": "QDVD.DE", "isin": "IE00B40B8R38", "name": "iShares S&P 500 Consumer Staples UCITS"},
    "XLY":  {"ucits": "QDVK.DE", "isin": "IE00B4MCHD36", "name": "iShares S&P 500 Consumer Discret. UCITS"},
    "XLU":  {"ucits": "QDVF.DE", "isin": "IE00B4KBBD01", "name": "iShares S&P 500 Utilities UCITS"},
    "XLC":  {"ucits": "QDVX.DE", "isin": "IE00BDDRDW15", "name": "iShares S&P 500 Communication UCITS"},
    "XLRE": {"ucits": "IUSP.DE", "isin": "IE00B1FZS244", "name": "iShares US Property Yield UCITS"},
    "XLB":  {"ucits": "QDVJ.DE", "isin": "IE00B4MJ5D07", "name": "iShares S&P 500 Materials UCITS"},
    "SOXX": {"ucits": "SXRS.DE", "isin": "IE00B3WJKG14", "name": "iShares MSCI USA Momentum UCITS"},
    # Commodities
    "USO":  {"ucits": "OD7F.DE", "isin": "JE00B78CGV99", "name": "WisdomTree WTI Crude Oil"},
    "UNG":  {"ucits": "OD7U.DE", "isin": "JE00B6XF1L81", "name": "WisdomTree Natural Gas"},
    "DBA":  {"ucits": "OD7L.DE", "isin": "JE00B8JVMF97", "name": "WisdomTree Agriculture"},
    "COPX": {"ucits": "2B7K.DE", "isin": "IE00BM67HN09", "name": "Global X Copper Miners UCITS"},
    "GDX":  {"ucits": "IE3G.DE", "isin": "IE00B6R52036", "name": "VanEck Gold Miners UCITS"},
    "XBI":  {"ucits": "IBBB.DE", "isin": "IE00BYXG2H39", "name": "iShares Nasdaq US Biotech UCITS"},
    # Crypto
    "IBIT": {"ucits": "BTCE.DE", "isin": "DE000A27Z304", "name": "BTCetc Physical Bitcoin ETP"},
    "ETHA": {"ucits": "ZETH.DE", "isin": "CH1146882820", "name": "21Shares Ethereum ETP"},
}

# Bekannte ISINs fuer Einzelaktien (fuer Trade Republic Deep-Links)
# yfinance liefert ISIN via ticker.isin, aber das ist im Docker blocked.
# Hier die wichtigsten manuell gemappt:
SYMBOL_TO_ISIN = {
    # US Tech
    "AAPL": "US0378331005", "MSFT": "US5949181045", "GOOGL": "US02079K3059",
    "GOOG": "US02079K1079", "META": "US30303M1027", "AMZN": "US0231351067",
    "NVDA": "US67066G1040", "TSLA": "US88160R1014", "NFLX": "US64110L1061",
    "CRM": "US79466L3024", "ORCL": "US68389X1054", "ADBE": "US00724F1012",
    "INTC": "US4581401001", "AMD": "US0079031078", "CSCO": "US17275R1023",
    # US Finance/Healthcare/Consumer
    "JPM": "US46625H1005", "BAC": "US0605051046", "WFC": "US9497461015",
    "GS": "US38141G1040", "MS": "US6174464486", "BLK": "US09247X1019",
    "V": "US92826C8394", "MA": "US57636Q1040", "JNJ": "US4781601046",
    "UNH": "US91324P1021", "PFE": "US7170811035", "MRK": "US58933Y1055",
    "ABBV": "US00287Y1091", "LLY": "US5324571083", "WMT": "US9311421039",
    "PG": "US7427181091", "KO": "US1912161007", "PEP": "US7134481081",
    "MCD": "US5801351017", "NKE": "US6541061031", "DIS": "US2546871060",
    "COST": "US22160K1051", "HD": "US4370761029", "BABA": "US01609W1027",
    "ISRG": "US46120E6023", "BP": "GB0007980591",
    # DAX / EU
    "SAP.DE": "DE0007164600", "SIE.DE": "DE0007236101", "ALV.DE": "DE0008404005",
    "DTE.DE": "DE0005557508", "BAS.DE": "DE000BASF111", "BAYN.DE": "DE000BAY0017",
    "BMW.DE": "DE0005190003", "DAI.DE": "DE0007100000", "DBK.DE": "DE0005140008",
    "DHL.DE": "DE0005552004", "DPW.DE": "DE0005552004", "DTG.DE": "DE000TRAT0N7",
    "EOAN.DE": "DE000ENAG999", "FME.DE": "DE0005785802", "HEI.DE": "DE0006047004",
    "IFX.DE": "DE0006231004", "LIN.DE": "IE000S9YS762", "MBG.DE": "DE0007100000",
    "MRK.DE": "DE0006599905", "MTX.DE": "DE000A0D9PT0", "MUV2.DE": "DE0008430026",
    "PAH3.DE": "DE000PAH0038", "P911.DE": "DE000PAG9113", "QIA.DE": "NL0000240000",
    "RWE.DE": "DE0007037129", "SRT3.DE": "DE0007165631", "VNA.DE": "DE000A1ML7J1",
    "VOW3.DE": "DE0007664039", "ZAL.DE": "DE000ZAL1111", "ADE.DE": "DE0005500001",
    # France
    "AIR.PA": "NL0000235190", "TTE.PA": "FR0000120271", "OR.PA": "FR0000120321",
    "MC.PA": "FR0000121014", "BNP.PA": "FR0000131104", "AI.PA": "FR0000120073",
    "SAN.PA": "FR0000120578", "SU.PA": "FR0000121972", "RI.PA": "FR0000130577",
    # Switzerland
    "NESN.SW": "CH0038863350", "NOVN.SW": "CH0012005267", "ROG.SW": "CH0012032048",
    # UK
    "HSBA.L": "GB0005405286", "BP.L": "GB0007980591", "GSK.L": "GB00BN7SWP63",
    "AZN.L": "GB0009895292", "ULVR.L": "GB00B10RZP78",
    # iShares Core / Xetra ETFs
    "IQQH.DE": "IE00BMDPBZ72", "CSPX.L": "IE00B5BMR087",
}


def get_isin(symbol: str) -> str | None:
    """ISIN fuer Trade Republic Deep-Link."""
    sym = symbol.upper()
    # UCITS-Alternative zuerst
    ucits = US_ETF_TO_UCITS.get(sym)
    if ucits:
        return ucits.get("isin")
    return SYMBOL_TO_ISIN.get(sym)


def get_trade_republic_url(symbol: str) -> dict:
    """Trade Republic Deep-Link + Fallback-Such-URL.

    Returns:
        {"url": "https://...", "type": "direct"|"search", "isin": "..."|None}
    """
    sym = symbol.upper()
    # Fuer US-ETFs: UCITS-Alternative nutzen
    ucits = US_ETF_TO_UCITS.get(sym)
    if ucits and ucits.get("isin"):
        return {
            "url": f"https://app.traderepublic.com/stocks/{ucits['isin']}/chart",
            "type": "ucits",
            "isin": ucits["isin"],
            "symbol": ucits["ucits"],
        }

    isin = SYMBOL_TO_ISIN.get(sym)
    if isin:
        return {
            "url": f"https://app.traderepublic.com/stocks/{isin}/chart",
            "type": "direct",
            "isin": isin,
            "symbol": sym,
        }

    # Fallback: Such-URL
    return {
        "url": f"https://app.traderepublic.com/search?q={sym}",
        "type": "search",
        "isin": None,
        "symbol": sym,
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
