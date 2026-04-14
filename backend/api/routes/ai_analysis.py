import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import redis

from core.database import get_db
from core.config import get_settings
from ai.analyzer import analyze_ticker

router = APIRouter()
settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

RATE_LIMIT_KEY = "claude_api_requests"


class AnalyzeRequest(BaseModel):
    symbol: str
    portfolio_capital: float | None = None


@router.post("/")
def run_ai_analysis(req: AnalyzeRequest, db: Session = Depends(get_db)):
    current_minute = int(time.time() // 60)
    rate_key = f"{RATE_LIMIT_KEY}:{current_minute}"
    current = redis_client.incr(rate_key)
    if current == 1:
        redis_client.expire(rate_key, 120)
    if current > settings.claude_max_requests_per_minute:
        raise HTTPException(429, "Rate-Limit erreicht. Bitte warte eine Minute.")

    capital = req.portfolio_capital or settings.default_portfolio_capital
    result = analyze_ticker(req.symbol.upper(), capital, db)
    return result
