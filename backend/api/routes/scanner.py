from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, func
from typing import Optional

from core.database import get_db
from core.models import Ticker, Indicator, Signal

router = APIRouter()


@router.get("/")
def scan_stocks(
    rsi_below: Optional[float] = Query(None, description="RSI unter diesem Wert (oversold)"),
    rsi_above: Optional[float] = Query(None, description="RSI über diesem Wert (overbought)"),
    above_ema200: Optional[bool] = Query(None, description="Kurs über EMA200"),
    macd_bullish: Optional[bool] = Query(None, description="MACD > Signal"),
    min_confidence: Optional[float] = Query(None, description="Mindest-Konfidenz aktives Signal"),
    sector: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Ticker, Indicator)
        .join(Indicator, and_(Indicator.ticker_id == Ticker.id))
        .filter(Ticker.is_active == True)
    )

    if rsi_below is not None:
        query = query.filter(Indicator.rsi_14 < rsi_below)
    if rsi_above is not None:
        query = query.filter(Indicator.rsi_14 > rsi_above)
    if macd_bullish is True:
        query = query.filter(Indicator.macd > Indicator.macd_signal)
    if macd_bullish is False:
        query = query.filter(Indicator.macd < Indicator.macd_signal)
    if sector:
        query = query.filter(Ticker.sector == sector)

    # Nur den neuesten Indikator pro Ticker
    subq = (
        db.query(Indicator.ticker_id, func.max(Indicator.date).label("max_date"))
        .group_by(Indicator.ticker_id)
        .subquery()
    )
    query = query.filter(
        and_(Indicator.ticker_id == subq.c.ticker_id, Indicator.date == subq.c.max_date)
    )

    results = query.limit(limit).all()

    output = []
    for ticker, ind in results:
        item = {
            "symbol": ticker.symbol,
            "name": ticker.name,
            "sector": ticker.sector,
            "rsi_14": ind.rsi_14,
            "macd": ind.macd,
            "macd_signal": ind.macd_signal,
            "ema_21": ind.ema_21,
            "ema_50": ind.ema_50,
            "ema_200": ind.ema_200,
            "atr_14": ind.atr_14,
        }

        if above_ema200 is not None and ind.ema_200:
            # Filter client-side (braucht close-Preis, der im Indicator nicht direkt ist)
            pass

        output.append(item)

    return output
