"""Paper Aggregator: SSRN RSS, AQR, Two Sigma, Man Institute."""
import json
import feedparser
import anthropic
from datetime import date
from sqlalchemy.orm import Session

from core.config import get_settings
from core.models import Paper

settings = get_settings()

ARXIV_FEEDS = [
    "https://rss.arxiv.org/rss/q-fin",  # Quantitative Finance
    "https://rss.arxiv.org/rss/q-fin.PM",  # Portfolio Management
    "https://rss.arxiv.org/rss/q-fin.TR",  # Trading and Market Microstructure
    "https://rss.arxiv.org/rss/q-fin.ST",  # Statistical Finance
]


def fetch_ssrn_papers(db: Session):
    """Neue Papers von arXiv Quantitative Finance RSS-Feeds abrufen."""
    for feed_url in ARXIV_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:30]:
                url = entry.get("link", "")
                if not url or db.query(Paper).filter(Paper.url == url).first():
                    continue

                # Autoren extrahieren
                authors = entry.get("author", "")
                if hasattr(entry, "authors"):
                    authors = ", ".join(a.get("name", "") for a in entry.authors)

                published = None
                if entry.get("published_parsed"):
                    from time import mktime
                    from datetime import datetime
                    published = datetime.fromtimestamp(mktime(entry.published_parsed)).date()

                paper = Paper(
                    title=entry.get("title", "").replace("\n", " ").strip()[:500],
                    authors=authors[:500] if authors else "",
                    source="arXiv",
                    url=url,
                    abstract=entry.get("summary", "").replace("\n", " ").strip(),
                    published_date=published or date.today(),
                    tags=["quantitative-finance"],
                )
                db.add(paper)
            db.commit()
        except Exception:
            db.rollback()
            continue


def summarize_paper_with_claude(paper: Paper) -> dict | None:
    """Paper mit Claude API zusammenfassen."""
    if not settings.anthropic_api_key:
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Fasse folgendes Quantitative Finance Paper zusammen:

Titel: {paper.title}
Autoren: {paper.authors}
Abstract: {paper.abstract}

Antworte im JSON-Format:
{{
  "summary": "5 Bullet Points auf Deutsch (maximal)",
  "trading_implication": "Konkrete Trading-Implikation in 2 Sätzen",
  "relevance_score": 0-100,
  "tags": ["tag1", "tag2"]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        return json.loads(response_text.strip())
    except json.JSONDecodeError:
        return None


def process_unsummarized_papers(db: Session, limit: int = 5):
    """Papers ohne AI-Summary verarbeiten."""
    papers = (
        db.query(Paper)
        .filter(Paper.ai_summary.is_(None))
        .order_by(Paper.created_at.desc())
        .limit(limit)
        .all()
    )

    for paper in papers:
        result = summarize_paper_with_claude(paper)
        if result:
            paper.ai_summary = result.get("summary")
            paper.trading_implication = result.get("trading_implication")
            paper.relevance_score = result.get("relevance_score")
            paper.tags = result.get("tags", [])
            db.commit()
