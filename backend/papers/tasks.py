from core.celery_app import app
from core.database import SessionLocal
from papers.aggregator import fetch_ssrn_papers, process_unsummarized_papers
import structlog

logger = structlog.get_logger()


@app.task(name="papers.tasks.fetch_new_papers")
def fetch_new_papers():
    db = SessionLocal()
    try:
        fetch_ssrn_papers(db)
        process_unsummarized_papers(db, limit=5)
        logger.info("papers.fetched")
    except Exception as e:
        logger.error("papers.fetch_failed", error=str(e))
    finally:
        db.close()
