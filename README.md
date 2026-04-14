# Trading Intelligence

Institutionelle Trading-Analyse-Plattform mit KI-gestützten Signalen, Hedge-Fund-Tracking und Makro-Dashboard.

## Setup (5 Schritte)

### 1. Repository klonen & .env erstellen
```bash
cp .env.example .env
# API-Keys in .env eintragen
```

### 2. Docker Compose starten
```bash
docker-compose up --build
```

### 3. Datenbank-Migration ausführen
```bash
docker-compose exec backend alembic revision --autogenerate -m "initial"
docker-compose exec backend alembic upgrade head
```

### 4. Erste Ticker zur Watchlist hinzufügen
```bash
curl -X POST http://localhost:8000/api/watchlist \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

### 5. Frontend öffnen
```
http://localhost:3000
```

## Architektur

| Service | Port | Beschreibung |
|---------|------|-------------|
| Frontend (React) | 3000 | Dashboard, Signale, Scanner, Journal |
| Backend (FastAPI) | 8000 | REST API, Signal Engine, AI Analyse |
| Celery Worker | — | Async Tasks (Datenabruf, Signale) |
| Celery Beat | — | Scheduler (15-Min-Intervall) |
| PostgreSQL | 5432 | Persistenz |
| Redis | 6379 | Cache & Task Queue |

## Module

- **Signal Engine** — Kombiniert TA (40%), Fundamental (30%), Sentiment (20%), Makro (10%)
- **Aggregator** — Yahoo Finance + Alpha Vantage Daten, pandas-ta Indikatoren
- **Hedge Fund Tracker** — SEC EDGAR 13F-Filings, Top 20 Funds, Cluster-Signale
- **Sentiment Engine** — NewsAPI + Reddit (PRAW) + VADER
- **Makro Dashboard** — FRED API (CPI, Fed Funds, Yield Curve, NFP) + VIX
- **Paper Aggregator** — SSRN RSS + Claude AI Zusammenfassungen
- **Backtest Engine** — Historische Signal-Simulation mit Equity-Kurve
- **AI Analyse** — Claude API für strukturierte Ticker-Analyse

## API Keys (kostenlose Tiers)

| Service | Key holen |
|---------|-----------|
| Alpha Vantage | alphavantage.co/support/#api-key |
| NewsAPI | newsapi.org/register |
| FRED | fred.stlouisfed.org/docs/api/api_key.html |
| Reddit | reddit.com/prefs/apps |
| Anthropic | console.anthropic.com |

## Tests

```bash
docker-compose exec backend pytest
```

---

*Keine Anlageberatung. Nur zu Informations- und Bildungszwecken.*
