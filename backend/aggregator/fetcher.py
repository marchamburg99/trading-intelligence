import math
import structlog
import pandas as pd
import pandas_ta as ta
from aggregator.yf_session import yf_safe_ticker
from aggregator import twelvedata
from datetime import date, timedelta
from sqlalchemy.orm import Session

from core.models import Ticker, OHLCVData, Indicator

logger = structlog.get_logger()


def safe_float(val):
    """Konvertiere numpy/pandas Werte zu Python float, None bei NaN."""
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _period_to_days(period: str) -> int:
    mapping = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825}
    return mapping.get(period, 365)


def _fetch_from_twelvedata(symbol: str, period: str, db: Session) -> bool:
    """Primaer-Provider: Twelve Data."""
    days = _period_to_days(period)
    values = twelvedata.fetch_time_series(symbol, days=days)
    if not values:
        return False

    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        info = twelvedata.fetch_ticker_info(symbol)
        ticker = Ticker(
            symbol=symbol,
            name=info.get("name") or symbol,
            sector=info.get("sector"),
            industry=info.get("industry"),
            exchange=info.get("exchange"),
            country=info.get("country"),
        )
        db.add(ticker)
        db.flush()

    for v in values:
        existing = (
            db.query(OHLCVData)
            .filter(OHLCVData.ticker_id == ticker.id, OHLCVData.date == v["date"])
            .first()
        )
        if existing:
            continue
        ohlcv = OHLCVData(
            ticker_id=ticker.id,
            date=v["date"],
            open=v["open"],
            high=v["high"],
            low=v["low"],
            close=v["close"],
            adj_close=v["close"],
            volume=v["volume"],
        )
        db.add(ohlcv)

    db.commit()
    return True


def _fetch_from_yfinance(symbol: str, period: str, db: Session) -> bool:
    """Fallback-Provider: yfinance."""
    try:
        ticker_obj = yf_safe_ticker(symbol)
        hist = ticker_obj.history(period=period)
    except Exception as e:
        logger.warning("yfinance_history_failed", symbol=symbol, error=str(e))
        return False

    if hist.empty:
        return False

    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        try:
            info = ticker_obj.info
        except Exception:
            info = {}
        ticker = Ticker(
            symbol=symbol,
            name=info.get("longName") or info.get("shortName") or symbol,
            sector=info.get("sector"),
            industry=info.get("industry"),
            market_cap=safe_float(info.get("marketCap")),
            exchange=info.get("exchange"),
            country=info.get("country"),
        )
        db.add(ticker)
        db.flush()

    for idx, row in hist.iterrows():
        trade_date = idx.date()
        existing = (
            db.query(OHLCVData)
            .filter(OHLCVData.ticker_id == ticker.id, OHLCVData.date == trade_date)
            .first()
        )
        if existing:
            continue

        ohlcv = OHLCVData(
            ticker_id=ticker.id,
            date=trade_date,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            adj_close=float(row.get("Adj Close", row["Close"])),
            volume=int(row["Volume"]),
        )
        db.add(ohlcv)

    db.commit()
    return True


def fetch_and_store_ohlcv(symbol: str, db: Session, period: str = "1y") -> bool:
    """Lade OHLCV-Daten. Provider-Kette: Twelve Data -> yfinance."""
    if twelvedata.is_available():
        try:
            if _fetch_from_twelvedata(symbol, period, db):
                logger.info("ohlcv.fetched", symbol=symbol, source="twelvedata")
                return True
        except Exception as e:
            logger.warning("twelvedata_fetch_failed", symbol=symbol, error=str(e))

    try:
        if _fetch_from_yfinance(symbol, period, db):
            logger.info("ohlcv.fetched", symbol=symbol, source="yfinance")
            return True
    except Exception as e:
        logger.warning("yfinance_fetch_failed", symbol=symbol, error=str(e))

    return False


def compute_indicators(symbol: str, db: Session) -> bool:
    """Berechne technische Indikatoren und speichere in DB."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        return False

    ohlcv_data = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(OHLCVData.date)
        .all()
    )

    if len(ohlcv_data) < 200:
        return False

    df = pd.DataFrame([
        {
            "date": d.date,
            "open": float(d.open),
            "high": float(d.high),
            "low": float(d.low),
            "close": float(d.close),
            "volume": float(d.volume) if d.volume else 0,
        }
        for d in ohlcv_data
    ])
    df.set_index("date", inplace=True)

    # Technische Indikatoren berechnen
    df["rsi_14"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd"] = macd.iloc[:, 0]
    df["macd_signal"] = macd.iloc[:, 1]
    df["macd_histogram"] = macd.iloc[:, 2]
    df["ema_21"] = ta.ema(df["close"], length=21)
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    bbands = ta.bbands(df["close"], length=20)
    df["bb_upper"] = bbands.iloc[:, 2]
    df["bb_middle"] = bbands.iloc[:, 1]
    df["bb_lower"] = bbands.iloc[:, 0]
    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["obv"] = ta.obv(df["close"], df["volume"])
    stoch = ta.stoch(df["high"], df["low"], df["close"])
    df["stoch_k"] = stoch.iloc[:, 0]
    df["stoch_d"] = stoch.iloc[:, 1]

    # Nur letzte 30 Tage speichern/aktualisieren
    recent = df.tail(30)
    for idx, row in recent.iterrows():
        existing = (
            db.query(Indicator)
            .filter(Indicator.ticker_id == ticker.id, Indicator.date == idx)
            .first()
        )
        if existing:
            continue

        ind = Indicator(
            ticker_id=ticker.id,
            date=idx,
            rsi_14=safe_float(row.get("rsi_14")),
            macd=safe_float(row.get("macd")),
            macd_signal=safe_float(row.get("macd_signal")),
            macd_histogram=safe_float(row.get("macd_histogram")),
            ema_21=safe_float(row.get("ema_21")),
            ema_50=safe_float(row.get("ema_50")),
            ema_200=safe_float(row.get("ema_200")),
            bb_upper=safe_float(row.get("bb_upper")),
            bb_middle=safe_float(row.get("bb_middle")),
            bb_lower=safe_float(row.get("bb_lower")),
            atr_14=safe_float(row.get("atr_14")),
            obv=safe_float(row.get("obv")),
            stoch_k=safe_float(row.get("stoch_k")),
            stoch_d=safe_float(row.get("stoch_d")),
        )
        db.add(ind)

    db.commit()
    return True
