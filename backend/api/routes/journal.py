from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

from core.database import get_db
from core.models import JournalEntry

router = APIRouter()


class JournalCreate(BaseModel):
    symbol: str
    trade_date: date
    direction: str  # LONG, SHORT
    entry_price: float
    position_size: int
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_type: Optional[str] = None
    notes: Optional[str] = None


class JournalClose(BaseModel):
    exit_price: float
    lessons: Optional[str] = None


class JournalUpdate(BaseModel):
    entry_price: Optional[float] = None
    position_size: Optional[int] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_type: Optional[str] = None
    notes: Optional[str] = None
    lessons: Optional[str] = None
    direction: Optional[str] = None


@router.get("/")
def get_journal(
    is_closed: Optional[bool] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    query = db.query(JournalEntry)
    if is_closed is not None:
        query = query.filter(JournalEntry.is_closed == is_closed)
    entries = query.order_by(desc(JournalEntry.trade_date)).limit(limit).all()
    return [
        {
            "id": e.id,
            "symbol": e.symbol,
            "trade_date": e.trade_date.isoformat(),
            "direction": e.direction,
            "entry_price": float(e.entry_price) if e.entry_price else None,
            "exit_price": float(e.exit_price) if e.exit_price else None,
            "position_size": e.position_size,
            "pnl": float(e.pnl) if e.pnl else None,
            "pnl_percent": e.pnl_percent,
            "setup_type": e.setup_type,
            "is_closed": e.is_closed,
            "notes": e.notes,
            "lessons": e.lessons,
        }
        for e in entries
    ]


@router.post("/")
def create_journal_entry(entry: JournalCreate, db: Session = Depends(get_db)):
    je = JournalEntry(
        symbol=entry.symbol.upper(),
        trade_date=entry.trade_date,
        direction=entry.direction,
        entry_price=entry.entry_price,
        position_size=entry.position_size,
        stop_loss=entry.stop_loss,
        take_profit=entry.take_profit,
        setup_type=entry.setup_type,
        notes=entry.notes,
    )
    db.add(je)
    db.commit()
    return {"id": je.id, "status": "created"}


@router.post("/{entry_id}/close")
def close_trade(entry_id: int, close: JournalClose, db: Session = Depends(get_db)):
    je = db.query(JournalEntry).get(entry_id)
    if not je:
        raise HTTPException(404, "Eintrag nicht gefunden")
    if je.is_closed:
        raise HTTPException(400, "Trade bereits geschlossen")

    je.exit_price = close.exit_price
    je.is_closed = True
    je.closed_at = datetime.utcnow()
    je.lessons = close.lessons

    if je.entry_price and je.position_size:
        entry = float(je.entry_price)
        multiplier = 1 if je.direction == "LONG" else -1
        je.pnl = (close.exit_price - entry) * je.position_size * multiplier
        je.pnl_percent = ((close.exit_price - entry) / entry) * 100 * multiplier

    db.commit()
    return {"id": je.id, "pnl": float(je.pnl) if je.pnl else 0}


@router.put("/{entry_id}")
def update_journal_entry(entry_id: int, update: JournalUpdate, db: Session = Depends(get_db)):
    je = db.query(JournalEntry).get(entry_id)
    if not je:
        raise HTTPException(404, "Eintrag nicht gefunden")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(je, field, value)

    # P&L neu berechnen falls Trade geschlossen und Preise geändert
    if je.is_closed and je.entry_price and je.exit_price and je.position_size:
        entry = float(je.entry_price)
        exit_p = float(je.exit_price)
        multiplier = 1 if je.direction == "LONG" else -1
        je.pnl = (exit_p - entry) * je.position_size * multiplier
        je.pnl_percent = ((exit_p - entry) / entry) * 100 * multiplier

    db.commit()
    return {"id": je.id, "status": "updated"}


@router.delete("/{entry_id}")
def delete_journal_entry(entry_id: int, db: Session = Depends(get_db)):
    je = db.query(JournalEntry).get(entry_id)
    if not je:
        raise HTTPException(404, "Eintrag nicht gefunden")
    db.delete(je)
    db.commit()
    return {"id": entry_id, "status": "deleted"}


@router.get("/performance")
def get_performance(db: Session = Depends(get_db)):
    """Equity-Kurve und Performance-Metriken aus Journal-Daten."""
    closed = (
        db.query(JournalEntry)
        .filter(JournalEntry.is_closed == True)
        .order_by(JournalEntry.closed_at)
        .all()
    )

    if not closed:
        return {"equity_curve": [], "monthly": [], "by_setup": []}

    # Equity-Kurve
    equity = 100000.0  # Start-Kapital
    curve = [{"date": closed[0].trade_date.isoformat(), "equity": equity}]
    peak = equity
    max_dd = 0.0

    for trade in closed:
        pnl = float(trade.pnl) if trade.pnl else 0
        equity += pnl
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
        curve.append({
            "date": (trade.closed_at or trade.trade_date).isoformat()[:10],
            "equity": round(equity, 2),
            "pnl": round(pnl, 2),
            "symbol": trade.symbol,
        })

    # Monats-Performance
    monthly = {}
    for trade in closed:
        month = (trade.closed_at or trade.trade_date).strftime("%Y-%m")
        if month not in monthly:
            monthly[month] = {"month": month, "trades": 0, "pnl": 0, "wins": 0}
        monthly[month]["trades"] += 1
        pnl = float(trade.pnl) if trade.pnl else 0
        monthly[month]["pnl"] += pnl
        if pnl > 0:
            monthly[month]["wins"] += 1

    monthly_list = sorted(monthly.values(), key=lambda x: x["month"])
    for m in monthly_list:
        m["pnl"] = round(m["pnl"], 2)
        m["win_rate"] = round(m["wins"] / m["trades"] * 100, 1) if m["trades"] > 0 else 0

    # Performance by Setup-Type
    by_setup = {}
    for trade in closed:
        setup = trade.setup_type or "Unbekannt"
        if setup not in by_setup:
            by_setup[setup] = {"setup": setup, "trades": 0, "pnl": 0, "wins": 0}
        by_setup[setup]["trades"] += 1
        pnl = float(trade.pnl) if trade.pnl else 0
        by_setup[setup]["pnl"] += pnl
        if pnl > 0:
            by_setup[setup]["wins"] += 1

    setup_list = sorted(by_setup.values(), key=lambda x: x["pnl"], reverse=True)
    for s in setup_list:
        s["pnl"] = round(s["pnl"], 2)
        s["win_rate"] = round(s["wins"] / s["trades"] * 100, 1) if s["trades"] > 0 else 0

    return {
        "equity_curve": curve,
        "final_equity": round(equity, 2),
        "max_drawdown": round(max_dd * 100, 2),
        "monthly": monthly_list,
        "by_setup": setup_list,
    }


@router.get("/stats")
def get_journal_stats(db: Session = Depends(get_db)):
    closed = db.query(JournalEntry).filter(JournalEntry.is_closed == True).all()
    if not closed:
        return {"total_trades": 0}

    wins = [e for e in closed if e.pnl and float(e.pnl) > 0]
    losses = [e for e in closed if e.pnl and float(e.pnl) <= 0]
    total_pnl = sum(float(e.pnl) for e in closed if e.pnl)

    return {
        "total_trades": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": len(wins) / len(closed) * 100 if closed else 0,
        "total_pnl": total_pnl,
        "avg_pnl": total_pnl / len(closed) if closed else 0,
        "best_trade": max((float(e.pnl) for e in closed if e.pnl), default=0),
        "worst_trade": min((float(e.pnl) for e in closed if e.pnl), default=0),
    }
