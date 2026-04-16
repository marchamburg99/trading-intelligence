from celery import Celery
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

app = Celery(
    "trading",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

app.conf.beat_schedule = {
    "fetch-watchlist-data": {
        "task": "aggregator.tasks.fetch_watchlist_data",
        "schedule": 900.0,  # 15 Minuten
    },
    "update-signals": {
        "task": "signals.tasks.update_all_signals",
        "schedule": 900.0,
    },
    "fetch-macro-data": {
        "task": "macro.tasks.fetch_macro_data",
        "schedule": crontab(minute=0, hour="*/6"),  # alle 6 Stunden
    },
    "fetch-news-sentiment": {
        "task": "sentiment.tasks.fetch_news_sentiment",
        "schedule": 1800.0,  # 30 Minuten
    },
    # Reddit-Sentiment deaktiviert: 0% Gewichtung im Signal-Score, verschwendet Ressourcen
    # "fetch-reddit-sentiment": {
    #     "task": "sentiment.tasks.fetch_reddit_sentiment",
    #     "schedule": 3600.0,
    # },
    "scan-13f-filings": {
        "task": "hedgefunds.tasks.scan_new_filings",
        "schedule": crontab(minute=0, hour=8),  # täglich 08:00 UTC
    },
    "fetch-papers": {
        "task": "papers.tasks.fetch_new_papers",
        "schedule": crontab(minute=0, hour=6),  # täglich 06:00 UTC
    },
    "run-discovery": {
        "task": "discovery.tasks.run_discovery",
        "schedule": crontab(minute=0, hour=5),  # täglich 05:00 UTC
    },
    "check-portfolio": {
        "task": "portfolio.tasks.check_portfolio",
        "schedule": 900.0,  # alle 15 Min (parallel zu Signal-Update)
    },
}

app.autodiscover_tasks([
    "aggregator",
    "signals",
    "sentiment",
    "macro",
    "hedgefunds",
    "papers",
    "backtest",
    "discovery",
    "portfolio",
])
