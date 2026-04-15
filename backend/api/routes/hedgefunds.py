from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from core.database import get_db
from core.models import HedgeFundFiling, HedgeFundPosition

router = APIRouter()


@router.get("/filings")
def get_latest_filings(limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    filings = (
        db.query(HedgeFundFiling)
        .order_by(desc(HedgeFundFiling.filing_date))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": f.id,
            "fund_name": f.fund_name,
            "filing_date": f.filing_date.isoformat(),
            "report_date": f.report_date.isoformat() if f.report_date else None,
            "total_value": float(f.total_value) if f.total_value else None,
            "position_count": len(f.positions),
        }
        for f in filings
    ]


@router.get("/filings/{filing_id}/positions")
def get_filing_positions(filing_id: int, db: Session = Depends(get_db)):
    positions = (
        db.query(HedgeFundPosition)
        .filter(HedgeFundPosition.filing_id == filing_id)
        .order_by(desc(HedgeFundPosition.value))
        .all()
    )
    return [
        {
            "symbol": p.symbol,
            "company_name": p.company_name,
            "value": float(p.value) if p.value else None,
            "shares": float(p.shares) if p.shares else None,
            "change_type": p.change_type,
            "change_percent": p.change_percent,
        }
        for p in positions
    ]


@router.get("/clusters")
def get_cluster_signals(min_funds: int = Query(3, ge=2), db: Session = Depends(get_db)):
    """Finde Aktien, die von mehreren Top-Funds gleichzeitig gekauft werden."""
    clusters = (
        db.query(
            HedgeFundPosition.symbol,
            func.count(func.distinct(HedgeFundFiling.fund_name)).label("fund_count"),
            func.sum(HedgeFundPosition.value).label("total_value"),
        )
        .join(HedgeFundFiling)
        .filter(HedgeFundPosition.symbol.isnot(None))
        .group_by(HedgeFundPosition.symbol)
        .having(func.count(func.distinct(HedgeFundFiling.fund_name)) >= min_funds)
        .order_by(desc("fund_count"))
        .all()
    )
    return [
        {
            "symbol": c.symbol,
            "fund_count": c.fund_count,
            "total_value": float(c.total_value) if c.total_value else None,
        }
        for c in clusters
    ]
