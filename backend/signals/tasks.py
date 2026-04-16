from core.celery_app import app
from core.database import SessionLocal
from core.models import Watchlist, Ticker, Signal
from core.portfolio import get_current_capital
from core.products import is_eu_tradeable
from signals.engine import generate_signal
import structlog
import redis
import json
from core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

ALERT_KEY = "signal_alerts"
ALERT_TTL = 86400  # 24 Stunden


@app.task(name="signals.tasks.update_all_signals")
def update_all_signals():
    """Aktualisiere Signale fuer alle Watchlist-Titel. Trackt Signal-Aenderungen."""
    db = SessionLocal()
    try:
        capital = get_current_capital(db)
        watchlist = db.query(Watchlist).join(Ticker).all()
        alerts = []

        for w in watchlist:
            # Nicht-EU-Ticker ueberspringen (US-ETFs, Leveraged etc.)
            if not is_eu_tradeable(w.ticker.symbol):
                continue
            try:
                # Altes Signal merken
                old_signal = (
                    db.query(Signal)
                    .filter(Signal.ticker_id == w.ticker_id, Signal.is_active == True)
                    .first()
                )
                old_type = old_signal.signal_type.value if old_signal else None
                old_conf = old_signal.confidence if old_signal else None

                # Alte Signale deaktivieren
                db.query(Signal).filter(
                    Signal.ticker_id == w.ticker_id, Signal.is_active == True
                ).update({"is_active": False})

                signal = generate_signal(w.ticker.symbol, db, capital)
                if signal:
                    db.add(signal)
                    db.commit()

                    new_type = signal.signal_type.value
                    new_conf = signal.confidence

                    # Signal-Aenderung erkennen
                    if old_type and old_type != new_type:
                        alert = {
                            "symbol": w.ticker.symbol,
                            "from": old_type,
                            "to": new_type,
                            "confidence": round(new_conf, 1),
                            "old_confidence": round(old_conf, 1) if old_conf else None,
                        }
                        alerts.append(alert)
                        logger.info("signal.changed", **alert)

                    logger.info(
                        "signal.generated",
                        symbol=w.ticker.symbol,
                        type=new_type,
                        confidence=new_conf,
                    )
            except Exception as e:
                db.rollback()
                logger.error("signal.failed", symbol=w.ticker.symbol, error=str(e))

        # Alerts in Redis speichern
        if alerts:
            existing = redis_client.get(ALERT_KEY)
            all_alerts = json.loads(existing) if existing else []
            all_alerts.extend(alerts)
            redis_client.setex(ALERT_KEY, ALERT_TTL, json.dumps(all_alerts[-50:]))
            logger.info("signal.alerts_stored", count=len(alerts))

    finally:
        db.close()
