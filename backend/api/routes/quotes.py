from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Watchlist, Ticker, Signal, JournalEntry
from aggregator.realtime import get_realtime_quote, get_bulk_quotes

router = APIRouter()


@router.get("/{symbol}")
def get_quote(symbol: str):
    quote = get_realtime_quote(symbol.upper(), priority=True)
    if not quote:
        return {"error": "Kein Kurs verfügbar"}
    return {"symbol": symbol.upper(), **quote}


@router.get("/")
def get_all_quotes(db: Session = Depends(get_db)):
    """Realtime-Kurse für alle Watchlist-Ticker. Offene Positionen haben Priorität."""
    watchlist = db.query(Watchlist).join(Ticker).all()
    symbols = [w.ticker.symbol for w in watchlist]

    # Priority: offene Positionen + Top-Signale
    open_trades = db.query(JournalEntry).filter(JournalEntry.is_closed == False).all()
    priority = {t.symbol for t in open_trades}

    # Top 10 Signale auch als Priority
    top_signals = (
        db.query(Signal).join(Ticker)
        .filter(Signal.is_active == True)
        .order_by(Signal.confidence.desc())
        .limit(10)
        .all()
    )
    priority.update(s.ticker.symbol for s in top_signals)

    quotes = get_bulk_quotes(symbols, priority_symbols=priority)
    return quotes
