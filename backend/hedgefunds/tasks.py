from core.celery_app import app
from core.database import SessionLocal
from hedgefunds.edgar import scan_all_funds
import structlog

logger = structlog.get_logger()


@app.task(name="hedgefunds.tasks.scan_new_filings")
def scan_new_filings():
    db = SessionLocal()
    try:
        scan_all_funds(db)
        logger.info("hedgefunds.scanned")
    except Exception as e:
        logger.error("hedgefunds.scan_failed", error=str(e))
    finally:
        db.close()
