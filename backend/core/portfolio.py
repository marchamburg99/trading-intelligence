"""Portfolio-Kapital: Startkapital + realisierte P&L."""
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.models import PortfolioSettings, JournalEntry


def get_portfolio_settings(db: Session) -> PortfolioSettings:
    """Hole oder erstelle Portfolio-Settings (Singleton)."""
    settings = db.query(PortfolioSettings).first()
    if not settings:
        settings = PortfolioSettings(initial_capital=10000)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def get_current_capital(db: Session) -> float:
    """Aktuelles Kapital = Startkapital + realisierte P&L."""
    settings = get_portfolio_settings(db)
    initial = float(settings.initial_capital)

    realized_pnl = (
        db.query(func.coalesce(func.sum(JournalEntry.pnl), 0))
        .filter(JournalEntry.is_closed == True)
        .scalar()
    )

    return round(initial + float(realized_pnl), 2)
