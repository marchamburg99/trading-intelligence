"""Makro-Daten von FRED API und Yahoo Finance (VIX)."""
import structlog
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from core.config import get_settings
from core.models import MacroData, MacroStatus

logger = structlog.get_logger()
settings = get_settings()


def fetch_fred_series(series_id: str, indicator_name: str, db: Session):
    """Einzelne FRED-Serie abrufen und speichern."""
    if not settings.fred_api_key:
        return

    from fredapi import Fred

    fred = Fred(api_key=settings.fred_api_key)
    data = fred.get_series(series_id, observation_start=date.today() - timedelta(days=365))

    if data is None or data.empty:
        return

    for idx, value in data.items():
        if value is None:
            continue
        d = idx.date()
        existing = (
            db.query(MacroData)
            .filter(MacroData.indicator == indicator_name, MacroData.date == d)
            .first()
        )
        if existing:
            continue

        # Status bestimmen
        status = determine_status(indicator_name, float(value))

        # Vorheriger Wert
        prev = (
            db.query(MacroData)
            .filter(MacroData.indicator == indicator_name, MacroData.date < d)
            .order_by(desc(MacroData.date))
            .first()
        )

        db.add(MacroData(
            date=d,
            indicator=indicator_name,
            value=float(value),
            previous_value=prev.value if prev else None,
            status=status,
        ))

    db.commit()


def fetch_vix(db: Session):
    """VIX von Yahoo Finance abrufen."""
    from aggregator.yf_session import yf_safe_ticker

    vix = yf_safe_ticker("^VIX")
    hist = vix.history(period="3mo")

    for idx, row in hist.iterrows():
        d = idx.date()
        existing = (
            db.query(MacroData)
            .filter(MacroData.indicator == "VIX", MacroData.date == d)
            .first()
        )
        if existing:
            continue

        value = float(row["Close"])
        status = determine_status("VIX", value)

        db.add(MacroData(
            date=d,
            indicator="VIX",
            value=value,
            status=status,
        ))

    db.commit()


def determine_status(indicator: str, value: float) -> MacroStatus:
    """Bestimme Ampel-Status für Makro-Indikator."""
    thresholds = {
        "VIX": {"green": 20, "red": 30},
        "FED_FUNDS": {"green": 3, "red": 5.5},
        "YIELD_SPREAD": {"green": 0.5, "red": 0},  # Inversion = Rot
        "CPI": {"green": 2.5, "red": 4.0},
    }

    t = thresholds.get(indicator)
    if not t:
        return MacroStatus.YELLOW

    if indicator == "YIELD_SPREAD":
        if value < t["red"]:
            return MacroStatus.RED
        elif value > t["green"]:
            return MacroStatus.GREEN
        return MacroStatus.YELLOW

    if value <= t["green"]:
        return MacroStatus.GREEN
    elif value >= t["red"]:
        return MacroStatus.RED
    return MacroStatus.YELLOW


def fetch_all_macro(db: Session):
    """Alle Makro-Daten abrufen."""
    fred_series = {
        "CPIAUCSL": "CPI",
        "FEDFUNDS": "FED_FUNDS",
        "T10Y2Y": "YIELD_SPREAD",
        "PAYEMS": "NFP",
    }

    for series_id, name in fred_series.items():
        try:
            fetch_fred_series(series_id, name, db)
        except Exception as e:
            logger.warning("fred_series_fetch_failed", series_id=series_id, indicator=name, error=str(e))
            continue

    try:
        fetch_vix(db)
    except Exception as e:
        logger.warning("vix_fetch_failed", error=str(e))
