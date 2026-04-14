"""Backtest Engine: Simuliert Signal-Engine über historische Daten."""
import math
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import asc

from core.models import Ticker, OHLCVData, Indicator, BacktestResult
from signals.engine import compute_ta_score


def run_backtest(
    symbol: str,
    strategy: str,
    months: int,
    db: Session,
    capital: float = 100000.0,
) -> dict:
    """Führe Backtest für einen Ticker durch."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol.upper()).first()
    if not ticker:
        return {"error": "Ticker nicht gefunden"}

    start_date = date.today() - timedelta(days=months * 30)

    prices = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id, OHLCVData.date >= start_date)
        .order_by(asc(OHLCVData.date))
        .all()
    )

    indicators = (
        db.query(Indicator)
        .filter(Indicator.ticker_id == ticker.id, Indicator.date >= start_date)
        .order_by(asc(Indicator.date))
        .all()
    )

    if len(prices) < 30 or len(indicators) < 30:
        return {"error": "Nicht genügend historische Daten"}

    # Indicator-Lookup by date
    ind_by_date = {ind.date: ind for ind in indicators}

    # Backtest-Simulation
    equity = capital
    peak_equity = capital
    max_drawdown = 0.0
    trades = []
    equity_curve = [{"date": str(start_date), "equity": equity}]

    position = None  # {"entry_price", "shares", "stop_loss", "take_profit", "entry_date"}

    for price in prices:
        close = float(price.close)
        ind = ind_by_date.get(price.date)

        if not ind:
            continue

        # Position-Management
        if position:
            if close <= position["stop_loss"]:
                # Stop-Loss getroffen
                pnl = (close - position["entry_price"]) * position["shares"]
                equity += pnl
                trades.append({
                    "entry_date": str(position["entry_date"]),
                    "exit_date": str(price.date),
                    "entry_price": position["entry_price"],
                    "exit_price": close,
                    "pnl": pnl,
                    "reason": "stop_loss",
                })
                position = None
            elif close >= position["take_profit"]:
                # Take-Profit erreicht
                pnl = (close - position["entry_price"]) * position["shares"]
                equity += pnl
                trades.append({
                    "entry_date": str(position["entry_date"]),
                    "exit_date": str(price.date),
                    "entry_price": position["entry_price"],
                    "exit_price": close,
                    "pnl": pnl,
                    "reason": "take_profit",
                })
                position = None
        else:
            # Signal prüfen
            ta_score, _ = compute_ta_score(ind, close)
            if ta_score >= 65:
                atr = ind.atr_14 or (close * 0.02)
                stop_loss = close - (1.5 * atr)
                take_profit = close + (3.0 * atr)
                risk_per_share = close - stop_loss
                shares = int((equity * 0.02) / risk_per_share) if risk_per_share > 0 else 0

                if shares > 0:
                    position = {
                        "entry_price": close,
                        "shares": shares,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "entry_date": price.date,
                    }

        # Drawdown tracking
        peak_equity = max(peak_equity, equity)
        current_dd = (peak_equity - equity) / peak_equity if peak_equity > 0 else 0
        max_drawdown = max(max_drawdown, current_dd)
        equity_curve.append({"date": str(price.date), "equity": round(equity, 2)})

    # Offene Position zum letzten Kurs schließen
    if position and prices:
        last_close = float(prices[-1].close)
        pnl = (last_close - position["entry_price"]) * position["shares"]
        equity += pnl
        trades.append({
            "entry_date": str(position["entry_date"]),
            "exit_date": str(prices[-1].date),
            "entry_price": position["entry_price"],
            "exit_price": last_close,
            "pnl": pnl,
            "reason": "end_of_period",
        })

    # Metriken berechnen
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_trades = len(trades)
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    total_return = (equity - capital) / capital * 100

    # Sharpe Ratio (vereinfacht)
    if trades:
        returns = [t["pnl"] / capital for t in trades]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe = (avg_return / std_return) * math.sqrt(252) if std_return > 0 else 0
    else:
        sharpe = 0

    # Ergebnis speichern
    result = BacktestResult(
        symbol=symbol.upper(),
        strategy=strategy,
        start_date=start_date,
        end_date=date.today(),
        total_trades=total_trades,
        win_rate=round(win_rate, 1),
        profit_factor=round(profit_factor, 2),
        max_drawdown=round(max_drawdown * 100, 2),
        sharpe_ratio=round(sharpe, 2),
        total_return=round(total_return, 2),
        equity_curve=equity_curve,
        trade_log=trades,
    )
    db.add(result)
    db.commit()

    return {
        "symbol": symbol.upper(),
        "strategy": strategy,
        "period": f"{months} Monate",
        "total_trades": total_trades,
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 2),
        "total_return": round(total_return, 2),
        "equity_curve": equity_curve,
        "trades": trades,
    }
