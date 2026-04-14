from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from core.models import SentimentScore, Ticker

router = APIRouter()


@router.get("/{symbol}")
def get_sentiment(symbol: str, db: Session = Depends(get_db)):
    score = (
        db.query(SentimentScore)
        .join(Ticker)
        .filter(Ticker.symbol == symbol.upper())
        .order_by(desc(SentimentScore.date))
        .first()
    )
    if not score:
        return {"error": "Kein Sentiment-Score verfügbar"}

    return {
        "symbol": symbol.upper(),
        "date": score.date.isoformat(),
        "news_sentiment": score.news_sentiment,
        "reddit_sentiment": score.reddit_sentiment,
        "reddit_mentions": score.reddit_mentions,
        "put_call_ratio": score.put_call_ratio,
        "fear_greed_index": score.fear_greed_index,
        "composite_score": score.composite_score,
    }


@router.get("/")
def get_sentiment_heatmap(db: Session = Depends(get_db)):
    """Sentiment-Heatmap für alle Watchlist-Titel."""
    from core.models import Watchlist

    watchlist_tickers = db.query(Watchlist.ticker_id).subquery()
    scores = (
        db.query(SentimentScore)
        .join(Ticker)
        .filter(SentimentScore.ticker_id.in_(watchlist_tickers))
        .order_by(desc(SentimentScore.date))
        .all()
    )

    seen = set()
    result = []
    for s in scores:
        if s.ticker_id in seen:
            continue
        seen.add(s.ticker_id)
        result.append({
            "symbol": s.ticker.symbol,
            "composite_score": s.composite_score,
            "news_sentiment": s.news_sentiment,
            "reddit_mentions": s.reddit_mentions,
        })
    return result
