import json
import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.config import get_settings
from core.models import Ticker, Indicator, OHLCVData, SentimentScore, MacroData

settings = get_settings()

SYSTEM_PROMPT = """Du bist ein institutioneller Trading-Research-Assistent, spezialisiert auf Aktien (US & Europa) und ETFs/Fonds für einen fortgeschrittenen Swing-Trader (Haltedauer: Tage bis Wochen).

Analysiere den bereitgestellten Ticker technisch (RSI, MACD, EMA 21/50/200, Bollinger Bands, Volumen) und fundamental (KGV, KBV, Wachstum, Sektor-Kontext). Berücksichtige den Makro-Kontext.

Antworte IMMER im folgenden JSON-Format:
{
  "signal_type": "BUY|SELL|HOLD|AVOID",
  "confidence": 0-100,
  "entry_price": number,
  "stop_loss": number,
  "take_profit": number,
  "risk_reward_ratio": number,
  "risk_rating": 1-5,
  "expected_hold_days": 3-21,
  "reasoning": "Max 5 Sätze Begründung",
  "key_risks": ["Risiko 1", "Risiko 2"],
  "technical_summary": "Kurze TA-Zusammenfassung",
  "macro_context": "Kurzer Makro-Kontext"
}

Regeln:
- BUY nur wenn ≥3 technische Signale + positiver Kontext
- Stop-Loss: 1.5x ATR unter Einstieg
- Take-Profit: Min. 1:2 Risk-Reward
- Bei VIX > 30: Warnung ausgeben, AVOID bevorzugen
- Disclaimer: Keine Anlageberatung, nur informative Analyse
"""


def analyze_ticker(symbol: str, capital: float, db: Session) -> dict:
    """Ruft Claude API für vollständige Ticker-Analyse auf."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        return {"error": f"Ticker {symbol} nicht in Datenbank"}

    # Daten sammeln
    indicator = (
        db.query(Indicator)
        .filter(Indicator.ticker_id == ticker.id)
        .order_by(desc(Indicator.date))
        .first()
    )

    last_prices = (
        db.query(OHLCVData)
        .filter(OHLCVData.ticker_id == ticker.id)
        .order_by(desc(OHLCVData.date))
        .limit(20)
        .all()
    )

    sentiment = (
        db.query(SentimentScore)
        .filter(SentimentScore.ticker_id == ticker.id)
        .order_by(desc(SentimentScore.date))
        .first()
    )

    vix = (
        db.query(MacroData)
        .filter(MacroData.indicator == "VIX")
        .order_by(desc(MacroData.date))
        .first()
    )

    # Context für Claude bauen
    context = {
        "symbol": symbol,
        "name": ticker.name,
        "sector": ticker.sector,
        "market_cap": float(ticker.market_cap) if ticker.market_cap else None,
        "portfolio_capital": capital,
    }

    if indicator:
        context["indicators"] = {
            "rsi_14": indicator.rsi_14,
            "macd": indicator.macd,
            "macd_signal": indicator.macd_signal,
            "ema_21": indicator.ema_21,
            "ema_50": indicator.ema_50,
            "ema_200": indicator.ema_200,
            "bb_upper": indicator.bb_upper,
            "bb_lower": indicator.bb_lower,
            "atr_14": indicator.atr_14,
            "stoch_k": indicator.stoch_k,
            "stoch_d": indicator.stoch_d,
        }

    if last_prices:
        context["recent_prices"] = [
            {"date": str(p.date), "close": float(p.close), "volume": float(p.volume) if p.volume else 0}
            for p in reversed(last_prices)
        ]

    if sentiment:
        context["sentiment"] = {
            "composite_score": sentiment.composite_score,
            "news_sentiment": sentiment.news_sentiment,
            "reddit_mentions": sentiment.reddit_mentions,
        }

    if vix:
        context["vix"] = vix.value

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Analysiere folgenden Ticker:\n\n{json.dumps(context, indent=2, default=str)}",
            }
        ],
    )

    response_text = message.content[0].text

    try:
        # JSON aus Antwort extrahieren
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        result = json.loads(response_text.strip())
    except json.JSONDecodeError:
        result = {"raw_response": response_text, "error": "Konnte JSON nicht parsen"}

    result["symbol"] = symbol
    result["model"] = "claude-sonnet-4-20250514"

    return result
