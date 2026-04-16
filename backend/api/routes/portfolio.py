"""Portfolio: persistente Positionen mit CRUD + Analyse."""
import csv
import io
import json
from datetime import datetime
import redis
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from core.config import get_settings
from core.database import get_db
from core.models import (
    Ticker, Signal, Indicator, OHLCVData, Watchlist, PortfolioHolding,
)
from core.portfolio import get_current_capital
from core.products import is_leveraged, get_product_info, is_eu_tradeable, get_ucits_alternative, get_trade_republic_url
from aggregator.currency import get_ticker_currency, get_currency_symbol

settings = get_settings()
redis_client = redis.from_url(settings.redis_url)
router = APIRouter()

PORTFOLIO_ALERTS_KEY = "portfolio_alerts"
PORTFOLIO_ALERTS_TTL = 86400


# ============================================================
# Analyse-Logik (shared zwischen CRUD und Celery-Task)
# ============================================================

def analyze_position(holding: PortfolioHolding, db: Session, capital: float) -> dict:
    """Analysiere eine persistente Position gegen aktive Signale."""
    symbol = holding.symbol.upper().strip()
    shares = float(holding.shares)
    entry_price = float(holding.entry_price) if holding.entry_price else 0

    result = {
        "id": holding.id,
        "symbol": symbol,
        "shares": shares,
        "entry_price": entry_price,
        "notes": holding.notes,
        "position_value": round(shares * entry_price, 2),
    }

    ccy = get_ticker_currency(symbol)
    result["currency"] = ccy
    result["currency_symbol"] = get_currency_symbol(ccy)
    result["eu_tradeable"] = is_eu_tradeable(symbol)
    result["ucits_alternative"] = get_ucits_alternative(symbol)
    result["trade_republic"] = get_trade_republic_url(symbol)

    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()

    # Fallback: unbekannten Ticker auto-enrollen in Watchlist
    if not ticker:
        try:
            ticker = Ticker(symbol=symbol, name=symbol)
            db.add(ticker)
            db.flush()
            existing_wl = db.query(Watchlist).filter(Watchlist.ticker_id == ticker.id).first()
            if not existing_wl:
                db.add(Watchlist(ticker_id=ticker.id, notes="Auto via Portfolio"))
            db.commit()
        except Exception:
            db.rollback()

        pos_val = shares * entry_price
        concentration = (pos_val / capital * 100) if capital > 0 else 0
        result.update({
            "current_value": pos_val,
            "concentration": round(concentration, 1),
            "status": "NO_DATA",
            "action": "REDUZIEREN" if concentration > 25 else "BEOBACHTEN",
            "reason": f"{symbol}: Kursdaten werden nachgeladen. Bei grosser Konzentration ({concentration:.0f}%) Position pruefen.",
        })
        return result

    result["name"] = ticker.name
    result["sector"] = ticker.sector

    last_ohlcv = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(desc(OHLCVData.date))
        .first()
    )
    current_price = float(last_ohlcv.close) if last_ohlcv else None
    result["current_price"] = current_price

    if current_price:
        result["unrealized_pnl"] = round((current_price - entry_price) * shares, 2)
        result["unrealized_pct"] = round(((current_price - entry_price) / entry_price) * 100, 2) if entry_price else 0
        result["current_value"] = round(current_price * shares, 2)
        result["concentration"] = round(current_price * shares / capital * 100, 1) if capital > 0 else 0
    else:
        result["unrealized_pnl"] = 0
        result["unrealized_pct"] = 0
        result["current_value"] = result["position_value"]
        result["concentration"] = 0

    signal = (
        db.query(Signal)
        .filter(Signal.ticker_id == ticker.id, Signal.is_active == True)
        .order_by(desc(Signal.confidence))
        .first()
    )

    if not signal:
        try:
            from signals.engine import generate_signal
            signal = generate_signal(symbol, db, capital)
        except Exception:
            signal = None

    if not signal:
        result["status"] = "NO_SIGNAL"
        result["action"] = "BEOBACHTEN"
        result["reason"] = f"Kein Signal fuer {symbol} berechenbar."
        result["confidence"] = None
        result["signal_type"] = None
        return result

    result["signal_type"] = signal.signal_type.value
    result["confidence"] = signal.confidence
    result["data_quality"] = signal.data_quality
    result["risk_rating"] = signal.risk_rating
    result["stop_loss"] = float(signal.stop_loss) if signal.stop_loss else None
    result["take_profit"] = float(signal.take_profit) if signal.take_profit else None
    result["risk_reward_ratio"] = signal.risk_reward_ratio
    result["reasoning"] = signal.reasoning

    ind = (
        db.query(Indicator)
        .filter(Indicator.ticker_id == ticker.id)
        .order_by(desc(Indicator.date))
        .first()
    )
    if ind:
        result["rsi"] = ind.rsi_14
        result["above_ema200"] = (current_price > ind.ema_200) if current_price and ind.ema_200 else None

    sig_type = signal.signal_type.value
    conf = signal.confidence
    pnl_pct = result.get("unrealized_pct", 0)
    sl = result.get("stop_loss")
    tp = result.get("take_profit")

    if sig_type == "BUY" and conf >= 68:
        action = "AUFSTOCKEN" if pnl_pct < -5 else "HALTEN"
        reason = (f"BUY-Signal ({conf:.0f}%) — Position im Minus ({pnl_pct:+.1f}%), Nachkauf erwaegen."
                  if pnl_pct < -5 else f"BUY-Signal ({conf:.0f}%) — Position laeuft, halten.")
    elif sig_type == "HOLD":
        if conf >= 60:
            action, reason = "HALTEN", f"HOLD-Signal ({conf:.0f}%) — nahe am Kaufsignal."
        elif conf >= 50:
            action, reason = "HALTEN", f"HOLD-Signal ({conf:.0f}%) — neutral, beobachten."
        else:
            action, reason = "REDUZIEREN", f"Schwaches HOLD ({conf:.0f}%) — Teilverkauf erwaegen."
    elif sig_type == "SELL":
        action = "VERKAUFEN"
        reason = (f"SELL-Signal ({conf:.0f}%) — Gewinne mitnehmen ({pnl_pct:+.1f}%)."
                  if pnl_pct > 0 else f"SELL-Signal ({conf:.0f}%) — Verluste begrenzen.")
    elif sig_type == "AVOID":
        action, reason = "SOFORT_VERKAUFEN", f"AVOID-Signal ({conf:.0f}%) — sofort verkaufen."
    else:
        action, reason = "BEOBACHTEN", f"Signal: {sig_type} ({conf:.0f}%)"

    if current_price and sl and current_price <= sl * 1.05:
        action = "STOP_LOSS"
        reason = f"ACHTUNG: Kurs (${current_price:.2f}) nahe Stop-Loss (${sl:.2f})!"
    elif current_price and tp and current_price >= tp * 0.95:
        reason += f" Take-Profit (${tp:.2f}) fast erreicht."

    result["action"] = action
    result["reason"] = reason
    return result


def analyze_all_holdings(db: Session) -> dict:
    """Analysiere alle persistenten Portfolio-Positionen."""
    capital = get_current_capital(db)
    holdings = db.query(PortfolioHolding).order_by(PortfolioHolding.id).all()
    results = [analyze_position(h, db, capital) for h in holdings]

    total_value = sum(r.get("current_value", 0) for r in results)
    total_pnl = sum(r.get("unrealized_pnl", 0) for r in results)

    sector_alloc = {}
    for r in results:
        sec = r.get("sector") or "Unbekannt"
        sector_alloc[sec] = sector_alloc.get(sec, 0) + r.get("current_value", 0)

    actions = {}
    for r in results:
        a = r.get("action", "BEOBACHTEN")
        actions[a] = actions.get(a, 0) + 1

    return {
        "portfolio_capital": capital,
        "total_positions": len(results),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / total_value * 100, 2) if total_value > 0 else 0,
        "action_summary": actions,
        "sector_allocation": {
            k: round(v / total_value * 100, 1) if total_value > 0 else 0
            for k, v in sector_alloc.items()
        },
        "positions": results,
    }


# ============================================================
# CRUD Endpoints
# ============================================================

class HoldingCreate(BaseModel):
    symbol: str
    shares: float
    entry_price: float
    notes: str | None = None


class HoldingUpdate(BaseModel):
    shares: float | None = None
    entry_price: float | None = None
    notes: str | None = None


class BulkReplace(BaseModel):
    positions: list[HoldingCreate]


@router.get("/")
def get_portfolio(db: Session = Depends(get_db)):
    """Alle persistenten Positionen + Analyse."""
    return analyze_all_holdings(db)


@router.get("/holdings")
def list_holdings(db: Session = Depends(get_db)):
    """Rohe Holdings-Liste ohne Analyse."""
    holdings = db.query(PortfolioHolding).order_by(PortfolioHolding.id).all()
    return [
        {
            "id": h.id,
            "symbol": h.symbol,
            "shares": float(h.shares),
            "entry_price": float(h.entry_price),
            "notes": h.notes,
            "last_action": h.last_action,
            "last_check_at": h.last_check_at.isoformat() if h.last_check_at else None,
        }
        for h in holdings
    ]


@router.post("/holdings")
def add_holding(data: HoldingCreate, db: Session = Depends(get_db)):
    h = PortfolioHolding(
        symbol=data.symbol.upper().strip(),
        shares=data.shares,
        entry_price=data.entry_price,
        notes=data.notes,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id, "status": "created"}


@router.put("/holdings/{holding_id}")
def update_holding(holding_id: int, data: HoldingUpdate, db: Session = Depends(get_db)):
    h = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not h:
        raise HTTPException(404, "Nicht gefunden")
    if data.shares is not None:
        h.shares = data.shares
    if data.entry_price is not None:
        h.entry_price = data.entry_price
    if data.notes is not None:
        h.notes = data.notes
    db.commit()
    return {"status": "updated"}


@router.delete("/holdings/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    h = db.query(PortfolioHolding).filter(PortfolioHolding.id == holding_id).first()
    if not h:
        raise HTTPException(404, "Nicht gefunden")
    db.delete(h)
    db.commit()
    return {"status": "deleted"}


@router.post("/holdings/bulk")
def bulk_replace(data: BulkReplace, db: Session = Depends(get_db)):
    """Loescht alle bestehenden Holdings und ersetzt sie durch die neuen."""
    db.query(PortfolioHolding).delete()
    for p in data.positions:
        db.add(PortfolioHolding(
            symbol=p.symbol.upper().strip(),
            shares=p.shares,
            entry_price=p.entry_price,
            notes=p.notes,
        ))
    db.commit()
    return {"status": "replaced", "count": len(data.positions)}


@router.post("/holdings/csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """CSV-Upload (comdirect-Format oder einfach). Ersetzt alle bestehenden Holdings."""
    content = (await file.read()).decode("utf-8-sig")
    lines = content.strip().split("\n")
    positions: list[HoldingCreate] = []

    def _parse_de_num(s: str) -> float:
        return float(s.replace(".", "").replace(",", ".")) if s else 0

    if ";" in lines[0]:
        reader = csv.reader(lines, delimiter=";")
        header_found = False
        header = []
        for row in reader:
            if not row:
                continue
            row_lower = [c.strip().lower() for c in row]
            if any(k in " ".join(row_lower) for k in ["wkn", "isin", "bezeichnung", "stück"]):
                header_found = True
                header = row_lower
                continue
            if not header_found or len(row) < 3:
                continue
            try:
                symbol = shares = price = None
                for i, h in enumerate(header):
                    val = row[i].strip() if i < len(row) else ""
                    if "wkn" in h or "symbol" in h or "ticker" in h:
                        symbol = val
                    elif "stück" in h or "stueck" in h or "nom" in h:
                        shares = _parse_de_num(val)
                    elif "kurs" in h or "preis" in h or "ausführung" in h:
                        price = _parse_de_num(val)
                if symbol and shares and shares > 0:
                    positions.append(HoldingCreate(
                        symbol=symbol, shares=shares, entry_price=price or 0
                    ))
            except (ValueError, IndexError):
                continue
    else:
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace("\t", " ").split()
            if len(parts) >= 2:
                try:
                    positions.append(HoldingCreate(
                        symbol=parts[0].upper(),
                        shares=_parse_de_num(parts[1]),
                        entry_price=_parse_de_num(parts[2]) if len(parts) >= 3 else 0,
                    ))
                except ValueError:
                    continue

    if not positions:
        raise HTTPException(400, "Keine Positionen erkannt")

    return bulk_replace(BulkReplace(positions=positions), db)


# ============================================================
# Alerts
# ============================================================

@router.get("/alerts")
def get_alerts():
    raw = redis_client.get(PORTFOLIO_ALERTS_KEY)
    return json.loads(raw) if raw else []


@router.delete("/alerts")
def clear_alerts():
    redis_client.delete(PORTFOLIO_ALERTS_KEY)
    return {"status": "cleared"}
