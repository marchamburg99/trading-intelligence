from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from core.models import Paper

router = APIRouter()


@router.get("/")
def get_papers(
    source: str | None = None,
    search: str | None = None,
    min_relevance: float = Query(0, ge=0, le=100),
    limit: int = Query(30, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Paper)
    if source:
        query = query.filter(Paper.source == source)
    if search:
        query = query.filter(
            Paper.title.ilike(f"%{search}%") | Paper.tags.cast(str).ilike(f"%{search}%")
        )
    if min_relevance > 0:
        query = query.filter(Paper.relevance_score >= min_relevance)

    papers = query.order_by(desc(Paper.published_date)).limit(limit).all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "authors": p.authors,
            "source": p.source,
            "url": p.url,
            "published_date": p.published_date.isoformat() if p.published_date else None,
            "ai_summary": p.ai_summary,
            "trading_implication": p.trading_implication,
            "relevance_score": p.relevance_score,
            "tags": p.tags,
        }
        for p in papers
    ]


@router.get("/{paper_id}")
def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    paper = db.query(Paper).get(paper_id)
    if not paper:
        return {"error": "Paper nicht gefunden"}
    return {
        "id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "source": paper.source,
        "url": paper.url,
        "published_date": paper.published_date.isoformat() if paper.published_date else None,
        "abstract": paper.abstract,
        "ai_summary": paper.ai_summary,
        "trading_implication": paper.trading_implication,
        "relevance_score": paper.relevance_score,
        "tags": paper.tags,
    }
