"""Sentiment Engine: News, Reddit, Fear & Greed, Put/Call Ratio."""
import structlog
from datetime import date, datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.config import get_settings
from core.models import Ticker, SentimentScore, NewsItem

logger = structlog.get_logger()
settings = get_settings()
vader = SentimentIntensityAnalyzer()


def analyze_news_sentiment(symbol: str, db: Session) -> float | None:
    """Sentiment-Score aus NewsAPI für einen Ticker."""
    if not settings.newsapi_key:
        return None

    from newsapi import NewsApiClient

    newsapi = NewsApiClient(api_key=settings.newsapi_key)
    articles = newsapi.get_everything(
        q=symbol,
        language="en",
        sort_by="publishedAt",
        page_size=20,
    )

    if not articles.get("articles"):
        return None

    scores = []
    for article in articles["articles"]:
        text = f"{article.get('title', '')} {article.get('description', '')}"
        vs = vader.polarity_scores(text)
        scores.append(vs["compound"])

        # News-Item speichern
        existing = db.query(NewsItem).filter(NewsItem.url == article.get("url")).first()
        if not existing:
            db.add(NewsItem(
                title=article.get("title", "")[:500],
                source=article.get("source", {}).get("name"),
                url=article.get("url"),
                published_at=datetime.fromisoformat(article["publishedAt"].replace("Z", "+00:00")) if article.get("publishedAt") else None,
                content=article.get("description"),
                sentiment=vs["compound"],
                related_symbols=[symbol],
            ))

    db.commit()
    return sum(scores) / len(scores) if scores else None


def analyze_reddit_sentiment(symbol: str) -> tuple[float, int] | None:
    """Sentiment und Mentions-Volumen aus Reddit."""
    if not settings.reddit_client_id:
        return None

    import praw

    reddit = praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
    )

    subreddits = ["investing", "stocks", "wallstreetbets"]
    scores = []
    mention_count = 0

    for sub_name in subreddits:
        try:
            subreddit = reddit.subreddit(sub_name)
            for submission in subreddit.search(symbol, time_filter="week", limit=25):
                text = f"{submission.title} {submission.selftext[:500]}"
                vs = vader.polarity_scores(text)
                scores.append(vs["compound"])
                mention_count += 1
        except Exception as e:
            logger.warning("reddit_subreddit_fetch_failed", subreddit=sub_name, symbol=symbol, error=str(e))
            continue

    if not scores:
        return None

    avg_sentiment = sum(scores) / len(scores)
    return avg_sentiment, mention_count


def compute_composite_sentiment(
    news_sent: float | None,
    reddit_sent: float | None,
    reddit_mentions: int = 0,
    fear_greed: float | None = None,
    put_call: float | None = None,
) -> float:
    """Berechne Composite Sentiment Score (0-100)."""
    components = []
    weights = []

    if news_sent is not None:
        # Normalisiere von [-1, 1] auf [0, 100]
        components.append((news_sent + 1) * 50)
        weights.append(0.35)

    if reddit_sent is not None:
        components.append((reddit_sent + 1) * 50)
        weights.append(0.25)

    if fear_greed is not None:
        components.append(fear_greed)
        weights.append(0.25)

    if put_call is not None:
        # Hohe Put/Call = bearish → niedrigerer Score
        pcr_score = max(0, min(100, 100 - (put_call * 50)))
        components.append(pcr_score)
        weights.append(0.15)

    if not components:
        return 50.0

    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    return sum(c * w for c, w in zip(components, normalized_weights))


def update_sentiment_for_ticker(symbol: str, db: Session) -> SentimentScore | None:
    """Vollständiges Sentiment-Update für einen Ticker."""
    ticker = db.query(Ticker).filter(Ticker.symbol == symbol).first()
    if not ticker:
        return None

    news_sent = analyze_news_sentiment(symbol, db)

    reddit_result = analyze_reddit_sentiment(symbol)
    reddit_sent = reddit_result[0] if reddit_result else None
    reddit_mentions = reddit_result[1] if reddit_result else 0

    composite = compute_composite_sentiment(
        news_sent=news_sent,
        reddit_sent=reddit_sent,
        reddit_mentions=reddit_mentions,
    )

    score = SentimentScore(
        ticker_id=ticker.id,
        date=date.today(),
        news_sentiment=news_sent,
        reddit_sentiment=reddit_sent,
        reddit_mentions=reddit_mentions,
        composite_score=round(composite, 1),
    )
    db.add(score)
    db.commit()
    return score
