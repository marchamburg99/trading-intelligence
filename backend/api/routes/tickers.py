from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from core.database import get_db
from core.models import Ticker, OHLCVData, Indicator

router = APIRouter()


@router.get("/")
def list_tickers(
    sector: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(Ticker).filter(Ticker.is_active == True)
    if sector:
        query = query.filter(Ticker.sector == sector)
    if search:
        query = query.filter(
            Ticker.symbol.ilike(f"%{search}%") | Ticker.name.ilike(f"%{search}%")
        )
    return query.order_by(Ticker.symbol).limit(limit).all()


@router.get("/{symbol}")
def get_ticker_detail(symbol: str, db: Session = Depends(get_db)):
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        return {"error": "Ticker nicht gefunden"}

    ohlcv = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(desc(OHLCVData.date))
        .limit(250)
        .all()
    )

    indicators = (
        db.query(Indicator)
        .filter(Indicator.ticker_id == ticker.id)
        .order_by(desc(Indicator.date))
        .first()
    )

    return {
        "ticker": {
            "symbol": ticker.symbol,
            "name": ticker.name,
            "sector": ticker.sector,
            "industry": ticker.industry,
            "market_cap": float(ticker.market_cap) if ticker.market_cap else None,
            "exchange": ticker.exchange,
        },
        "ohlcv": [
            {
                "date": d.date.isoformat(),
                "open": float(d.open),
                "high": float(d.high),
                "low": float(d.low),
                "close": float(d.close),
                "volume": float(d.volume) if d.volume else 0,
            }
            for d in reversed(ohlcv)
        ],
        "indicators": {
            "rsi_14": indicators.rsi_14,
            "macd": indicators.macd,
            "macd_signal": indicators.macd_signal,
            "ema_21": indicators.ema_21,
            "ema_50": indicators.ema_50,
            "ema_200": indicators.ema_200,
            "bb_upper": indicators.bb_upper,
            "bb_lower": indicators.bb_lower,
            "atr_14": indicators.atr_14,
            "stoch_k": indicators.stoch_k,
            "stoch_d": indicators.stoch_d,
        }
        if indicators
        else None,
    }
