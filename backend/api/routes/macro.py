from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.database import get_db
from core.models import MacroData

router = APIRouter()


@router.get("/")
def get_macro_overview(db: Session = Depends(get_db)):
    indicators = ["CPI", "FED_FUNDS", "YIELD_SPREAD", "NFP", "VIX"]
    result = {}
    for ind in indicators:
        latest = (
            db.query(MacroData)
            .filter(MacroData.indicator == ind)
            .order_by(desc(MacroData.date))
            .first()
        )
        if latest:
            result[ind] = {
                "value": latest.value,
                "previous": latest.previous_value,
                "status": latest.status.value if latest.status else None,
                "date": latest.date.isoformat(),
            }
    return result


@router.get("/history/{indicator}")
def get_macro_history(indicator: str, limit: int = 60, db: Session = Depends(get_db)):
    data = (
        db.query(MacroData)
        .filter(MacroData.indicator == indicator.upper())
        .order_by(desc(MacroData.date))
        .limit(limit)
        .all()
    )
    return [
        {"date": d.date.isoformat(), "value": d.value, "status": d.status.value if d.status else None}
        for d in reversed(data)
    ]


@router.get("/calendar")
def get_economic_calendar():
    """Statischer Wirtschaftskalender — wichtigste recurring Events."""
    from datetime import date, timedelta

    today = date.today()
    events = []

    # FOMC Meetings 2026 (feste Termine)
    fomc_dates = [
        "2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
        "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16",
    ]
    for d in fomc_dates:
        event_date = date.fromisoformat(d)
        if event_date >= today and event_date <= today + timedelta(days=90):
            events.append({"date": d, "event": "FOMC Zinsentscheid", "importance": "HIGH", "impact": "Zinsen, Marktvolatilität"})

    # CPI Release: ~10.-15. jeden Monats
    for m in range(today.month, today.month + 3):
        month = m if m <= 12 else m - 12
        year = today.year if m <= 12 else today.year + 1
        cpi_date = date(year, month, 13)
        if cpi_date >= today:
            events.append({"date": cpi_date.isoformat(), "event": "CPI Veröffentlichung", "importance": "HIGH", "impact": "Inflation, Fed-Erwartungen"})

    # NFP: erster Freitag jeden Monats
    for m in range(today.month, today.month + 3):
        month = m if m <= 12 else m - 12
        year = today.year if m <= 12 else today.year + 1
        first = date(year, month, 1)
        days_until_friday = (4 - first.weekday()) % 7
        nfp_date = first + timedelta(days=days_until_friday)
        if nfp_date >= today:
            events.append({"date": nfp_date.isoformat(), "event": "Non-Farm Payrolls", "importance": "HIGH", "impact": "Arbeitsmarkt, Fed-Politik"})

    # Earnings Season Marker
    earnings_starts = ["2026-01-12", "2026-04-13", "2026-07-13", "2026-10-12"]
    for d in earnings_starts:
        event_date = date.fromisoformat(d)
        if event_date >= today and event_date <= today + timedelta(days=90):
            events.append({"date": d, "event": "Earnings Season Start", "importance": "MEDIUM", "impact": "Volatilität bei Einzeltiteln"})

    events.sort(key=lambda x: x["date"])
    return events[:10]


@router.get("/ampel")
def get_macro_ampel(db: Session = Depends(get_db)):
    """Makro-Ampel: aggregierter Status aus allen Indikatoren."""
    indicators = ["CPI", "FED_FUNDS", "YIELD_SPREAD", "NFP", "VIX"]
    statuses = []
    for ind in indicators:
        latest = (
            db.query(MacroData)
            .filter(MacroData.indicator == ind)
            .order_by(desc(MacroData.date))
            .first()
        )
        if latest and latest.status:
            statuses.append(latest.status.value)

    if not statuses:
        return {"ampel": "YELLOW", "detail": "Keine Daten verfügbar"}

    red_count = statuses.count("RED")
    green_count = statuses.count("GREEN")

    if red_count >= 3:
        ampel = "RED"
    elif green_count >= 3:
        ampel = "GREEN"
    else:
        ampel = "YELLOW"

    return {"ampel": ampel, "indicators": dict(zip(indicators, statuses))}
