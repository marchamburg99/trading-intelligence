"""
Signal Engine v2: Multi-Factor + Institutional + Regime-Aware

Gewichtung:
  - Technical Analysis: 25%
  - Multi-Factor (Momentum + Quality + Trend): 25%
  - Institutional (13F Conviction): 20%
  - Makro/Regime: 15%
  - Sentiment (News only, kein Reddit): 10%
  - Research: 5%

Basiert auf: AQR Value & Momentum Everywhere, MSCI 50-Year Factor Study,
Two Sigma Factor Lens, Pan/Poteshman PCR-Studie, RegimeFolio (arXiv 2025)
"""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from core.models import (
    Ticker, Indicator, Signal, SignalType, SentimentScore,
    MacroData, MacroStatus, OHLCVData,
    HedgeFundFiling, HedgeFundPosition, Paper,
)


# ============================================================
# 1. TECHNICAL ANALYSIS (25%)
# ============================================================

def compute_ta_score(ind: Indicator, close: float) -> tuple[float, list[str]]:
    signals = []
    score = 50.0

    if ind.rsi_14 is not None:
        if ind.rsi_14 < 30:
            score += 15
            signals.append("RSI oversold")
        elif ind.rsi_14 < 40:
            score += 8
        elif ind.rsi_14 > 70:
            score -= 15
            signals.append("RSI overbought")
        elif ind.rsi_14 > 60:
            score -= 5

    if ind.macd is not None and ind.macd_signal is not None:
        if ind.macd > ind.macd_signal:
            score += 10
            signals.append("MACD bullish")
        else:
            score -= 10

    if ind.ema_21 and ind.ema_50 and ind.ema_200:
        if close > ind.ema_21 > ind.ema_50 > ind.ema_200:
            score += 15
            signals.append("EMA-Alignment bullish (21>50>200)")
        elif close < ind.ema_21 < ind.ema_50 < ind.ema_200:
            score -= 15
            signals.append("EMA-Alignment bearish")
        elif close > ind.ema_200:
            score += 5
        else:
            score -= 5

    if ind.bb_lower and ind.bb_upper:
        bb_width = ind.bb_upper - ind.bb_lower
        if bb_width > 0:
            bb_pos = (close - ind.bb_lower) / bb_width
            if bb_pos < 0.2:
                score += 10
                signals.append("Nahe unterem BB")
            elif bb_pos > 0.8:
                score -= 10

    if ind.stoch_k is not None and ind.stoch_d is not None:
        if ind.stoch_k < 20 and ind.stoch_d < 20:
            score += 8
            signals.append("Stochastic oversold")
        elif ind.stoch_k > 80 and ind.stoch_d > 80:
            score -= 8

    return max(0, min(100, score)), signals


# ============================================================
# 2. MULTI-FACTOR SCORE (25%) — Momentum + Quality + Trend
# ============================================================

def compute_multifactor_score(ticker: Ticker, db: Session) -> tuple[float, list[str]]:
    """
    Multi-Factor Score basierend auf:
    - 12-1 Monats-Momentum (klassischer Momentum-Faktor)
    - 20-Tage Short-Term Reversal
    - Preis über 200-Tage EMA (Trend-Quality)
    - Market Cap (Size-Faktor)
    """
    signals = []
    score = 50.0

    prices = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(desc(OHLCVData.date))
        .limit(260)  # ~1 Jahr
        .all()
    )

    if len(prices) < 60:
        return score, signals

    current = float(prices[0].close)

    # --- 12-1 Monats-Momentum ---
    # Return über 12 Monate, exkl. letzten Monat (klassischer Jegadeesh/Titman)
    if len(prices) >= 252:
        price_12m = float(prices[251].close)
        price_1m = float(prices[21].close)
        momentum_12_1 = ((price_1m - price_12m) / price_12m) * 100

        if momentum_12_1 > 30:
            score += 15
            signals.append(f"Starkes 12-1M Momentum ({momentum_12_1:+.0f}%)")
        elif momentum_12_1 > 10:
            score += 10
            signals.append(f"Positives Momentum ({momentum_12_1:+.0f}%)")
        elif momentum_12_1 < -20:
            score -= 15
            signals.append(f"Negatives Momentum ({momentum_12_1:+.0f}%)")
        elif momentum_12_1 < -5:
            score -= 8

    # --- 20-Tage Short-Term Trend ---
    if len(prices) >= 20:
        price_20d = float(prices[19].close)
        ret_20d = ((current - price_20d) / price_20d) * 100

        if ret_20d > 8:
            score += 5
        elif ret_20d < -8:
            # Mean-Reversion Opportunity bei Überverkauf
            score += 3
            signals.append(f"20d Überverkauf ({ret_20d:+.1f}%), Mean-Reversion möglich")

    # --- 50-Tage Trend-Stärke ---
    if len(prices) >= 50:
        price_50d = float(prices[49].close)
        ret_50d = ((current - price_50d) / price_50d) * 100
        if ret_50d > 15:
            score += 5
        elif ret_50d < -15:
            score -= 5

    # --- Market Cap (Size-Faktor) ---
    if ticker.market_cap:
        cap = float(ticker.market_cap)
        if cap > 200e9:  # Mega Cap
            score += 3  # Stabilität
        elif cap > 50e9:  # Large Cap
            score += 2
        elif cap < 2e9:  # Small Cap — höheres Alpha-Potenzial aber Risiko
            score -= 3

    return max(0, min(100, score)), signals


# ============================================================
# 3. INSTITUTIONAL SCORE (20%) — 13F Conviction-Weighted
# ============================================================

def compute_institutional_score(symbol: str, db: Session) -> tuple[float, list[str]]:
    """
    Institutioneller Score mit Conviction-Filter:
    - Nur Positionen > 1% des Fund-Portfolios zählen (high conviction)
    - Gewichtet nach Anzahl unterschiedlicher Fonds
    - Aufstockungen stärker als statische Positionen
    """
    signals = []
    score = 50.0

    # Neuestes Filing pro Fund
    latest_filings = (
        db.query(
            HedgeFundFiling.fund_name,
            func.max(HedgeFundFiling.id).label("latest_id"),
        )
        .group_by(HedgeFundFiling.fund_name)
        .subquery()
    )

    # Alle Positionen für dieses Symbol in den neuesten Filings
    positions = (
        db.query(HedgeFundPosition, HedgeFundFiling)
        .join(HedgeFundFiling)
        .filter(
            HedgeFundFiling.id.in_(db.query(latest_filings.c.latest_id)),
            HedgeFundPosition.symbol == symbol,
        )
        .all()
    )

    if not positions:
        # Fallback: Name-Matching
        positions = (
            db.query(HedgeFundPosition, HedgeFundFiling)
            .join(HedgeFundFiling)
            .filter(
                HedgeFundFiling.id.in_(db.query(latest_filings.c.latest_id)),
                HedgeFundPosition.company_name.ilike(f"%{symbol}%"),
            )
            .all()
        )

    if not positions:
        return score, signals

    # Conviction-Filter: Position > 1% des Fund-Gesamtwerts
    conviction_positions = []
    for pos, filing in positions:
        if filing.total_value and filing.total_value > 0 and pos.value:
            weight = (float(pos.value) / float(filing.total_value)) * 100
            if weight >= 1.0:
                conviction_positions.append((pos, filing, weight))
        else:
            conviction_positions.append((pos, filing, 0))

    fund_count = len(set(f.fund_name for _, f, _ in conviction_positions))
    total_funds = len(set(f.fund_name for _, f in positions))

    if fund_count >= 5:
        score += 25
        signals.append(f"{fund_count} Fonds mit High-Conviction Position")
    elif fund_count >= 3:
        score += 15
        signals.append(f"{fund_count} Fonds halten Position (Cluster)")
    elif fund_count >= 1:
        score += 5
        signals.append(f"{fund_count} Fonds hält Position")
    elif total_funds >= 3:
        # Viele Fonds halten, aber kleine Positionen
        score += 8
        signals.append(f"{total_funds} Fonds (niedrige Conviction)")

    # Aufstockungen
    increased = [p for p, _, _ in conviction_positions if p.change_type in ("NEW", "INCREASED")]
    if increased:
        score += 10
        signals.append(f"{len(increased)} Fonds stocken auf")

    decreased = [p for p, _, _ in conviction_positions if p.change_type in ("DECREASED", "EXIT")]
    if decreased:
        score -= 10
        signals.append(f"{len(decreased)} Fonds reduzieren")

    return max(0, min(100, score)), signals


# ============================================================
# 4. MAKRO/REGIME SCORE (15%) — VIX + Yield + Credit Spreads
# ============================================================

def compute_macro_score(db: Session) -> tuple[float, list[str]]:
    """
    Regime-Erkennung: VIX, Yield Curve, Credit Spreads (HYG-Proxy).
    3 Regime: Risk-On (>65), Neutral (35-65), Risk-Off (<35)
    """
    signals = []
    score = 50.0

    # VIX
    vix = db.query(MacroData).filter(MacroData.indicator == "VIX").order_by(desc(MacroData.date)).first()
    if vix:
        if vix.value < 15:
            score += 15
            signals.append(f"VIX niedrig ({vix.value:.1f})")
        elif vix.value < 20:
            score += 5
        elif vix.value > 30:
            score -= 20
            signals.append(f"VIX HOCH ({vix.value:.1f}) — Risk-Off")
        elif vix.value > 25:
            score -= 10
            signals.append(f"VIX erhöht ({vix.value:.1f})")

    # Yield Curve (10Y-2Y)
    ys = db.query(MacroData).filter(MacroData.indicator == "YIELD_SPREAD").order_by(desc(MacroData.date)).first()
    if ys:
        if ys.value < -0.5:
            score -= 15
            signals.append(f"Yield Curve stark invertiert ({ys.value:.2f}%)")
        elif ys.value < 0:
            score -= 8
            signals.append(f"Yield Curve invertiert ({ys.value:.2f}%)")
        elif ys.value > 1.5:
            score += 10
            signals.append("Steile Yield Curve — expansiv")
        elif ys.value > 0.5:
            score += 5

    # Fed Funds Rate Trend
    fed_data = (
        db.query(MacroData)
        .filter(MacroData.indicator == "FED_FUNDS")
        .order_by(desc(MacroData.date))
        .limit(3)
        .all()
    )
    if len(fed_data) >= 2:
        if fed_data[0].value < fed_data[1].value:
            score += 5
            signals.append("Fed senkt Zinsen — bullish")
        elif fed_data[0].value > fed_data[1].value:
            score -= 5

    return max(0, min(100, score)), signals


# ============================================================
# 5. SENTIMENT SCORE (10%) — News only, kein Reddit
# ============================================================

def compute_sentiment_score(sentiment: SentimentScore | None) -> tuple[float, list[str]]:
    """
    Sentiment aus News. Reddit-Gewichtung = 0 (kein Alpha laut Forschung).
    PCR als Kontra-Indikator bei Extremen.
    """
    signals = []

    if not sentiment:
        return 50.0, signals

    score = 50.0

    # News-Sentiment (normalisiert von [-1,1] auf [0,100])
    if sentiment.news_sentiment is not None:
        news_norm = (sentiment.news_sentiment + 1) * 50
        score = news_norm
        if sentiment.news_sentiment > 0.3:
            signals.append("Positiver Newsflow")
        elif sentiment.news_sentiment < -0.3:
            signals.append("Negativer Newsflow")

    # Put/Call Ratio als Kontra-Indikator (Pan/Poteshman 2006)
    if sentiment.put_call_ratio is not None:
        pcr = sentiment.put_call_ratio
        if pcr > 1.5:
            score += 10  # Extreme Fear → Kontra-Bullish
            signals.append(f"PCR extrem hoch ({pcr:.2f}) — Kontra-Kaufsignal")
        elif pcr < 0.6:
            score -= 10  # Extreme Greed → Kontra-Bearish
            signals.append(f"PCR extrem niedrig ({pcr:.2f}) — Euphorie-Warnung")

    # Fear & Greed als Kontra-Indikator bei Extremen
    if sentiment.fear_greed_index is not None:
        fg = sentiment.fear_greed_index
        if fg < 20:
            score += 8  # Extreme Fear → Buying Opportunity
            signals.append("Fear & Greed: Extreme Angst — Kontra-Kaufgelegenheit")
        elif fg > 80:
            score -= 8  # Extreme Greed → Warnung
            signals.append("Fear & Greed: Extreme Gier — Vorsicht")

    return max(0, min(100, score)), signals


# ============================================================
# 6. RESEARCH SCORE (5%)
# ============================================================

def compute_research_score(symbol: str, ticker: Ticker, db: Session) -> tuple[float, list[str]]:
    signals = []
    score = 50.0

    relevant = (
        db.query(Paper)
        .filter(Paper.relevance_score.isnot(None), Paper.relevance_score >= 60)
        .count()
    )

    if relevant >= 10:
        score += 5
        signals.append(f"{relevant} relevante Research-Papers")

    high = (
        db.query(Paper)
        .filter(Paper.relevance_score.isnot(None), Paper.relevance_score >= 80)
        .count()
    )
    if high >= 3:
        score += 5

    total = db.query(Paper).count()
    if total >= 20:
        score += 3

    return max(0, min(100, score)), signals


# ============================================================
# REASONING BUILDER
# ============================================================

def _build_reasoning(
    symbol, signal_type, confidence, close,
    ta_score, ta_signals, mf_score, mf_signals,
    inst_score, inst_signals, macro_score, macro_signals,
    sent_score, sent_signals, research_score,
    stop_loss, take_profit, risk_per_share, reward_per_share,
    ind,
) -> str:
    """Erzeugt eine klare, menschenlesbare Begründung für das Signal."""
    parts = []

    # 1. Hauptaussage
    if signal_type == SignalType.BUY:
        parts.append(f"KAUFEMPFEHLUNG für {symbol} bei ${close:.2f}.")
    elif signal_type == SignalType.SELL:
        parts.append(f"VERKAUFSEMPFEHLUNG für {symbol} bei ${close:.2f}.")
    elif signal_type == SignalType.AVOID:
        parts.append(f"{symbol} MEIDEN — zu viele Risikofaktoren.")
    else:
        if confidence >= 60:
            parts.append(f"{symbol} auf der Watchlist halten — nahe am Kaufsignal ({confidence:.0f}%).")
        elif confidence >= 50:
            parts.append(f"{symbol} neutral — kein klarer Einstiegspunkt.")
        else:
            parts.append(f"{symbol} unter Beobachtung — schwache Signallage ({confidence:.0f}%).")

    # 2. Technische Lage (stärkster Treiber)
    ta_parts = []
    if ind.rsi_14 is not None:
        if ind.rsi_14 < 30:
            ta_parts.append(f"RSI bei {ind.rsi_14:.0f} (überverkauft)")
        elif ind.rsi_14 > 70:
            ta_parts.append(f"RSI bei {ind.rsi_14:.0f} (überkauft)")
        else:
            ta_parts.append(f"RSI bei {ind.rsi_14:.0f}")

    for s in ta_signals:
        if s not in str(ta_parts):
            ta_parts.append(s)

    if ta_parts:
        ta_label = "bullish" if ta_score >= 60 else "bearish" if ta_score <= 40 else "neutral"
        parts.append(f"Technisch {ta_label}: {', '.join(ta_parts[:3])}.")

    # 3. Momentum/Multi-Factor
    if mf_signals:
        parts.append(" ".join(mf_signals[:2]) + ".")

    # 4. Institutionelle Unterstützung
    if inst_signals:
        parts.append(" ".join(inst_signals[:2]) + ".")
    elif inst_score == 50:
        parts.append("Keine Hedge-Fund-Daten für diesen Ticker.")

    # 5. Makro-Kontext
    if macro_signals:
        parts.append("Makro: " + ", ".join(macro_signals[:2]) + ".")
    elif macro_score >= 55:
        parts.append("Makro-Umfeld unterstützend.")
    elif macro_score <= 45:
        parts.append("Makro-Gegenwind (erhöhte Vorsicht).")

    # 6. Sentiment
    if sent_signals:
        parts.append(" ".join(sent_signals[:1]) + ".")

    # 7. Risk/Reward Erklärung
    if risk_per_share > 0 and reward_per_share > 0:
        rr = reward_per_share / risk_per_share
        risk_pct = (risk_per_share / close) * 100
        parts.append(
            f"Risk/Reward {rr:.1f}:1 — "
            f"Risiko ${risk_per_share:.2f}/Aktie ({risk_pct:.1f}%), "
            f"Ziel ${reward_per_share:.2f}/Aktie."
        )

    return " ".join(parts)


# ============================================================
# SIGNAL GENERATOR
# ============================================================

def generate_signal(symbol: str, db: Session, capital: float = 100000.0) -> Signal | None:
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        return None

    ind = (
        db.query(Indicator)
        .filter(Indicator.ticker_id == ticker.id)
        .order_by(desc(Indicator.date))
        .first()
    )
    if not ind:
        return None

    last_ohlcv = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(desc(OHLCVData.date))
        .first()
    )
    if not last_ohlcv:
        return None

    close = float(last_ohlcv.close)

    # === Sub-Scores ===
    ta_score, ta_signals = compute_ta_score(ind, close)
    mf_score, mf_signals = compute_multifactor_score(ticker, db)
    inst_score, inst_signals = compute_institutional_score(symbol, db)
    macro_score, macro_signals = compute_macro_score(db)

    sentiment = (
        db.query(SentimentScore)
        .filter(SentimentScore.ticker_id == ticker.id)
        .order_by(desc(SentimentScore.date))
        .first()
    )
    sent_score, sent_signals = compute_sentiment_score(sentiment)
    research_score, research_signals = compute_research_score(symbol, ticker, db)

    # === Gewichteter Score ===
    # TA 25%, Multi-Factor 25%, Institutional 20%, Makro 15%, Sentiment 10%, Research 5%
    confidence = (
        (ta_score * 0.25) +
        (mf_score * 0.25) +
        (inst_score * 0.20) +
        (macro_score * 0.15) +
        (sent_score * 0.10) +
        (research_score * 0.05)
    )

    # === Signal-Typ ===
    if confidence >= 68:
        signal_type = SignalType.BUY
    elif confidence >= 40:
        signal_type = SignalType.HOLD
    elif confidence >= 25:
        signal_type = SignalType.SELL
    else:
        signal_type = SignalType.AVOID

    # === Stop-Loss & Take-Profit (ATR-basiert) ===
    atr = ind.atr_14 or (close * 0.02)
    if signal_type in (SignalType.BUY, SignalType.HOLD):
        stop_loss = close - (1.5 * atr)
        take_profit = close + (3.0 * atr)
    else:
        stop_loss = close + (1.5 * atr)
        take_profit = close - (3.0 * atr)

    # === Position Sizing: Fractional Kelly (50%) ===
    risk_per_share = abs(close - stop_loss)
    reward_per_share = abs(take_profit - close)

    # Kelly: f* = (p * b - q) / b, wobei p=Win-Prob, b=Reward/Risk, q=1-p
    # Approximation: Confidence/100 als Win-Wahrscheinlichkeit
    win_prob = min(0.7, max(0.3, confidence / 100))
    rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 2.0
    kelly_full = (win_prob * rr_ratio - (1 - win_prob)) / rr_ratio if rr_ratio > 0 else 0
    kelly_fraction = max(0, kelly_full * 0.5)  # 50% Kelly

    # Cap bei 3% des Portfolios
    max_risk_pct = min(kelly_fraction, 0.03)
    position_size = (capital * max_risk_pct) / risk_per_share if risk_per_share > 0 else 0

    # Risk-Rating
    if confidence >= 75:
        risk_rating = 1
    elif confidence >= 63:
        risk_rating = 2
    elif confidence >= 50:
        risk_rating = 3
    elif confidence >= 35:
        risk_rating = 4
    else:
        risk_rating = 5

    # === Reasoning: Verständliche Begründung ===
    reasoning = _build_reasoning(
        symbol, signal_type, confidence, close,
        ta_score, ta_signals, mf_score, mf_signals,
        inst_score, inst_signals, macro_score, macro_signals,
        sent_score, sent_signals, research_score,
        stop_loss, take_profit, risk_per_share, reward_per_share,
        ind,
    )

    signal = Signal(
        ticker_id=ticker.id,
        date=date.today(),
        signal_type=signal_type,
        confidence=round(confidence, 1),
        entry_price=Decimal(str(round(close, 4))),
        stop_loss=Decimal(str(round(stop_loss, 4))),
        take_profit=Decimal(str(round(take_profit, 4))),
        risk_reward_ratio=round(rr_ratio, 2) if risk_per_share > 0 else 0,
        position_size=round(position_size, 0),
        risk_rating=risk_rating,
        expected_hold_days=10,
        reasoning=reasoning,
        ta_score=ta_score,
        fundamental_score=mf_score,
        sentiment_score_val=sent_score,
        macro_score=macro_score,
        is_active=True,
    )

    return signal
