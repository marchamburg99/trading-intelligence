"""Discovery Screener: Trichter-Ansatz fuer proaktive Markt-Erkennung."""
import math
import structlog
import pandas as pd
import pandas_ta as pta
from aggregator.yf_session import yf_safe_download
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from core.models import (
    HedgeFundFiling, HedgeFundPosition, OHLCVData, Ticker,
    DiscoverySuggestion, Watchlist,
)
from core.products import is_eu_tradeable
from discovery.universe import SECTOR_TOP_STOCKS

logger = structlog.get_logger()


def _safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else round(f, 4)
    except (ValueError, TypeError):
        return None


# ============================================================
# Stage 1: Hedge-Fund-Clustering (nur SQL)
# ============================================================

def _find_hedge_fund_clusters(db: Session) -> list[dict]:
    """Finde Aktien die in 3+ Top-Fonds mit hoher Conviction gehalten werden."""
    # Neuestes Filing pro Fund
    latest_filings = (
        db.query(
            HedgeFundFiling.fund_name,
            func.max(HedgeFundFiling.id).label("latest_id"),
        )
        .group_by(HedgeFundFiling.fund_name)
        .subquery()
    )

    # Alle Positionen aus den neuesten Filings
    positions = (
        db.query(HedgeFundPosition, HedgeFundFiling)
        .join(HedgeFundFiling)
        .filter(
            HedgeFundFiling.id.in_(db.query(latest_filings.c.latest_id)),
            HedgeFundPosition.symbol.isnot(None),
        )
        .all()
    )

    if not positions:
        logger.info("discovery.no_hedge_fund_data")
        return []

    # Gruppieren nach Symbol
    by_symbol: dict[str, list[tuple]] = {}
    for pos, filing in positions:
        by_symbol.setdefault(pos.symbol, []).append((pos, filing))

    clusters = []
    for symbol, entries in by_symbol.items():
        # Conviction-Filter: Position > 1% des Fund-Portfolios
        high_conviction = []
        for pos, filing in entries:
            if filing.total_value and filing.total_value > 0 and pos.value:
                weight = (float(pos.value) / float(filing.total_value)) * 100
                if weight >= 1.0:
                    high_conviction.append((pos, filing, weight))

        fund_names = list({f.fund_name for _, f, _ in high_conviction})
        fund_count = len(fund_names)

        if fund_count < 2:
            continue

        # Score berechnen
        score = 50.0
        if fund_count >= 5:
            score += 30
        elif fund_count >= 3:
            score += 20
        else:
            score += 10

        # Aufstockungen bonus
        increased = [p for p, _, _ in high_conviction if p.change_type in ("NEW", "INCREASED")]
        if increased:
            score += min(15, len(increased) * 5)

        decreased = [p for p, _, _ in high_conviction if p.change_type in ("DECREASED", "EXIT")]
        if decreased:
            score -= min(15, len(decreased) * 5)

        change_types = list({p.change_type for p, _, _ in high_conviction if p.change_type})
        company_name = entries[0][0].company_name

        clusters.append({
            "symbol": symbol,
            "name": company_name,
            "fund_count": fund_count,
            "fund_names": fund_names,
            "change_types": change_types,
            "hedge_fund_score": max(0, min(100, score)),
        })

    clusters.sort(key=lambda x: x["hedge_fund_score"], reverse=True)
    logger.info("discovery.hedge_fund_clusters", count=len(clusters))
    return clusters


# ============================================================
# Stage 2: Sektor-Momentum (nutzt bestehende OHLCV)
# ============================================================

SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLP": "Consumer Staples",
    "XLY": "Consumer Discretionary",
    "XLU": "Utilities",
    "XLC": "Communication Services",
    "XLRE": "Real Estate",
    "XLB": "Materials",
}


def _compute_sector_momentum(db: Session) -> dict[str, float]:
    """Berechne 20-Tage-Momentum der Sektor-ETFs."""
    sector_tickers = db.query(Ticker).filter(Ticker.symbol.in_(SECTOR_ETFS.keys())).all()
    if not sector_tickers:
        return {}

    ticker_ids = [t.id for t in sector_tickers]
    sym_by_id = {t.id: t.symbol for t in sector_tickers}

    ohlcv_all = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id.in_(ticker_ids))
        .order_by(OHLCVData.ticker_id, desc(OHLCVData.date))
        .all()
    )

    by_tid: dict[int, list] = {}
    for row in ohlcv_all:
        lst = by_tid.setdefault(row.ticker_id, [])
        if len(lst) < 20:
            lst.append(row)

    momentum = {}
    for tid, prices in by_tid.items():
        if len(prices) < 2:
            continue
        cur = float(prices[0].close)
        ref = float(prices[-1].close)
        ret_20d = round(((cur - ref) / ref) * 100, 2)
        sector_name = SECTOR_ETFS.get(sym_by_id[tid])
        if sector_name:
            momentum[sector_name] = ret_20d

    logger.info("discovery.sector_momentum", sectors=momentum)
    return momentum


# ============================================================
# Stage 3: Technisches Screening (Batch yf.download)
# ============================================================

def _compute_ta_from_df(df: pd.DataFrame) -> dict | None:
    """Berechne leichtgewichtige TA-Indikatoren aus OHLCV DataFrame."""
    if len(df) < 50:
        return None

    close = df["Close"] if "Close" in df.columns else df["close"]
    high = df["High"] if "High" in df.columns else df["high"]
    low = df["Low"] if "Low" in df.columns else df["low"]

    rsi = pta.rsi(close, length=14)
    ema_50 = pta.ema(close, length=50)
    ema_200 = pta.ema(close, length=200) if len(df) >= 200 else None
    bbands = pta.bbands(close, length=20)
    macd = pta.macd(close, fast=12, slow=26, signal=9)

    current_price = float(close.iloc[-1])
    rsi_val = _safe_float(rsi.iloc[-1]) if rsi is not None else None
    ema50_val = _safe_float(ema_50.iloc[-1]) if ema_50 is not None else None
    ema200_val = _safe_float(ema_200.iloc[-1]) if ema_200 is not None else None

    # TA Score berechnen (gleiche Logik wie signals/engine.py, vereinfacht)
    score = 50.0
    signals = []

    if rsi_val is not None:
        if rsi_val < 30:
            score += 15
            signals.append(f"RSI bei {rsi_val:.0f} (ueberverkauft)")
        elif rsi_val < 40:
            score += 8
            signals.append(f"RSI bei {rsi_val:.0f}")
        elif rsi_val > 70:
            score -= 15
            signals.append(f"RSI bei {rsi_val:.0f} (ueberkauft)")
        elif rsi_val > 60:
            score -= 5

    if macd is not None and len(macd.columns) >= 2:
        macd_val = _safe_float(macd.iloc[-1, 0])
        macd_sig = _safe_float(macd.iloc[-1, 1])
        if macd_val is not None and macd_sig is not None:
            if macd_val > macd_sig:
                score += 10
                signals.append("MACD bullish")
            else:
                score -= 10

    if ema50_val and ema200_val:
        if current_price > ema50_val > ema200_val:
            score += 15
            signals.append("EMA-Alignment bullish")
        elif current_price < ema50_val < ema200_val:
            score -= 15
        elif current_price > ema200_val:
            score += 5
        else:
            score -= 5

    if bbands is not None and len(bbands.columns) >= 3:
        bb_lower = _safe_float(bbands.iloc[-1, 0])
        bb_upper = _safe_float(bbands.iloc[-1, 2])
        if bb_lower and bb_upper:
            bb_width = bb_upper - bb_lower
            if bb_width > 0:
                bb_pos = (current_price - bb_lower) / bb_width
                if bb_pos < 0.2:
                    score += 10
                    signals.append("Nahe unterem Bollinger Band")
                elif bb_pos > 0.8:
                    score -= 10

    return {
        "price": round(current_price, 2),
        "rsi": rsi_val,
        "technical_score": max(0, min(100, score)),
        "signals": signals,
    }


def _screen_candidates(candidates: list[str], db: Session) -> dict[str, dict]:
    """Technisches Screening: zuerst DB-Daten, dann yfinance fuer Rest."""
    results = {}

    # Bereits in DB vorhandene Ticker pruefen
    existing_tickers = db.query(Ticker).filter(Ticker.symbol.in_(candidates)).all()
    existing_by_sym = {t.symbol: t for t in existing_tickers}

    db_screened = set()
    for sym, ticker in existing_by_sym.items():
        ohlcv = (
            db.query(OHLCVData)
            .filter(OHLCVData.ticker_id == ticker.id)
            .order_by(OHLCVData.date)
            .all()
        )
        if len(ohlcv) < 50:
            continue

        df = pd.DataFrame([{
            "close": float(d.close),
            "high": float(d.high),
            "low": float(d.low),
        } for d in ohlcv])

        # Rename for _compute_ta_from_df
        df.rename(columns={"close": "Close", "high": "High", "low": "Low"}, inplace=True)
        ta_result = _compute_ta_from_df(df)
        if ta_result:
            ta_result["name"] = ticker.name
            ta_result["sector"] = ticker.sector
            results[sym] = ta_result
            db_screened.add(sym)

    # Rest via yfinance batch-download
    to_fetch = [s for s in candidates if s not in db_screened]
    if to_fetch:
        logger.info("discovery.yfinance_batch", count=len(to_fetch))
        try:
            # Batch in Gruppen von 50 aufteilen
            for i in range(0, len(to_fetch), 50):
                batch = to_fetch[i:i + 50]
                data = yf_safe_download(
                    batch,
                    period="6mo",
                    group_by="ticker",
                )

                if data.empty:
                    continue

                for sym in batch:
                    try:
                        if len(batch) == 1:
                            sym_df = data
                        else:
                            sym_df = data[sym].dropna(how="all")
                        if sym_df.empty or len(sym_df) < 50:
                            continue
                        ta_result = _compute_ta_from_df(sym_df)
                        if ta_result:
                            results[sym] = ta_result
                    except (KeyError, TypeError):
                        continue
        except Exception as e:
            logger.error("discovery.yfinance_failed", error=str(e))

    logger.info("discovery.screened", count=len(results))
    return results


# ============================================================
# Stage 4: Ranking + Suggestion-Erstellung
# ============================================================

def _build_reason(symbol: str, hf_data: dict | None, ta_data: dict | None,
                  sector_name: str | None, sector_momentum: float | None) -> str:
    """Deutsche Begruendung fuer die Suggestion."""
    parts = []

    if hf_data:
        names = ", ".join(hf_data["fund_names"][:4])
        suffix = f" +{len(hf_data['fund_names']) - 4} weitere" if len(hf_data["fund_names"]) > 4 else ""
        parts.append(f"In {hf_data['fund_count']} Top-Fonds ({names}{suffix})")

        if "NEW" in hf_data.get("change_types", []):
            parts.append("Neue Position(en) eroeffnet")
        elif "INCREASED" in hf_data.get("change_types", []):
            parts.append("Position(en) aufgestockt")

    if ta_data and ta_data.get("signals"):
        parts.extend(ta_data["signals"][:2])

    if sector_name and sector_momentum is not None and sector_momentum > 3:
        parts.append(f"{sector_name}-Sektor mit {sector_momentum:+.1f}% Momentum")

    return ". ".join(parts) + "." if parts else f"{symbol} erfuellt Discovery-Kriterien."


def run_discovery_pipeline(db: Session) -> list[DiscoverySuggestion]:
    """Hauptpipeline: Trichter von Universum zu Top-20 Vorschlaegen."""
    # Watchlist-Symbole ausschliessen (die werden schon analysiert)
    watchlist_syms = {
        row[0] for row in db.query(Ticker.symbol).join(Watchlist).all()
    }

    # Stage 1: Hedge-Fund-Clustering
    clusters = _find_hedge_fund_clusters(db)
    hf_by_sym = {c["symbol"]: c for c in clusters}

    # Stage 2: Sektor-Momentum
    sector_momentum = _compute_sector_momentum(db)

    # Kandidaten aus heissen Sektoren hinzufuegen
    sector_candidates = set()
    for sector_name, momentum_val in sector_momentum.items():
        if momentum_val > 3.0:  # >3% 20d Return = starker Sektor
            stocks = SECTOR_TOP_STOCKS.get(sector_name, [])
            sector_candidates.update(stocks[:10])

    # Alle Kandidaten zusammenfuehren (HF-Cluster + Sektor-Picks)
    all_candidates = set(hf_by_sym.keys()) | sector_candidates
    all_candidates -= watchlist_syms  # Bereits auf Watchlist ausschliessen

    # US-ETFs + Leveraged ETFs rausfiltern (nicht EU-kaufbar)
    all_candidates = {s for s in all_candidates if is_eu_tradeable(s)}

    if not all_candidates:
        logger.info("discovery.no_candidates")
        return []

    logger.info("discovery.candidates", count=len(all_candidates))

    # Stage 3: Technisches Screening
    ta_results = _screen_candidates(list(all_candidates), db)

    # Stage 4: Composite Score + Ranking
    suggestions = []
    for sym in all_candidates:
        hf_data = hf_by_sym.get(sym)
        ta_data = ta_results.get(sym)

        # Mindestens eine Datenquelle muss vorhanden sein
        is_sector_candidate = sym in sector_candidates
        if not hf_data and not ta_data and not is_sector_candidate:
            continue

        hf_score = hf_data["hedge_fund_score"] if hf_data else 50.0
        tech_score = ta_data["technical_score"] if ta_data else 50.0

        # Sektor-Score
        sector_name = ta_data.get("sector") if ta_data else None
        sec_momentum = None
        sec_score = 50.0
        if sector_name and sector_name in sector_momentum:
            sec_momentum = sector_momentum[sector_name]
            sec_score = max(0, min(100, 50 + sec_momentum * 3))
        elif not sector_name:
            # Checke ob Symbol in einer Sektor-Liste vorkommt
            for sname, stocks in SECTOR_TOP_STOCKS.items():
                if sym in stocks:
                    sector_name = sname
                    if sname in sector_momentum:
                        sec_momentum = sector_momentum[sname]
                        sec_score = max(0, min(100, 50 + sec_momentum * 3))
                    break

        # Composite: 40% HF + 40% TA + 20% Sektor
        composite = (hf_score * 0.40) + (tech_score * 0.40) + (sec_score * 0.20)

        # Source bestimmen
        if hf_data and hf_data["fund_count"] >= 3 and ta_data and tech_score >= 60:
            source = "combined"
        elif hf_data and hf_data["fund_count"] >= 3:
            source = "hedge_fund_cluster"
        elif sec_momentum and sec_momentum > 3:
            source = "sector_momentum"
        elif ta_data and tech_score >= 60:
            source = "technical_setup"
        else:
            source = "sector_momentum" if is_sector_candidate else "technical_setup"

        reason = _build_reason(sym, hf_data, ta_data, sector_name, sec_momentum)

        suggestions.append(DiscoverySuggestion(
            symbol=sym,
            name=(ta_data.get("name") if ta_data else None) or (hf_data["name"] if hf_data else None),
            sector=sector_name,
            discovery_score=round(composite, 1),
            hedge_fund_score=round(hf_score, 1),
            technical_score=round(tech_score, 1),
            sector_score=round(sec_score, 1),
            source=source,
            reason=reason,
            fund_count=hf_data["fund_count"] if hf_data else None,
            fund_names=hf_data["fund_names"] if hf_data else None,
            current_price=ta_data["price"] if ta_data else None,
            rsi_14=ta_data["rsi"] if ta_data else None,
        ))

    suggestions.sort(key=lambda s: s.discovery_score, reverse=True)
    top = suggestions[:20]
    logger.info("discovery.pipeline_complete", suggestions=len(top))
    return top
