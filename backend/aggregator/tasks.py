from core.celery_app import app
from core.database import SessionLocal
from core.models import Watchlist, Ticker
from aggregator.fetcher import fetch_and_store_ohlcv, compute_indicators
import structlog

logger = structlog.get_logger()


@app.task(name="aggregator.tasks.fetch_watchlist_data")
def fetch_watchlist_data():
    """Alle 15 Min: Daten für Watchlist-Titel abrufen und Indikatoren berechnen."""
    db = SessionLocal()
    try:
        watchlist = db.query(Watchlist).join(Ticker).all()
        symbols = [w.ticker.symbol for w in watchlist]

        for symbol in symbols:
            try:
                fetch_and_store_ohlcv(symbol, db, period="3mo")
                compute_indicators(symbol, db)
                logger.info("aggregator.fetched", symbol=symbol)
            except Exception as e:
                logger.error("aggregator.fetch_failed", symbol=symbol, error=str(e))
    finally:
        db.close()


@app.task(name="aggregator.tasks.fetch_ticker_data")
def fetch_ticker_data(symbol: str):
    """On-Demand: Daten für einzelnen Ticker abrufen."""
    db = SessionLocal()
    try:
        fetch_and_store_ohlcv(symbol, db)
        compute_indicators(symbol, db)
        logger.info("aggregator.fetched_single", symbol=symbol)
    finally:
        db.close()
