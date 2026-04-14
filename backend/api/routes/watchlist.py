from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from core.models import Watchlist, Ticker, OHLCVData, Indicator, Signal

router = APIRouter()


class WatchlistAdd(BaseModel):
    symbol: str
    notes: Optional[str] = None
    alert_price_above: Optional[float] = None
    alert_price_below: Optional[float] = None


@router.get("/")
def get_watchlist(db: Session = Depends(get_db)):
    entries = db.query(Watchlist).join(Ticker).all()
    result = []
    for w in entries:
        # Letzter Preis + Vortag
        prices = (
            db.query(OHLCVData)
            .filter(OHLCVData.ticker_id == w.ticker.id)
            .order_by(desc(OHLCVData.date))
            .limit(2)
            .all()
        )
        price = None
        change = None
        if prices:
            price = round(float(prices[0].close), 2)
            if len(prices) >= 2:
                prev = float(prices[1].close)
                change = round(((price - prev) / prev) * 100, 2)

        # Letzter Indikator
        ind = (
            db.query(Indicator)
            .filter(Indicator.ticker_id == w.ticker.id)
            .order_by(desc(Indicator.date))
            .first()
        )

        # Aktives Signal
        signal = (
            db.query(Signal)
            .filter(Signal.ticker_id == w.ticker.id, Signal.is_active == True)
            .order_by(desc(Signal.date))
            .first()
        )

        result.append({
            "id": w.id,
            "symbol": w.ticker.symbol,
            "name": w.ticker.name,
            "sector": w.ticker.sector,
            "price": price,
            "change_1d": change,
            "rsi": round(ind.rsi_14, 1) if ind and ind.rsi_14 else None,
            "macd_bullish": (ind.macd > ind.macd_signal) if ind and ind.macd and ind.macd_signal else None,
            "above_ema200": (price > ind.ema_200) if price and ind and ind.ema_200 else None,
            "atr": round(ind.atr_14, 2) if ind and ind.atr_14 else None,
            "signal_type": signal.signal_type.value if signal else None,
            "confidence": signal.confidence if signal else None,
            "notes": w.notes,
        })

    result.sort(key=lambda x: x.get("confidence") or 0, reverse=True)
    return result


@router.post("/")
def add_to_watchlist(item: WatchlistAdd, db: Session = Depends(get_db)):
    ticker = db.query(Ticker).filter(Ticker.symbol == item.symbol.upper()).first()
    if not ticker:
        ticker = Ticker(symbol=item.symbol.upper(), is_active=True)
        db.add(ticker)
        db.flush()

    existing = db.query(Watchlist).filter(Watchlist.ticker_id == ticker.id).first()
    if existing:
        raise HTTPException(400, "Symbol bereits auf Watchlist")

    entry = Watchlist(
        ticker_id=ticker.id,
        notes=item.notes,
        alert_price_above=item.alert_price_above,
        alert_price_below=item.alert_price_below,
    )
    db.add(entry)
    db.commit()
    return {"status": "added", "symbol": ticker.symbol}


@router.delete("/{symbol}")
def remove_from_watchlist(symbol: str, db: Session = Depends(get_db)):
    entry = (
        db.query(Watchlist)
        .join(Ticker)
        .filter(Ticker.symbol == symbol.upper())
        .first()
    )
    if not entry:
        raise HTTPException(404, "Symbol nicht auf Watchlist")

    db.delete(entry)
    db.commit()
    return {"status": "removed", "symbol": symbol.upper()}
