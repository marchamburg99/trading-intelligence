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
