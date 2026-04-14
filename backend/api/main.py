from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import (
    signals,
    watchlist,
    tickers,
    macro,
    hedgefunds,
    papers,
    sentiment,
    backtest,
    journal,
    ai_analysis,
    scanner,
    dashboard,
    quotes,
)

app = FastAPI(
    title="Trading Intelligence API",
    version="1.0.0",
    description="Institutionelle Trading-Analyse mit KI-gestützten Signalen",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["Watchlist"])
app.include_router(tickers.router, prefix="/api/tickers", tags=["Tickers"])
app.include_router(macro.router, prefix="/api/macro", tags=["Macro"])
app.include_router(hedgefunds.router, prefix="/api/hedgefunds", tags=["Hedge Funds"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["Sentiment"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtest"])
app.include_router(journal.router, prefix="/api/journal", tags=["Journal"])
app.include_router(ai_analysis.router, prefix="/api/analyze", tags=["AI Analysis"])
app.include_router(scanner.router, prefix="/api/scanner", tags=["Scanner"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(quotes.router, prefix="/api/quotes", tags=["Quotes"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
