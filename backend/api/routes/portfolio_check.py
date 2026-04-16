"""Portfolio-Check: Bestehendes Portfolio analysieren lassen."""
import csv
import io
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel

from core.database import get_db
from core.models import Ticker, Signal, Indicator, OHLCVData
from core.portfolio import get_current_capital
from core.products import is_leveraged, get_product_info
from aggregator.currency import get_ticker_currency, get_currency_symbol

router = APIRouter()


class PortfolioPosition(BaseModel):
    symbol: str
    shares: float
    entry_price: float


class PortfolioCheckRequest(BaseModel):
    positions: list[PortfolioPosition]


def _analyze_position(pos: PortfolioPosition, db: Session, capital: float) -> dict:
    """Analysiere eine einzelne Position gegen aktive Signale."""
    symbol = pos.symbol.upper().strip()
    result = {
        "symbol": symbol,
        "shares": pos.shares,
        "entry_price": pos.entry_price,
        "position_value": round(pos.shares * pos.entry_price, 2),
    }

    # Waehrung
    ccy = get_ticker_currency(symbol)
    result["currency"] = ccy
    result["currency_symbol"] = get_currency_symbol(ccy)

    # Ticker + aktueller Kurs aus DB
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()

    # Fallback: unbekannten Ticker automatisch via yfinance anlegen + OHLCV laden
    if not ticker:
        try:
            from aggregator.fetcher import fetch_and_store_ohlcv, compute_indicators
            if fetch_and_store_ohlcv(symbol, db, period="1y"):
                compute_indicators(symbol, db)
                ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
        except Exception:
            pass

    if not ticker:
        # Minimal-Analyse ohne Kursdaten: nur Konzentrations-Check
        pos_val = pos.shares * pos.entry_price
        concentration = (pos_val / capital * 100) if capital > 0 else 0
        result["current_value"] = pos_val
        result["concentration"] = round(concentration, 1)
        result["status"] = "NO_DATA"
        if concentration > 25:
            result["action"] = "REDUZIEREN"
            result["reason"] = f"{symbol}: Keine Kursdaten, aber {concentration:.0f}% Konzentration — zu gross, Position verkleinern."
        else:
            result["action"] = "BEOBACHTEN"
            result["reason"] = f"{symbol}: Keine Kursdaten verfuegbar (yfinance blockiert). Zur Watchlist hinzufuegen fuer Analyse."
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
        result["unrealized_pnl"] = round((current_price - pos.entry_price) * pos.shares, 2)
        result["unrealized_pct"] = round(((current_price - pos.entry_price) / pos.entry_price) * 100, 2)
        result["current_value"] = round(current_price * pos.shares, 2)
        result["concentration"] = round(current_price * pos.shares / capital * 100, 1) if capital > 0 else 0
    else:
        result["unrealized_pnl"] = 0
        result["unrealized_pct"] = 0
        result["current_value"] = result["position_value"]
        result["concentration"] = 0

    # Aktives Signal
    signal = (
        db.query(Signal)
        .filter(Signal.ticker_id == ticker.id, Signal.is_active == True)
        .order_by(desc(Signal.confidence))
        .first()
    )

    # Kein aktives Signal: on-the-fly generieren
    if not signal:
        try:
            from signals.engine import generate_signal
            signal = generate_signal(symbol, db, capital)
        except Exception:
            signal = None

    if not signal:
        result["status"] = "NO_SIGNAL"
        result["action"] = "BEOBACHTEN"
        result["reason"] = f"Kein Signal fuer {symbol} berechenbar (zu wenig Daten)."
        result["confidence"] = None
        result["signal_type"] = None
        return result

    result["signal_type"] = signal.signal_type.value
    result["confidence"] = signal.confidence
    result["data_quality"] = signal.data_quality
    result["risk_rating"] = signal.risk_rating
    result["entry_signal"] = float(signal.entry_price) if signal.entry_price else None
    result["stop_loss"] = float(signal.stop_loss) if signal.stop_loss else None
    result["take_profit"] = float(signal.take_profit) if signal.take_profit else None
    result["risk_reward_ratio"] = signal.risk_reward_ratio
    result["reasoning"] = signal.reasoning

    # Indikatoren
    ind = (
        db.query(Indicator)
        .filter(Indicator.ticker_id == ticker.id)
        .order_by(desc(Indicator.date))
        .first()
    )
    if ind:
        result["rsi"] = ind.rsi_14
        result["above_ema200"] = (current_price > ind.ema_200) if current_price and ind.ema_200 else None

    # Handlungsempfehlung ableiten
    sig_type = signal.signal_type.value
    conf = signal.confidence
    pnl_pct = result.get("unrealized_pct", 0)
    sl = result.get("stop_loss")
    tp = result.get("take_profit")

    if sig_type == "BUY" and conf >= 68:
        if pnl_pct < -5:
            action = "AUFSTOCKEN"
            reason = f"BUY-Signal ({conf:.0f}%) — Position im Minus ({pnl_pct:+.1f}%), Nachkauf erwaegen bei unveraenderter These."
        else:
            action = "HALTEN"
            reason = f"BUY-Signal ({conf:.0f}%) — Position laeuft, Signal bestaetigt Halten."
    elif sig_type == "HOLD":
        if conf >= 60:
            action = "HALTEN"
            reason = f"HOLD-Signal ({conf:.0f}%) — nahe am Kaufsignal. Position halten."
        elif conf >= 50:
            action = "HALTEN"
            reason = f"HOLD-Signal ({conf:.0f}%) — neutral. Beobachten, kein Handlungsbedarf."
        else:
            action = "REDUZIEREN"
            reason = f"Schwaches HOLD ({conf:.0f}%) — Teilverkauf erwaegen, Position reduzieren."
    elif sig_type == "SELL":
        if pnl_pct > 0:
            action = "VERKAUFEN"
            reason = f"SELL-Signal ({conf:.0f}%) — Gewinne mitnehmen ({pnl_pct:+.1f}%). Position schliessen."
        else:
            action = "VERKAUFEN"
            reason = f"SELL-Signal ({conf:.0f}%) — Verluste begrenzen ({pnl_pct:+.1f}%). Position schliessen."
    elif sig_type == "AVOID":
        action = "SOFORT_VERKAUFEN"
        reason = f"AVOID-Signal ({conf:.0f}%) — sofort verkaufen, hohes Risiko."
    else:
        action = "BEOBACHTEN"
        reason = f"Signal: {sig_type} ({conf:.0f}%)"

    # SL/TP Warnung
    if current_price and sl and current_price <= sl * 1.05:
        action = "STOP_LOSS"
        reason = f"ACHTUNG: Kurs (${current_price:.2f}) nahe Stop-Loss (${sl:.2f})! Sofort pruefen."
    elif current_price and tp and current_price >= tp * 0.95:
        reason += f" Take-Profit (${tp:.2f}) fast erreicht — Gewinnmitnahme pruefen."

    result["action"] = action
    result["reason"] = reason

    return result


@router.post("/check")
def check_portfolio(req: PortfolioCheckRequest, db: Session = Depends(get_db)):
    """Analysiere ein bestehendes Portfolio gegen aktive Signale."""
    capital = get_current_capital(db)
    results = [_analyze_position(p, db, capital) for p in req.positions]

    total_value = sum(r.get("current_value", 0) for r in results)
    total_pnl = sum(r.get("unrealized_pnl", 0) for r in results)

    # Sektor-Konzentration
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
        "sector_allocation": {k: round(v / total_value * 100, 1) if total_value > 0 else 0 for k, v in sector_alloc.items()},
        "positions": results,
    }


@router.post("/check/csv")
async def check_portfolio_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Portfolio aus CSV importieren und analysieren. Unterstuetzt comdirect-Format und einfaches Format."""
    content = (await file.read()).decode("utf-8-sig")
    lines = content.strip().split("\n")

    positions = []

    # Format erkennen: comdirect (Semicolon, viele Spalten) oder einfach (Symbol,Shares,Price)
    if ";" in lines[0]:
        # comdirect-Format: ueberspringe Header-Zeilen bis Spaltenheader
        reader = csv.reader(lines, delimiter=";")
        header_found = False
        for row in reader:
            if not row:
                continue
            # Suche nach Spaltenheader
            row_lower = [c.strip().lower() for c in row]
            if any(k in " ".join(row_lower) for k in ["wkn", "isin", "bezeichnung", "stück"]):
                header_found = True
                header = row_lower
                continue
            if not header_found:
                continue
            if len(row) < 3:
                continue

            # Versuche Symbol/WKN und Stueckzahl zu extrahieren
            try:
                symbol = None
                shares = None
                price = None
                for i, h in enumerate(header):
                    val = row[i].strip() if i < len(row) else ""
                    if "wkn" in h or "symbol" in h or "ticker" in h:
                        symbol = val
                    elif "stück" in h or "stueck" in h or "nom" in h or "anzahl" in h:
                        shares = float(val.replace(".", "").replace(",", "."))
                    elif "kurs" in h or "preis" in h or "ausführung" in h:
                        price = float(val.replace(".", "").replace(",", "."))
                if symbol and shares and shares > 0:
                    positions.append(PortfolioPosition(
                        symbol=symbol, shares=shares, entry_price=price or 0
                    ))
            except (ValueError, IndexError):
                continue
    else:
        # Einfaches Format: Symbol,Shares,Price oder Symbol Shares Price
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace(",", " ").replace("\t", " ").split()
            if len(parts) >= 2:
                try:
                    symbol = parts[0].upper()
                    shares = float(parts[1])
                    price = float(parts[2]) if len(parts) >= 3 else 0
                    if shares > 0:
                        positions.append(PortfolioPosition(
                            symbol=symbol, shares=shares, entry_price=price
                        ))
                except ValueError:
                    continue

    if not positions:
        return {"error": "Keine Positionen erkannt. Format: Symbol Stueckzahl Kaufkurs (pro Zeile)"}

    req = PortfolioCheckRequest(positions=positions)
    return check_portfolio(req, db)
