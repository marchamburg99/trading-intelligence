from core.celery_app import app
from core.database import SessionLocal
from core.models import Watchlist, Ticker
from sentiment.engine import update_sentiment_for_ticker, analyze_news_sentiment
import structlog

logger = structlog.get_logger()


@app.task(name="sentiment.tasks.fetch_news_sentiment")
def fetch_news_sentiment():
    db = SessionLocal()
    try:
        watchlist = db.query(Watchlist).join(Ticker).all()
        for w in watchlist:
            try:
                analyze_news_sentiment(w.ticker.symbol, db)
                logger.info("sentiment.news_fetched", symbol=w.ticker.symbol)
            except Exception as e:
                logger.error("sentiment.news_failed", symbol=w.ticker.symbol, error=str(e))
    finally:
        db.close()


@app.task(name="sentiment.tasks.fetch_reddit_sentiment")
def fetch_reddit_sentiment():
    db = SessionLocal()
    try:
        watchlist = db.query(Watchlist).join(Ticker).all()
        for w in watchlist:
            try:
                update_sentiment_for_ticker(w.ticker.symbol, db)
                logger.info("sentiment.updated", symbol=w.ticker.symbol)
            except Exception as e:
                logger.error("sentiment.failed", symbol=w.ticker.symbol, error=str(e))
    finally:
        db.close()
