"""Portfolio-Check als wiederkehrender Celery-Task.

Laeuft alle 15 Min parallel zu update-signals, analysiert alle
persistenten Holdings und generiert Alerts bei Action-Wechseln.
"""
import json
from datetime import datetime
import redis
import structlog
from core.celery_app import app
from core.database import SessionLocal
from core.config import get_settings
from core.models import PortfolioHolding
from api.routes.portfolio import analyze_all_holdings

logger = structlog.get_logger()
settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

ALERT_KEY = "portfolio_alerts"
ALERT_TTL = 86400  # 24h

# Kritische Actions die einen Alert triggern
CRITICAL_ACTIONS = {"VERKAUFEN", "SOFORT_VERKAUFEN", "STOP_LOSS", "AUFSTOCKEN"}


@app.task(name="portfolio.tasks.check_portfolio")
def check_portfolio():
    db = SessionLocal()
    try:
        holdings = db.query(PortfolioHolding).all()
        if not holdings:
            logger.info("portfolio.empty")
            return

        result = analyze_all_holdings(db)
        alerts = []
        now = datetime.utcnow()

        for pos in result["positions"]:
            holding = next((h for h in holdings if h.id == pos["id"]), None)
            if not holding:
                continue

            new_action = pos.get("action")
            old_action = holding.last_action

            # Alert bei Action-Wechsel zu kritischer Action
            if new_action and new_action != old_action and new_action in CRITICAL_ACTIONS:
                alerts.append({
                    "symbol": pos["symbol"],
                    "from": old_action,
                    "to": new_action,
                    "reason": pos.get("reason"),
                    "current_price": pos.get("current_price"),
                    "unrealized_pct": pos.get("unrealized_pct"),
                    "timestamp": now.isoformat(),
                })

            holding.last_action = new_action
            holding.last_check_at = now

        db.commit()

        if alerts:
            existing = redis_client.get(ALERT_KEY)
            all_alerts = json.loads(existing) if existing else []
            all_alerts.extend(alerts)
            # Nur letzte 50 behalten
            redis_client.setex(ALERT_KEY, ALERT_TTL, json.dumps(all_alerts[-50:]))
            logger.info("portfolio.alerts_generated", count=len(alerts))

        logger.info(
            "portfolio.check_complete",
            positions=result["total_positions"],
            value=result["total_value"],
            pnl=result["total_pnl"],
            actions=result["action_summary"],
        )
    except Exception as e:
        db.rollback()
        logger.error("portfolio.check_failed", error=str(e))
        raise
    finally:
        db.close()
