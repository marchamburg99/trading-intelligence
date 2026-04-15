"""
Signal Engine v3: Multi-Factor + Institutional + Regime-Aware

Ueberarbeitung basierend auf Investment-Advisor-Review:
- Data Quality Tracking + Confidence Ceiling
- Dynamische R:R basierend auf VIX-Regime
- Risk Rating basierend auf echtem Risiko, nicht Confidence
- Fixed-Fractional Sizing statt Kelly mit fake Win-Prob
- Regime-Filter fuer kontraere Sentiment-Signale
- Institutional Age Decay
- Research Score entfernt (tokenistisch bei 5%)

Gewichtung v3:
  - Technical Analysis: 30%
  - Multi-Factor (Momentum + Trend): 30%
  - Institutional (13F Conviction): 20%
  - Makro/Regime: 15%
  - Sentiment (News, regime-gefiltert): 5%
"""
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from core.models import (
    Ticker, Indicator, Signal, SignalType, SentimentScore,
    MacroData, MacroStatus, OHLCVData,
    HedgeFundFiling, HedgeFundPosition,
)
from core.products import LEVERAGED_PRODUCTS, is_leveraged, get_leverage


# ============================================================
# 1. TECHNICAL ANALYSIS (30%)
# ============================================================

def compute_ta_score(ind: Indicator, close: float) -> tuple[float, list[str], float]:
    signals = []
    score = 50.0
    indicators_present = 0
    total_groups = 5  # RSI, MACD, EMA, BB, Stochastic

    if ind.rsi_14 is not None:
        indicators_present += 1
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
        indicators_present += 1
        if ind.macd > ind.macd_signal:
            score += 10
            signals.append("MACD bullish")
        else:
            score -= 10

    if ind.ema_21 and ind.ema_50 and ind.ema_200:
        indicators_present += 1
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
        indicators_present += 1
        bb_width = ind.bb_upper - ind.bb_lower
        if bb_width > 0:
            bb_pos = (close - ind.bb_lower) / bb_width
            if bb_pos < 0.2:
                score += 10
                signals.append("Nahe unterem BB")
            elif bb_pos > 0.8:
                score -= 10

    if ind.stoch_k is not None and ind.stoch_d is not None:
        indicators_present += 1
        if ind.stoch_k < 20 and ind.stoch_d < 20:
            score += 8
            signals.append("Stochastic oversold")
        elif ind.stoch_k > 80 and ind.stoch_d > 80:
            score -= 8

    coverage = indicators_present / total_groups
    return max(0, min(100, score)), signals, coverage


# ============================================================
# 2. MULTI-FACTOR SCORE (30%) — Momentum + Trend
# ============================================================

def compute_multifactor_score(ticker: Ticker, db: Session) -> tuple[float, list[str], float]:
    signals = []
    score = 50.0

    prices = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(desc(OHLCVData.date))
        .limit(260)
        .all()
    )

    if len(prices) < 60:
        return score, signals, 0.0

    current = float(prices[0].close)

    # 12-1 Monats-Momentum (Jegadeesh/Titman)
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

    # 20-Tage Short-Term Trend (konsistent mit Momentum, kein Mean-Reversion)
    if len(prices) >= 20:
        price_20d = float(prices[19].close)
        ret_20d = ((current - price_20d) / price_20d) * 100

        if ret_20d > 8:
            score += 5
        elif ret_20d < -8:
            score -= 5
            signals.append(f"20d Abwaertstrend ({ret_20d:+.1f}%)")

    # 50-Tage Trend-Staerke
    if len(prices) >= 50:
        price_50d = float(prices[49].close)
        ret_50d = ((current - price_50d) / price_50d) * 100
        if ret_50d > 15:
            score += 5
        elif ret_50d < -15:
            score -= 5

    # Market Cap (Size-Faktor)
    if ticker.market_cap:
        cap = float(ticker.market_cap)
        if cap > 200e9:
            score += 3
        elif cap > 50e9:
            score += 2
        elif cap < 2e9:
            score -= 3

    coverage = 1.0 if len(prices) >= 252 else 0.5
    return max(0, min(100, score)), signals, coverage


# ============================================================
# 3. INSTITUTIONAL SCORE (20%) — 13F Conviction + Age Decay
# ============================================================

def compute_institutional_score(symbol: str, db: Session) -> tuple[float, list[str], float]:
    signals = []
    score = 50.0

    latest_filings = (
        db.query(
            HedgeFundFiling.fund_name,
            func.max(HedgeFundFiling.id).label("latest_id"),
        )
        .group_by(HedgeFundFiling.fund_name)
        .subquery()
    )

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
        return score, signals, 0.0

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
        signals.append(f"{fund_count} Fonds haelt Position")
    elif total_funds >= 3:
        score += 8
        signals.append(f"{total_funds} Fonds (niedrige Conviction)")

    increased = [p for p, _, _ in conviction_positions if p.change_type in ("NEW", "INCREASED")]
    if increased:
        score += 10
        signals.append(f"{len(increased)} Fonds stocken auf")

    decreased = [p for p, _, _ in conviction_positions if p.change_type in ("DECREASED", "EXIT")]
    if decreased:
        score -= 10
        signals.append(f"{len(decreased)} Fonds reduzieren")

    # Age Decay: aeltere Filings weniger gewichten
    if conviction_positions:
        newest_filing_date = max(f.filing_date for _, f, _ in conviction_positions)
        age_days = (date.today() - newest_filing_date).days if newest_filing_date else 999
        if age_days > 120:
            decay = 0.5
            signals.append(f"13F-Daten veraltet ({age_days} Tage)")
        elif age_days > 90:
            decay = 0.7
            signals.append(f"13F-Daten {age_days} Tage alt")
        elif age_days > 60:
            decay = 0.85
        else:
            decay = 1.0
        score = 50 + (score - 50) * decay

    return max(0, min(100, score)), signals, 1.0


# ============================================================
# 4. MAKRO/REGIME SCORE (15%)
# ============================================================

def compute_macro_score(db: Session) -> tuple[float, list[str], float, float]:
    """Returns (score, signals, coverage, vix_value)."""
    signals = []
    score = 50.0
    vix_value = 20.0
    found = 0
    total = 3  # VIX, YIELD_SPREAD, FED_FUNDS

    vix = db.query(MacroData).filter(MacroData.indicator == "VIX").order_by(desc(MacroData.date)).first()
    if vix:
        found += 1
        vix_value = vix.value
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
            signals.append(f"VIX erhoeht ({vix.value:.1f})")

    ys = db.query(MacroData).filter(MacroData.indicator == "YIELD_SPREAD").order_by(desc(MacroData.date)).first()
    if ys:
        found += 1
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

    fed_data = (
        db.query(MacroData)
        .filter(MacroData.indicator == "FED_FUNDS")
        .order_by(desc(MacroData.date))
        .limit(3)
        .all()
    )
    if len(fed_data) >= 2:
        found += 1
        if fed_data[0].value < fed_data[1].value:
            score += 5
            signals.append("Fed senkt Zinsen — bullish")
        elif fed_data[0].value > fed_data[1].value:
            score -= 5

    coverage = found / total
    return max(0, min(100, score)), signals, coverage, vix_value


# ============================================================
# 5. SENTIMENT SCORE (5%) — Regime-gefiltert
# ============================================================

def compute_sentiment_score(sentiment: SentimentScore | None,
                            vix_value: float = 20.0) -> tuple[float, list[str], float]:
    signals = []

    if not sentiment:
        return 50.0, signals, 0.0

    score = 50.0
    found = 0
    total = 3  # news, PCR, fear_greed

    if sentiment.news_sentiment is not None:
        found += 1
        news_norm = (sentiment.news_sentiment + 1) * 50
        score = news_norm
        if sentiment.news_sentiment > 0.3:
            signals.append("Positiver Newsflow")
        elif sentiment.news_sentiment < -0.3:
            signals.append("Negativer Newsflow")

    # Kontraere Signale nur in nicht-krisenhaftem Umfeld
    if vix_value < 30:
        if sentiment.put_call_ratio is not None:
            found += 1
            pcr = sentiment.put_call_ratio
            if pcr > 1.5:
                score += 10
                signals.append(f"PCR extrem hoch ({pcr:.2f}) — Kontra-Kaufsignal")
            elif pcr < 0.6:
                score -= 10
                signals.append(f"PCR extrem niedrig ({pcr:.2f}) — Euphorie-Warnung")

        if sentiment.fear_greed_index is not None:
            found += 1
            fg = sentiment.fear_greed_index
            if fg < 20:
                score += 8
                signals.append("Extreme Angst — Kontra-Kaufgelegenheit")
            elif fg > 80:
                score -= 8
                signals.append("Extreme Gier — Vorsicht")
    else:
        # In Krise: Fear bestaetigt Baisse
        if sentiment.put_call_ratio is not None:
            found += 1
        if sentiment.fear_greed_index is not None:
            found += 1
            if sentiment.fear_greed_index < 20:
                score -= 5
                signals.append("Extreme Angst in Krise — KEIN Kontra-Signal")

    coverage = found / total
    return max(0, min(100, score)), signals, coverage


# ============================================================
# DYNAMIC RISK/REWARD
# ============================================================

def compute_dynamic_rr(close: float, atr: float, vix_value: float,
                       leveraged: bool) -> tuple[float, float]:
    """Returns (sl_multiplier, tp_multiplier) fuer ATR-basierte Levels."""
    if vix_value > 30:
        sl_mult, tp_mult = 2.0, 2.0
    elif vix_value > 25:
        sl_mult, tp_mult = 1.75, 2.5
    elif vix_value < 15:
        sl_mult, tp_mult = 1.25, 3.5
    else:
        sl_mult, tp_mult = 1.5, 3.0

    # Asset-Volatilitaet: hoehere ATR% = weiter SL, konservativeres TP
    atr_pct = (atr / close) * 100 if close > 0 else 2.0
    if atr_pct > 5:
        sl_mult *= 1.3
        tp_mult *= 0.85
    elif atr_pct > 3:
        sl_mult *= 1.1
        tp_mult *= 0.95

    if leveraged:
        sl_mult *= 0.8
        tp_mult *= 0.7

    return sl_mult, tp_mult


# ============================================================
# RISK RATING (echtes Risiko, nicht Confidence)
# ============================================================

def compute_risk_rating(
    close: float, atr: float, symbol: str,
    position_value: float, capital: float,
    vix_value: float, data_quality: float,
) -> int:
    """Risk Rating 1-5 basierend auf Volatilitaet, Leverage, Konzentration, VIX, Datenqualitaet."""
    risk_score = 0.0

    # Asset-Volatilitaet (30%)
    atr_pct = (atr / close) * 100 if close > 0 else 3.0
    risk_score += min(30, atr_pct * 6)

    # Leverage (25%)
    leverage = get_leverage(symbol)
    risk_score += min(25, (leverage - 1) * 12.5)

    # Konzentration (20%)
    concentration = (position_value / capital) if capital > 0 else 0
    risk_score += min(20, concentration * 100)

    # VIX-Regime (15%)
    if vix_value > 30:
        risk_score += 15
    elif vix_value > 25:
        risk_score += 10
    elif vix_value > 20:
        risk_score += 5

    # Datenqualitaet (10%)
    risk_score += (1 - data_quality) * 10

    if risk_score >= 60:
        return 5
    elif risk_score >= 45:
        return 4
    elif risk_score >= 30:
        return 3
    elif risk_score >= 15:
        return 2
    else:
        return 1


# ============================================================
# REASONING BUILDER
# ============================================================

def _build_reasoning(
    symbol, signal_type, confidence, close,
    ta_score, ta_signals, mf_score, mf_signals,
    inst_score, inst_signals, macro_score, macro_signals,
    sent_score, sent_signals,
    stop_loss, take_profit, risk_per_share, reward_per_share,
    ind, data_quality,
) -> str:
    parts = []

    if signal_type == SignalType.BUY:
        parts.append(f"KAUFEMPFEHLUNG fuer {symbol} bei ${close:.2f}.")
    elif signal_type == SignalType.SELL:
        parts.append(f"VERKAUFSEMPFEHLUNG fuer {symbol} bei ${close:.2f}.")
    elif signal_type == SignalType.AVOID:
        parts.append(f"{symbol} MEIDEN — zu viele Risikofaktoren.")
    else:
        if confidence >= 60:
            parts.append(f"{symbol} auf der Watchlist halten — nahe am Kaufsignal ({confidence:.0f}%).")
        elif confidence >= 50:
            parts.append(f"{symbol} neutral — kein klarer Einstiegspunkt.")
        else:
            parts.append(f"{symbol} unter Beobachtung — schwache Signallage ({confidence:.0f}%).")

    # Technische Lage
    ta_parts = []
    if ind.rsi_14 is not None:
        if ind.rsi_14 < 30:
            ta_parts.append(f"RSI bei {ind.rsi_14:.0f} (ueberverkauft)")
        elif ind.rsi_14 > 70:
            ta_parts.append(f"RSI bei {ind.rsi_14:.0f} (ueberkauft)")
        else:
            ta_parts.append(f"RSI bei {ind.rsi_14:.0f}")
    for s in ta_signals:
        if s not in str(ta_parts):
            ta_parts.append(s)
    if ta_parts:
        ta_label = "bullish" if ta_score >= 60 else "bearish" if ta_score <= 40 else "neutral"
        parts.append(f"Technisch {ta_label}: {', '.join(ta_parts[:3])}.")

    if mf_signals:
        parts.append(" ".join(mf_signals[:2]) + ".")

    if inst_signals:
        parts.append(" ".join(inst_signals[:2]) + ".")
    elif inst_score == 50:
        parts.append("Keine Hedge-Fund-Daten fuer diesen Ticker.")

    if macro_signals:
        parts.append("Makro: " + ", ".join(macro_signals[:2]) + ".")
    elif macro_score >= 55:
        parts.append("Makro-Umfeld unterstuetzend.")
    elif macro_score <= 45:
        parts.append("Makro-Gegenwind (erhoehte Vorsicht).")

    if sent_signals:
        parts.append(" ".join(sent_signals[:1]) + ".")

    if risk_per_share > 0 and reward_per_share > 0:
        rr = reward_per_share / risk_per_share
        risk_pct = (risk_per_share / close) * 100
        parts.append(
            f"Risk/Reward {rr:.1f}:1 — "
            f"Risiko ${risk_per_share:.2f}/Aktie ({risk_pct:.1f}%), "
            f"Ziel ${reward_per_share:.2f}/Aktie."
        )

    if data_quality < 0.5:
        parts.append(f"Datenabdeckung: {data_quality:.0%} — eingeschraenkte Signalqualitaet.")

    return " ".join(parts)


# ============================================================
# SIGNAL GENERATOR v3
# ============================================================

def generate_signal(symbol: str, db: Session, capital: float = 10000.0) -> Signal | None:
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

    # === Sub-Scores mit Coverage ===
    ta_score, ta_signals, ta_cov = compute_ta_score(ind, close)
    mf_score, mf_signals, mf_cov = compute_multifactor_score(ticker, db)
    inst_score, inst_signals, inst_cov = compute_institutional_score(symbol, db)
    macro_score, macro_signals, macro_cov, vix_value = compute_macro_score(db)

    sentiment = (
        db.query(SentimentScore)
        .filter(SentimentScore.ticker_id == ticker.id)
        .order_by(desc(SentimentScore.date))
        .first()
    )
    sent_score, sent_signals, sent_cov = compute_sentiment_score(sentiment, vix_value)

    # === Gewichtete Aggregation mit Data Quality ===
    factors = [
        (ta_score, 0.30, ta_cov),
        (mf_score, 0.30, mf_cov),
        (inst_score, 0.20, inst_cov),
        (macro_score, 0.15, macro_cov),
        (sent_score, 0.05, sent_cov),
    ]

    total_weight = sum(w * cov for _, w, cov in factors)
    if total_weight > 0:
        raw_confidence = sum(s * w * cov for s, w, cov in factors) / total_weight
    else:
        raw_confidence = 30.0

    max_weight = sum(w for _, w, _ in factors)
    data_quality = total_weight / max_weight

    # Confidence Ceiling: wenig Daten = gedeckelte Confidence
    confidence_ceiling = 40 + (60 * data_quality)
    confidence = min(raw_confidence, confidence_ceiling)

    # === Signal-Typ ===
    if confidence >= 68:
        signal_type = SignalType.BUY
    elif confidence >= 40:
        signal_type = SignalType.HOLD
    elif confidence >= 25:
        signal_type = SignalType.SELL
    else:
        signal_type = SignalType.AVOID

    # === Dynamische Stop-Loss & Take-Profit ===
    atr = ind.atr_14 or (close * 0.02)
    sym_is_lev = is_leveraged(symbol)
    sl_mult, tp_mult = compute_dynamic_rr(close, atr, vix_value, sym_is_lev)

    if signal_type in (SignalType.BUY, SignalType.HOLD):
        stop_loss = close - (sl_mult * atr)
        take_profit = close + (tp_mult * atr)
    else:
        stop_loss = close + (sl_mult * atr)
        take_profit = close - (tp_mult * atr)

    risk_per_share = abs(close - stop_loss)
    reward_per_share = abs(take_profit - close)
    risk_reward_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0

    # === Position Sizing: Fixed-Fractional mit Regime-Adjustment ===
    base_risk_pct = 0.01 if sym_is_lev else 0.02
    if vix_value > 30:
        risk_pct = base_risk_pct * 0.5
    elif vix_value > 25:
        risk_pct = base_risk_pct * 0.75
    else:
        risk_pct = base_risk_pct

    conf_scale = max(0.5, min(1.0, (confidence - 20) / 60))
    risk_pct *= conf_scale

    position_size = (capital * risk_pct) / risk_per_share if risk_per_share > 0 else 0

    # Volumen-Cap
    max_pct = 0.10 if sym_is_lev else 0.20
    if close > 0 and position_size > 0:
        max_shares = (capital * max_pct) / close
        position_size = min(position_size, max_shares)

    position_value = close * position_size

    # === Risk Rating (echtes Risiko) ===
    risk_rating = compute_risk_rating(
        close, atr, symbol, position_value, capital, vix_value, data_quality,
    )

    # === Reasoning ===
    reasoning = _build_reasoning(
        symbol, signal_type, confidence, close,
        ta_score, ta_signals, mf_score, mf_signals,
        inst_score, inst_signals, macro_score, macro_signals,
        sent_score, sent_signals,
        stop_loss, take_profit, risk_per_share, reward_per_share,
        ind, data_quality,
    )

    signal = Signal(
        ticker_id=ticker.id,
        date=date.today(),
        signal_type=signal_type,
        confidence=round(confidence, 1),
        entry_price=Decimal(str(round(close, 4))),
        stop_loss=Decimal(str(round(stop_loss, 4))),
        take_profit=Decimal(str(round(take_profit, 4))),
        risk_reward_ratio=round(risk_reward_ratio, 2),
        position_size=round(position_size, 0),
        risk_rating=risk_rating,
        expected_hold_days=10,
        reasoning=reasoning,
        ta_score=ta_score,
        fundamental_score=mf_score,
        sentiment_score_val=sent_score,
        macro_score=macro_score,
        is_active=True,
        data_quality=round(data_quality, 2),
    )

    return signal
