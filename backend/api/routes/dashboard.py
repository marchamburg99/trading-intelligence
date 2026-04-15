"""Trading Desk API — alles was ein Trader auf einen Blick braucht."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, case
from datetime import date

from core.database import get_db
from core.models import (
    Signal, Ticker, OHLCVData, Indicator, MacroData,
    SentimentScore, Watchlist, SignalType, JournalEntry,
)

# Leveraged Products Registry
LEVERAGED_PRODUCTS = {
    # 3x Long
    "TQQQ": {"leverage": 3, "direction": "LONG", "underlying": "QQQ", "name": "3x Nasdaq 100"},
    "SPXL": {"leverage": 3, "direction": "LONG", "underlying": "SPY", "name": "3x S&P 500"},
    "UPRO": {"leverage": 3, "direction": "LONG", "underlying": "SPY", "name": "3x S&P 500"},
    "SOXL": {"leverage": 3, "direction": "LONG", "underlying": "SOXX", "name": "3x Semiconductors"},
    "TNA":  {"leverage": 3, "direction": "LONG", "underlying": "IWM", "name": "3x Russell 2000"},
    "FAS":  {"leverage": 3, "direction": "LONG", "underlying": "XLF", "name": "3x Financials"},
    "LABU": {"leverage": 3, "direction": "LONG", "underlying": "XBI", "name": "3x Biotech"},
    "NUGT": {"leverage": 2, "direction": "LONG", "underlying": "GDX", "name": "2x Gold Miners"},
    "JNUG": {"leverage": 2, "direction": "LONG", "underlying": "GDXJ", "name": "2x Jr. Gold Miners"},
    "BOIL": {"leverage": 2, "direction": "LONG", "underlying": "UNG", "name": "2x Natural Gas"},
    # 3x Short / Inverse
    "SQQQ": {"leverage": 3, "direction": "SHORT", "underlying": "QQQ", "name": "3x Inverse Nasdaq"},
    "SPXS": {"leverage": 3, "direction": "SHORT", "underlying": "SPY", "name": "3x Inverse S&P 500"},
    "SOXS": {"leverage": 3, "direction": "SHORT", "underlying": "SOXX", "name": "3x Inverse Semis"},
    "TZA":  {"leverage": 3, "direction": "SHORT", "underlying": "IWM", "name": "3x Inverse Russell"},
    "FAZ":  {"leverage": 3, "direction": "SHORT", "underlying": "XLF", "name": "3x Inverse Financials"},
    "KOLD": {"leverage": 2, "direction": "SHORT", "underlying": "UNG", "name": "2x Inverse Gas"},
    # Volatility
    "UVXY": {"leverage": 1.5, "direction": "LONG", "underlying": "VIX", "name": "1.5x VIX"},
    "SVXY": {"leverage": 0.5, "direction": "SHORT", "underlying": "VIX", "name": "0.5x Inverse VIX"},
}

CRYPTO_ETFS = {"IBIT": "Bitcoin ETF", "ETHA": "Ethereum ETF"}
COMMODITY_ETFS = {"USO": "Crude Oil", "COPX": "Copper Miners", "UNG": "Natural Gas", "DBA": "Agriculture"}


def _is_leveraged(symbol: str) -> bool:
    return symbol in LEVERAGED_PRODUCTS


def _get_product_info(symbol: str) -> dict | None:
    if symbol in LEVERAGED_PRODUCTS:
        return {**LEVERAGED_PRODUCTS[symbol], "type": "leveraged"}
    if symbol in CRYPTO_ETFS:
        return {"leverage": 1, "direction": "LONG", "name": CRYPTO_ETFS[symbol], "type": "crypto"}
    if symbol in COMMODITY_ETFS:
        return {"leverage": 1, "direction": "LONG", "name": COMMODITY_ETFS[symbol], "type": "commodity"}
    return None


router = APIRouter()


def _serialize_signal(s, capital=100000.0, fx_rates=None):
    from aggregator.currency import get_ticker_currency, get_exchange_rate, get_currency_symbol

    entry = float(s.entry_price) if s.entry_price else 0
    sl = float(s.stop_loss) if s.stop_loss else 0
    tp = float(s.take_profit) if s.take_profit else 0
    risk_per_share = abs(entry - sl) if entry and sl else 0
    reward_per_share = abs(tp - entry) if tp and entry else 0

    symbol = s.ticker.symbol
    product_info = _get_product_info(symbol)
    is_lev = _is_leveraged(symbol)

    risk_pct = 0.01 if is_lev else 0.02
    max_position_pct = 0.10 if is_lev else 0.20  # Max 20% vom Kapital pro Position (10% bei Hebel)

    if risk_per_share > 0:
        adjusted_size = int((capital * risk_pct) / risk_per_share)
    else:
        adjusted_size = int(s.position_size) if s.position_size else 0

    # Volumen-Cap: Position darf max_position_pct des Kapitals nicht ueberschreiten
    if entry > 0 and adjusted_size > 0:
        max_shares = int((capital * max_position_pct) / entry)
        adjusted_size = min(adjusted_size, max(1, max_shares))

    leverage = product_info["leverage"] if product_info else 1
    effective_exposure = round(entry * adjusted_size * leverage, 2)

    # Währung + EUR-Umrechnung (Rate aus Cache oder einmal holen)
    ccy = get_ticker_currency(symbol)
    ccy_symbol = get_currency_symbol(ccy)
    entry_eur = sl_eur = tp_eur = None
    if ccy != "EUR":
        if fx_rates is None:
            fx_rates = {}
        if ccy not in fx_rates:
            fx_rates[ccy] = get_exchange_rate(ccy)
        rate = fx_rates[ccy]
        if rate and rate > 0:
            entry_eur = round(entry / rate, 2) if entry else None
            sl_eur = round(sl / rate, 2) if sl else None
            tp_eur = round(tp / rate, 2) if tp else None

    result = {
        "symbol": symbol,
        "name": s.ticker.name,
        "sector": s.ticker.sector,
        "signal_type": s.signal_type.value,
        "confidence": s.confidence,
        "currency": ccy,
        "currency_symbol": ccy_symbol,
        "entry_price": round(entry, 2),
        "stop_loss": round(sl, 2),
        "take_profit": round(tp, 2),
        "entry_eur": entry_eur,
        "sl_eur": sl_eur,
        "tp_eur": tp_eur,
        "risk_per_share": round(risk_per_share, 2),
        "reward_per_share": round(reward_per_share, 2),
        "risk_reward_ratio": s.risk_reward_ratio,
        "position_size": adjusted_size,
        "position_value": round(entry * adjusted_size, 2),
        "effective_exposure": effective_exposure,
        "max_loss": round(risk_per_share * adjusted_size, 2),
        "max_gain": round(reward_per_share * adjusted_size, 2),
        "risk_rating": s.risk_rating,
        "expected_hold_days": s.expected_hold_days,
        "reasoning": s.reasoning,
        "ta_score": s.ta_score,
        "fundamental_score": s.fundamental_score,
        "sentiment_score": s.sentiment_score_val,
        "macro_score": s.macro_score,
    }

    if product_info:
        result["product"] = product_info

    return result


@router.get("/overview")
def trading_desk(db: Session = Depends(get_db)):
    """Komplettes Trading-Desk in einem Call."""

    # Echtes Portfolio-Kapital fuer Position Sizing + Ranking
    from core.portfolio import get_current_capital
    _capital = get_current_capital(db)

    # === MAKRO-KONTEXT (Batch-Query) ===
    macro_indicators = ["VIX", "FED_FUNDS", "YIELD_SPREAD", "CPI", "NFP"]
    macro_subq = (
        db.query(MacroData.indicator, func.max(MacroData.date).label("max_date"))
        .filter(MacroData.indicator.in_(macro_indicators))
        .group_by(MacroData.indicator)
        .subquery()
    )
    macro_rows = (
        db.query(MacroData)
        .join(macro_subq, and_(
            MacroData.indicator == macro_subq.c.indicator,
            MacroData.date == macro_subq.c.max_date,
        ))
        .all()
    )
    macro = {}
    for row in macro_rows:
        macro[row.indicator] = {
            "value": round(row.value, 2),
            "status": row.status.value if row.status else "YELLOW",
            "date": row.date.isoformat(),
        }

    statuses = [v["status"] for v in macro.values()]
    red = statuses.count("RED")
    green = statuses.count("GREEN")
    ampel = "RED" if red >= 3 else "GREEN" if green >= 3 else "YELLOW"

    # VIX-Level bestimmt Marktregime
    vix_val = macro.get("VIX", {}).get("value", 20)
    if vix_val > 30:
        regime = "RISK_OFF"
        regime_msg = f"VIX bei {vix_val} — Hohe Volatilität. Nur mit Absicherung handeln."
    elif vix_val > 25:
        regime = "CAUTION"
        regime_msg = f"VIX bei {vix_val} — Erhöhte Vorsicht. Positionsgrößen reduzieren."
    elif vix_val < 15:
        regime = "RISK_ON"
        regime_msg = f"VIX bei {vix_val} — Niedrige Vola. Gute Bedingungen für Swing-Trades."
    else:
        regime = "NORMAL"
        regime_msg = f"VIX bei {vix_val} — Normales Marktumfeld."

    # === ALLE AKTIVEN SIGNALE LADEN ===
    all_signals = (
        db.query(Signal).join(Ticker)
        .filter(Signal.is_active == True)
        .order_by(desc(Signal.confidence)).all()
    )

    # Aufteilen: Normal vs. Leveraged/Crypto/Commodity
    leveraged_symbols = set(LEVERAGED_PRODUCTS.keys())
    special_symbols = leveraged_symbols | set(CRYPTO_ETFS.keys()) | set(COMMODITY_ETFS.keys())

    normal_signals = [s for s in all_signals if s.ticker.symbol not in special_symbols]
    product_signals = [s for s in all_signals if s.ticker.symbol in special_symbols]

    buy_signals = [s for s in normal_signals if s.signal_type == SignalType.BUY]
    sell_signals = [s for s in normal_signals if s.signal_type == SignalType.SELL]

    # Watch: HOLD-Signale sortiert nach Konfidenz × Gewinnpotenzial (volumenbereinigt)
    hold_candidates = [s for s in all_signals if s.signal_type == SignalType.HOLD and s.confidence >= 55]
    def _effective_score(s):
        entry = float(s.entry_price) if s.entry_price else 0
        tp = float(s.take_profit) if s.take_profit else 0
        sl = float(s.stop_loss) if s.stop_loss else 0
        if entry <= 0:
            return s.confidence
        risk_per_share = abs(entry - sl)
        reward_per_share = abs(tp - entry)
        # Max Stueck unter Volumen-Cap (20% Kapital)
        max_shares = min(
            int((_capital * 0.02) / risk_per_share) if risk_per_share > 0 else 0,
            int((_capital * 0.20) / entry),
        )
        max_gain_pct = (reward_per_share * max_shares / _capital * 100) if _capital > 0 else 0
        # Score: 70% Konfidenz + 30% Gewinnpotenzial (normalisiert auf 0-100)
        gain_score = min(100, max_gain_pct * 20)  # 5% Gewinn = Score 100
        return s.confidence * 0.7 + gain_score * 0.3
    hold_candidates.sort(key=_effective_score, reverse=True)
    strong_holds = hold_candidates[:8]

    # Leveraged Products — eigene Kategorien
    lev_buys = [s for s in product_signals if s.ticker.symbol in leveraged_symbols and s.signal_type in (SignalType.BUY, SignalType.HOLD) and s.confidence >= 55]
    lev_buys.sort(key=lambda s: s.confidence, reverse=True)
    crypto_signals = [s for s in product_signals if s.ticker.symbol in CRYPTO_ETFS]
    commodity_signals = [s for s in product_signals if s.ticker.symbol in COMMODITY_ETFS]

    # Signal-Counts
    signal_counts = dict(
        db.query(Signal.signal_type, func.count())
        .filter(Signal.is_active == True)
        .group_by(Signal.signal_type).all()
    )

    # === OFFENE POSITIONEN (aus Journal) — mit Realtime-Kursen ===
    from aggregator.realtime import get_realtime_quote
    open_trades = db.query(JournalEntry).filter(JournalEntry.is_closed == False).all()

    # Alle benötigten Realtime-Quotes parallel holen
    position_symbols = list({t.symbol for t in open_trades})
    index_symbols = list({"SPY", "QQQ", "IWM", "DIA", "VGK", "EEM"})
    all_rt_symbols = list(set(position_symbols + index_symbols))

    rt_quotes = {}
    if all_rt_symbols:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {
                pool.submit(get_realtime_quote, sym, sym in position_symbols): sym
                for sym in all_rt_symbols
            }
            for future in as_completed(futures):
                sym = futures[future]
                try:
                    result = future.result()
                    if result:
                        rt_quotes[sym] = result
                except Exception:
                    pass

    # Fallback-Preise für Positionen ohne Realtime-Kurs: Batch-Query
    missing_syms = [s for s in position_symbols if s not in rt_quotes]
    fallback_prices = {}
    if missing_syms:
        fallback_tickers = db.query(Ticker).filter(Ticker.symbol.in_(missing_syms)).all()
        fb_ticker_ids = {t.id: t.symbol for t in fallback_tickers}
        if fb_ticker_ids:
            from sqlalchemy.orm import aliased
            latest_ohlcv = (
                db.query(OHLCVData.ticker_id, OHLCVData.close)
                .filter(OHLCVData.ticker_id.in_(fb_ticker_ids.keys()))
                .order_by(OHLCVData.ticker_id, desc(OHLCVData.date))
                .distinct(OHLCVData.ticker_id)
                .all()
            )
            for tid, close in latest_ohlcv:
                fallback_prices[fb_ticker_ids[tid]] = round(float(close), 2)

    positions = []
    total_unrealized = 0.0
    for trade in open_trades:
        rt = rt_quotes.get(trade.symbol)
        current_price = rt["price"] if rt else fallback_prices.get(trade.symbol)

        entry = float(trade.entry_price) if trade.entry_price else 0
        size = trade.position_size or 0
        multiplier = 1 if trade.direction == "LONG" else -1

        unrealized_pnl = 0
        unrealized_pct = 0
        if current_price and entry:
            unrealized_pnl = round((current_price - entry) * size * multiplier, 2)
            unrealized_pct = round(((current_price - entry) / entry) * 100 * multiplier, 2)
            total_unrealized += unrealized_pnl

        sl = float(trade.stop_loss) if trade.stop_loss else None
        tp = float(trade.take_profit) if trade.take_profit else None
        alert = None
        if current_price and sl and current_price <= sl * 1.05 and trade.direction == "LONG":
            alert = "STOP_LOSS_NEAR"
        elif current_price and tp and current_price >= tp * 0.95 and trade.direction == "LONG":
            alert = "TAKE_PROFIT_NEAR"

        positions.append({
            "id": trade.id,
            "symbol": trade.symbol,
            "direction": trade.direction,
            "entry_price": entry,
            "current_price": current_price,
            "stop_loss": sl,
            "take_profit": tp,
            "position_size": size,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pct": unrealized_pct,
            "trade_date": trade.trade_date.isoformat(),
            "days_held": (date.today() - trade.trade_date).days,
            "setup_type": trade.setup_type,
            "alert": alert,
        })

    # === JOURNAL STATS ===
    closed = db.query(JournalEntry).filter(JournalEntry.is_closed == True).all()
    wins = [e for e in closed if e.pnl and float(e.pnl) > 0]
    total_realized = sum(float(e.pnl) for e in closed if e.pnl)
    win_rate = (len(wins) / len(closed) * 100) if closed else 0

    # === MARKT-INDIZES (mit Realtime-Kursen, bereits parallel geholt) ===
    from aggregator.currency import get_ticker_currency, convert_to_eur, get_currency_symbol
    index_map = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Russell 2000", "DIA": "Dow Jones", "VGK": "Europa", "EEM": "Emerging"}

    # Batch: alle Index-Ticker + OHLCV auf einmal
    index_tickers = db.query(Ticker).filter(Ticker.symbol.in_(index_map.keys())).all()
    idx_by_sym = {t.symbol: t for t in index_tickers}
    idx_ticker_ids = [t.id for t in index_tickers]

    idx_ohlcv_all = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id.in_(idx_ticker_ids))
        .order_by(OHLCVData.ticker_id, desc(OHLCVData.date))
        .all()
    ) if idx_ticker_ids else []

    idx_ohlcv_by_tid = {}
    for row in idx_ohlcv_all:
        idx_ohlcv_by_tid.setdefault(row.ticker_id, []).append(row)
    for tid in idx_ohlcv_by_tid:
        idx_ohlcv_by_tid[tid] = idx_ohlcv_by_tid[tid][:20]

    indices = []
    for sym, name in index_map.items():
        ticker = idx_by_sym.get(sym)
        if not ticker:
            continue
        prices = idx_ohlcv_by_tid.get(ticker.id, [])
        if len(prices) < 2:
            continue

        rt = rt_quotes.get(sym)
        if rt:
            cur = rt["price"]
            d1 = rt["change_pct"]
            source = rt["source"]
        else:
            cur = float(prices[0].close)
            prev = float(prices[1].close)
            d1 = round(((cur - prev) / prev) * 100, 2)
            source = "eod"

        d20 = round(((cur - float(prices[-1].close)) / float(prices[-1].close)) * 100, 2) if len(prices) >= 20 else d1
        ccy = get_ticker_currency(sym)
        indices.append({
            "symbol": sym, "name": name, "price": round(cur, 2),
            "change_1d": d1, "change_20d": d20, "source": source,
            "currency": ccy, "currency_symbol": get_currency_symbol(ccy),
            "price_eur": convert_to_eur(cur, ccy) if ccy != "EUR" else None,
        })

    # === SEKTOR-ROTATION (Batch-Query) ===
    sector_etfs = {"XLK": "Tech", "XLF": "Finanz", "XLV": "Health", "XLE": "Energie", "XLI": "Industrie", "XLP": "Konsum S.", "XLY": "Konsum D.", "XLU": "Versorger", "XLC": "Komm.", "XLRE": "Immob.", "XLB": "Material"}
    sector_tickers = db.query(Ticker).filter(Ticker.symbol.in_(sector_etfs.keys())).all()
    sec_by_sym = {t.symbol: t for t in sector_tickers}
    sec_ticker_ids = [t.id for t in sector_tickers]

    sec_ohlcv_all = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id.in_(sec_ticker_ids))
        .order_by(OHLCVData.ticker_id, desc(OHLCVData.date))
        .all()
    ) if sec_ticker_ids else []

    sec_ohlcv_by_tid = {}
    for row in sec_ohlcv_all:
        sec_ohlcv_by_tid.setdefault(row.ticker_id, []).append(row)
    for tid in sec_ohlcv_by_tid:
        sec_ohlcv_by_tid[tid] = sec_ohlcv_by_tid[tid][:20]

    sectors = []
    for sym, name in sector_etfs.items():
        ticker = sec_by_sym.get(sym)
        if not ticker:
            continue
        prices = sec_ohlcv_by_tid.get(ticker.id, [])
        if len(prices) >= 2:
            cur = float(prices[0].close)
            d1 = round(((cur - float(prices[1].close)) / float(prices[1].close)) * 100, 2)
            d20 = round(((cur - float(prices[-1].close)) / float(prices[-1].close)) * 100, 2) if len(prices) >= 20 else d1
            sectors.append({"symbol": sym, "name": name, "change_1d": d1, "change_20d": d20})
    sectors.sort(key=lambda x: x["change_20d"], reverse=True)

    # === TOP MOVERS (Batch-Query statt N+1) ===
    all_tickers = db.query(Ticker).join(Watchlist).all()
    all_ticker_ids = [t.id for t in all_tickers]
    ticker_by_id = {t.id: t for t in all_tickers}

    # Nur die letzten 2 Preise pro Ticker holen — eine einzige Query
    latest_two = (
        db.query(OHLCVData.ticker_id, OHLCVData.close, OHLCVData.date)
        .filter(OHLCVData.ticker_id.in_(all_ticker_ids))
        .order_by(OHLCVData.ticker_id, desc(OHLCVData.date))
        .all()
    ) if all_ticker_ids else []

    movers_by_tid = {}
    for row in latest_two:
        lst = movers_by_tid.setdefault(row.ticker_id, [])
        if len(lst) < 2:
            lst.append(float(row.close))

    movers = []
    for tid, prices in movers_by_tid.items():
        if len(prices) >= 2:
            cur, prev = prices[0], prices[1]
            ch = round(((cur - prev) / prev) * 100, 2)
            t = ticker_by_id[tid]
            movers.append({"symbol": t.symbol, "name": t.name, "price": round(cur, 2), "change": ch})
    movers.sort(key=lambda x: abs(x["change"]), reverse=True)

    # === MORNING BRIEFING ===
    briefing_points = []
    if vix_val > 25:
        briefing_points.append(f"⚠️ VIX erhöht ({vix_val:.1f}) — Positionsgrößen reduzieren")
    yield_spread = macro.get("YIELD_SPREAD", {}).get("value")
    if yield_spread is not None and yield_spread < 0:
        briefing_points.append(f"⚠️ Yield Curve invertiert ({yield_spread:.2f}%) — Rezessionsrisiko")
    if len(buy_signals) > 0:
        briefing_points.append(f"🟢 {len(buy_signals)} BUY-Signal(e) aktiv — Einstiegschancen prüfen")
    if len(sell_signals) > 0:
        briefing_points.append(f"🔴 {len(sell_signals)} SELL-Signal(e) — Positionen überprüfen")
    if len(open_trades) > 0:
        alerts = [p for p in positions if p["alert"]]
        briefing_points.append(f"📊 {len(open_trades)} offene Position(en), unrealisiert: ${total_unrealized:+,.2f}")
        if alerts:
            for a in alerts:
                if a["alert"] == "STOP_LOSS_NEAR":
                    briefing_points.append(f"🚨 {a['symbol']} nähert sich dem Stop-Loss!")
                elif a["alert"] == "TAKE_PROFIT_NEAR":
                    briefing_points.append(f"✅ {a['symbol']} nähert sich dem Take-Profit!")
    if not briefing_points:
        briefing_points.append("Keine besonderen Ereignisse. Watchlist beobachten.")

    # Wirtschaftskalender-Warnungen
    from api.routes.macro import get_economic_calendar
    try:
        calendar = get_economic_calendar()
        upcoming = [e for e in calendar if (date.fromisoformat(e["date"]) - date.today()).days <= 3 and e["importance"] == "HIGH"]
        for e in upcoming:
            days = (date.fromisoformat(e["date"]) - date.today()).days
            label = "MORGEN" if days == 1 else f"in {days} Tagen" if days > 0 else "HEUTE"
            briefing_points.append(f"📅 {e['event']} {label} — {e['impact']}")
    except Exception:
        pass

    strongest_sector = sectors[0] if sectors else None
    weakest_sector = sectors[-1] if sectors else None
    if strongest_sector:
        briefing_points.append(f"Stärkster Sektor: {strongest_sector['name']} ({strongest_sector['change_20d']:+.1f}% 20d)")
    if weakest_sector:
        briefing_points.append(f"Schwächster Sektor: {weakest_sector['name']} ({weakest_sector['change_20d']:+.1f}% 20d)")

    # Klumpenrisiko-Warnung (Batch-Query)
    if open_trades:
        trade_symbols = list({t.symbol for t in open_trades})
        trade_tickers = db.query(Ticker).filter(Ticker.symbol.in_(trade_symbols)).all()
        sector_by_sym = {t.symbol: (t.sector or "Unknown") for t in trade_tickers}
        sector_counts = {}
        for trade in open_trades:
            sector = sector_by_sym.get(trade.symbol, "Unknown")
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
        total_open = len(open_trades)
        for sector, count in sector_counts.items():
            pct = count / total_open * 100
            if pct > 50:
                briefing_points.append(f"⚠️ Klumpenrisiko: {pct:.0f}% deiner Positionen sind {sector}")

    # Leveraged Briefing
    if lev_buys:
        briefing_points.append(f"⚡ {len(lev_buys)} Hebel-Signal(e) aktiv — HOHES RISIKO, max. 1% pro Trade")
    if vix_val > 25 and lev_buys:
        briefing_points.append(f"🚫 VIX > 25 — Hebelprodukte NICHT empfohlen bei erhöhter Vola")

    # === TOP WATCHLIST (konfidenteste Signale) ===
    top_signals = (
        db.query(Signal).join(Ticker)
        .filter(Signal.is_active == True)
        .order_by(desc(Signal.confidence))
        .limit(10)
        .all()
    )

    # Shared FX-Rate Cache fuer alle Signal-Serialisierungen (1 Lookup pro Waehrung)
    _fx = {}

    # === DISCOVERY: Top-5 Vorschläge ===
    from core.models import DiscoverySuggestion
    top_discoveries = (
        db.query(DiscoverySuggestion)
        .order_by(desc(DiscoverySuggestion.discovery_score))
        .limit(5)
        .all()
    )

    return {
        "portfolio_capital": _capital,
        "briefing": briefing_points,
        "regime": {"status": regime, "message": regime_msg, "vix": vix_val},
        "macro": {"ampel": ampel, "indicators": macro},
        "signals": {
            "total": sum(signal_counts.values()),
            "buy": signal_counts.get(SignalType.BUY, 0),
            "sell": signal_counts.get(SignalType.SELL, 0),
            "hold": signal_counts.get(SignalType.HOLD, 0),
            "avoid": signal_counts.get(SignalType.AVOID, 0),
            "buys": [_serialize_signal(s, capital=_capital, fx_rates=_fx) for s in buy_signals],
            "watch": [_serialize_signal(s, capital=_capital, fx_rates=_fx) for s in strong_holds],
            "sells": [_serialize_signal(s, capital=_capital, fx_rates=_fx) for s in sell_signals],
        },
        "products": {
            "leveraged": [_serialize_signal(s, capital=_capital, fx_rates=_fx) for s in lev_buys[:8]],
            "crypto": [_serialize_signal(s, capital=_capital, fx_rates=_fx) for s in crypto_signals],
            "commodities": [_serialize_signal(s, capital=_capital, fx_rates=_fx) for s in commodity_signals],
        },
        "positions": {
            "open": positions,
            "unrealized_total": round(total_unrealized, 2),
            "realized_total": round(total_realized, 2),
            "total_trades": len(closed),
            "win_rate": round(win_rate, 1),
        },
        "indices": indices,
        "sectors": sectors,
        "movers": {
            "gainers": sorted([m for m in movers if m["change"] > 0], key=lambda x: x["change"], reverse=True)[:5],
            "losers": sorted([m for m in movers if m["change"] < 0], key=lambda x: x["change"])[:5],
        },
        "top_watchlist": [
            {
                "symbol": s.ticker.symbol,
                "name": s.ticker.name,
                "signal_type": s.signal_type.value,
                "confidence": s.confidence,
                "entry_price": float(s.entry_price) if s.entry_price else 0,
                "stop_loss": float(s.stop_loss) if s.stop_loss else 0,
                "take_profit": float(s.take_profit) if s.take_profit else 0,
                "reasoning": s.reasoning,
            }
            for s in top_signals
        ],
        "discovery": [
            {
                "symbol": d.symbol,
                "name": d.name,
                "score": d.discovery_score,
                "source": d.source,
                "reason": d.reason,
                "fund_count": d.fund_count,
                "price": float(d.current_price) if d.current_price else None,
                "rsi": d.rsi_14,
            }
            for d in top_discoveries
        ],
    }
