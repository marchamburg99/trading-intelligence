from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from core.database import get_db
from core.models import Signal, Ticker, SignalType

router = APIRouter()


@router.get("/")
def get_signals(
    signal_type: Optional[SignalType] = None,
    min_confidence: float = Query(0, ge=0, le=100),
    sector: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Signal).join(Ticker).filter(Signal.is_active == True)

    if signal_type:
        query = query.filter(Signal.signal_type == signal_type)
    if min_confidence > 0:
        query = query.filter(Signal.confidence >= min_confidence)
    if sector:
        query = query.filter(Ticker.sector == sector)

    signals = query.order_by(desc(Signal.confidence)).limit(limit).all()

    return [
        {
            "id": s.id,
            "symbol": s.ticker.symbol,
            "name": s.ticker.name,
            "sector": s.ticker.sector,
            "date": s.date.isoformat(),
            "signal_type": s.signal_type.value,
            "confidence": s.confidence,
            "entry_price": float(s.entry_price) if s.entry_price else None,
            "stop_loss": float(s.stop_loss) if s.stop_loss else None,
            "take_profit": float(s.take_profit) if s.take_profit else None,
            "risk_reward_ratio": s.risk_reward_ratio,
            "position_size": s.position_size,
            "risk_rating": s.risk_rating,
            "expected_hold_days": s.expected_hold_days,
            "reasoning": s.reasoning,
            "ta_score": s.ta_score,
            "fundamental_score": s.fundamental_score,
            "sentiment_score": s.sentiment_score_val,
            "macro_score": s.macro_score,
        }
        for s in signals
    ]


@router.get("/top")
def get_top_signals(limit: int = Query(10, le=50), db: Session = Depends(get_db)):
    signals = (
        db.query(Signal)
        .join(Ticker)
        .filter(Signal.is_active == True)
        .order_by(desc(Signal.confidence))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": s.id,
            "symbol": s.ticker.symbol,
            "name": s.ticker.name,
            "sector": s.ticker.sector,
            "date": s.date.isoformat(),
            "signal_type": s.signal_type.value,
            "confidence": s.confidence,
            "entry_price": float(s.entry_price) if s.entry_price else None,
            "stop_loss": float(s.stop_loss) if s.stop_loss else None,
            "take_profit": float(s.take_profit) if s.take_profit else None,
            "risk_reward_ratio": s.risk_reward_ratio,
            "position_size": s.position_size,
            "risk_rating": s.risk_rating,
            "expected_hold_days": s.expected_hold_days,
            "reasoning": s.reasoning,
            "ta_score": s.ta_score,
            "fundamental_score": s.fundamental_score,
            "sentiment_score": s.sentiment_score_val,
            "macro_score": s.macro_score,
        }
        for s in signals
    ]


@router.get("/{symbol}")
def get_signal_for_symbol(symbol: str, db: Session = Depends(get_db)):
    signal = (
        db.query(Signal)
        .join(Ticker)
        .filter(Ticker.symbol == symbol.upper(), Signal.is_active == True)
        .order_by(desc(Signal.date))
        .first()
    )
    if not signal:
        return {"error": "Kein aktives Signal gefunden"}

    return {
        "symbol": signal.ticker.symbol,
        "name": signal.ticker.name,
        "date": signal.date.isoformat(),
        "signal_type": signal.signal_type.value,
        "confidence": signal.confidence,
        "entry_price": float(signal.entry_price) if signal.entry_price else None,
        "stop_loss": float(signal.stop_loss) if signal.stop_loss else None,
        "take_profit": float(signal.take_profit) if signal.take_profit else None,
        "risk_reward_ratio": signal.risk_reward_ratio,
        "position_size": signal.position_size,
        "risk_rating": signal.risk_rating,
        "expected_hold_days": signal.expected_hold_days,
        "reasoning": signal.reasoning,
    }
