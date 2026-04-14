from core.celery_app import app
from core.database import SessionLocal
from macro.fetcher import fetch_all_macro
import structlog

logger = structlog.get_logger()


@app.task(name="macro.tasks.fetch_macro_data")
def fetch_macro_data():
    db = SessionLocal()
    try:
        fetch_all_macro(db)
        logger.info("macro.fetched")
    except Exception as e:
        logger.error("macro.fetch_failed", error=str(e))
    finally:
        db.close()
