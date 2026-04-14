from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from core.models import BacktestResult

router = APIRouter()


class BacktestRequest(BaseModel):
    symbol: str
    strategy: str = "signal_engine"
    months: int = 12


@router.post("/run")
def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    from backtest.engine import run_backtest as execute_backtest

    result = execute_backtest(req.symbol, req.strategy, req.months, db)
    return result


@router.get("/results")
def get_backtest_results(
    symbol: Optional[str] = None,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(BacktestResult)
    if symbol:
        query = query.filter(BacktestResult.symbol == symbol.upper())
    results = query.order_by(BacktestResult.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "strategy": r.strategy,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "end_date": r.end_date.isoformat() if r.end_date else None,
            "total_trades": r.total_trades,
            "win_rate": r.win_rate,
            "profit_factor": r.profit_factor,
            "max_drawdown": r.max_drawdown,
            "sharpe_ratio": r.sharpe_ratio,
            "total_return": r.total_return,
            "equity_curve": r.equity_curve,
        }
        for r in results
    ]
