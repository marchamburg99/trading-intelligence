"""Discovery Celery Task: taeglich proaktives Market-Screening."""
import structlog
from core.celery_app import app
from core.database import SessionLocal
from core.models import DiscoverySuggestion
from discovery.screener import run_discovery_pipeline

logger = structlog.get_logger()


@app.task(name="discovery.tasks.run_discovery")
def run_discovery():
    """Fuehre Discovery-Pipeline aus und speichere Top-Vorschlaege."""
    db = SessionLocal()
    try:
        db.query(DiscoverySuggestion).delete()
        db.commit()

        suggestions = run_discovery_pipeline(db)
        for s in suggestions:
            db.add(s)
        db.commit()

        logger.info("discovery.task_complete", count=len(suggestions))
    except Exception as e:
        db.rollback()
        logger.error("discovery.task_failed", error=str(e))
        raise
    finally:
        db.close()
