"""Discovery API: Proaktive Markt-Vorschlaege."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from core.models import DiscoverySuggestion, Ticker, Watchlist

router = APIRouter()


@router.get("/suggestions")
def get_suggestions(
    source: str | None = Query(None, description="Filter: hedge_fund_cluster, sector_momentum, technical_setup, combined"),
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(DiscoverySuggestion).filter(
        DiscoverySuggestion.discovery_score >= min_score
    )
    if source:
        query = query.filter(DiscoverySuggestion.source == source)

    suggestions = query.order_by(desc(DiscoverySuggestion.discovery_score)).limit(limit).all()

    return {
        "count": len(suggestions),
        "updated_at": suggestions[0].created_at.isoformat() if suggestions else None,
        "suggestions": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "sector": s.sector,
                "score": s.discovery_score,
                "scores": {
                    "hedge_fund": s.hedge_fund_score,
                    "technical": s.technical_score,
                    "sector": s.sector_score,
                },
                "source": s.source,
                "reason": s.reason,
                "fund_count": s.fund_count,
                "fund_names": s.fund_names,
                "current_price": float(s.current_price) if s.current_price else None,
                "rsi": s.rsi_14,
            }
            for s in suggestions
        ],
    }


@router.post("/suggestions/{symbol}/add-to-watchlist")
def add_to_watchlist(symbol: str, db: Session = Depends(get_db)):
    """Discovery-Vorschlag zur Watchlist hinzufuegen und Daten-Fetch triggern."""
    symbol = symbol.upper()

    # Pruefen ob bereits auf Watchlist
    existing = (
        db.query(Watchlist)
        .join(Ticker)
        .filter(Ticker.symbol == symbol)
        .first()
    )
    if existing:
        raise HTTPException(400, f"{symbol} ist bereits auf der Watchlist")

    # Ticker anlegen falls noetig
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        ticker = Ticker(symbol=symbol, name=symbol)
        db.add(ticker)
        db.flush()

    watchlist_entry = Watchlist(ticker_id=ticker.id, notes="Via Discovery hinzugefuegt")
    db.add(watchlist_entry)
    db.commit()

    # OHLCV-Fetch + Indikator-Berechnung async triggern
    try:
        from aggregator.tasks import fetch_ticker_data
        fetch_ticker_data.delay(symbol)
    except Exception:
        pass

    return {"status": "added", "symbol": symbol, "ticker_id": ticker.id}
