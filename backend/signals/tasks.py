from core.celery_app import app
from core.database import SessionLocal
from core.models import Watchlist, Ticker, Signal
from signals.engine import generate_signal
import structlog

logger = structlog.get_logger()


@app.task(name="signals.tasks.update_all_signals")
def update_all_signals():
    """Aktualisiere Signale für alle Watchlist-Titel."""
    db = SessionLocal()
    try:
        watchlist = db.query(Watchlist).join(Ticker).all()
        for w in watchlist:
            try:
                # Alte Signale deaktivieren
                db.query(Signal).filter(
                    Signal.ticker_id == w.ticker_id, Signal.is_active == True
                ).update({"is_active": False})

                signal = generate_signal(w.ticker.symbol, db)
                if signal:
                    db.add(signal)
                    db.commit()
                    logger.info(
                        "signal.generated",
                        symbol=w.ticker.symbol,
                        type=signal.signal_type.value,
                        confidence=signal.confidence,
                    )
            except Exception as e:
                db.rollback()
                logger.error("signal.failed", symbol=w.ticker.symbol, error=str(e))
    finally:
        db.close()
