#!/usr/bin/env python3
"""Host-seitiger OHLCV-Fetcher.

Wird direkt auf dem Mac ausgefuehrt (nicht im Docker), weil Yahoo Finance
Docker-IPs aggressiv rate-limited. Schreibt OHLCV-Daten und berechnet
Indikatoren direkt in die Postgres-DB (exposed auf 127.0.0.1:5432).

Usage:
  python3 scripts/fetch_missing_ohlcv.py          # alle Watchlist-Ticker ohne Daten
  python3 scripts/fetch_missing_ohlcv.py DHL.DE RWE.DE  # spezifische Ticker
"""
import sys
import os
import subprocess

# Dependencies installieren falls noetig
try:
    import yfinance as yf
    import pandas as pd
    import psycopg2
except ImportError:
    print("Installiere Dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "-q",
                    "yfinance", "pandas", "psycopg2-binary"], check=True)
    import yfinance as yf
    import pandas as pd
    import psycopg2

# pandas-ta optional: Indikatoren werden sonst im Docker berechnet
try:
    import pandas_ta as ta
    HAS_TA = True
except ImportError:
    HAS_TA = False
    print("Hinweis: pandas-ta nicht verfuegbar — Indikatoren werden vom Docker-Task berechnet\n")

import math
from datetime import date

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "trading",
    "user": "trading",
    "password": os.environ.get("POSTGRES_PASSWORD", "trading_secret"),
}


def safe_float(val):
    if val is None:
        return None
    try:
        f = float(val)
        return None if math.isnan(f) else f
    except (ValueError, TypeError):
        return None


def ensure_ticker(cur, symbol: str, info: dict) -> int:
    cur.execute("SELECT id FROM tickers WHERE symbol = %s", (symbol,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute(
        """INSERT INTO tickers (symbol, name, sector, industry, market_cap, exchange, country, is_active, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, true, NOW(), NOW()) RETURNING id""",
        (
            symbol,
            info.get("longName") or info.get("shortName") or symbol,
            info.get("sector"),
            info.get("industry"),
            safe_float(info.get("marketCap")),
            info.get("exchange"),
            info.get("country"),
        ),
    )
    return cur.fetchone()[0]


def insert_ohlcv(cur, ticker_id: int, hist) -> int:
    count = 0
    for idx, row in hist.iterrows():
        d = idx.date()
        cur.execute(
            "SELECT 1 FROM ohlcv_data WHERE ticker_id = %s AND date = %s",
            (ticker_id, d),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """INSERT INTO ohlcv_data (ticker_id, date, open, high, low, close, adj_close, volume, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
            (
                ticker_id, d,
                float(row["Open"]), float(row["High"]), float(row["Low"]),
                float(row["Close"]),
                float(row.get("Adj Close", row["Close"])),
                int(row["Volume"]) if pd.notna(row["Volume"]) else 0,
            ),
        )
        count += 1
    return count


def compute_indicators(cur, ticker_id: int) -> int:
    if not HAS_TA:
        return 0
    cur.execute(
        "SELECT date, open, high, low, close, volume FROM ohlcv_data WHERE ticker_id = %s ORDER BY date",
        (ticker_id,),
    )
    rows = cur.fetchall()
    if len(rows) < 200:
        return 0

    df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df.set_index("date", inplace=True)

    df["rsi_14"] = ta.rsi(df["close"], length=14)
    macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
    df["macd"] = macd.iloc[:, 0]
    df["macd_signal"] = macd.iloc[:, 1]
    df["macd_histogram"] = macd.iloc[:, 2]
    df["ema_21"] = ta.ema(df["close"], length=21)
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    bbands = ta.bbands(df["close"], length=20)
    df["bb_upper"] = bbands.iloc[:, 2]
    df["bb_middle"] = bbands.iloc[:, 1]
    df["bb_lower"] = bbands.iloc[:, 0]
    df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    df["obv"] = ta.obv(df["close"], df["volume"])
    stoch = ta.stoch(df["high"], df["low"], df["close"])
    df["stoch_k"] = stoch.iloc[:, 0]
    df["stoch_d"] = stoch.iloc[:, 1]

    count = 0
    for idx, row in df.tail(30).iterrows():
        cur.execute(
            "SELECT 1 FROM indicators WHERE ticker_id = %s AND date = %s",
            (ticker_id, idx),
        )
        if cur.fetchone():
            continue
        cur.execute(
            """INSERT INTO indicators (ticker_id, date, rsi_14, macd, macd_signal, macd_histogram,
               ema_21, ema_50, ema_200, bb_upper, bb_middle, bb_lower, atr_14, obv, stoch_k, stoch_d, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
            (
                ticker_id, idx,
                safe_float(row.get("rsi_14")), safe_float(row.get("macd")),
                safe_float(row.get("macd_signal")), safe_float(row.get("macd_histogram")),
                safe_float(row.get("ema_21")), safe_float(row.get("ema_50")),
                safe_float(row.get("ema_200")), safe_float(row.get("bb_upper")),
                safe_float(row.get("bb_middle")), safe_float(row.get("bb_lower")),
                safe_float(row.get("atr_14")), safe_float(row.get("obv")),
                safe_float(row.get("stoch_k")), safe_float(row.get("stoch_d")),
            ),
        )
        count += 1
    return count


def fetch_ticker(symbol: str, cur) -> bool:
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1y")
        if hist.empty:
            print(f"  {symbol:12s} LEER")
            return False

        try:
            info = t.info
        except Exception:
            info = {}

        ticker_id = ensure_ticker(cur, symbol, info)
        ohlcv_count = insert_ohlcv(cur, ticker_id, hist)
        ind_count = compute_indicators(cur, ticker_id)
        print(f"  {symbol:12s} OK — {ohlcv_count} OHLCV + {ind_count} Indikatoren, letzter Kurs: {hist['Close'].iloc[-1]:.2f}")
        return True
    except Exception as e:
        print(f"  {symbol:12s} FEHLER: {str(e)[:80]}")
        return False


def main():
    # .env laden falls vorhanden (fuer POSTGRES_PASSWORD)
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k, v)
        DB_CONFIG["password"] = os.environ.get("POSTGRES_PASSWORD", "trading_secret")

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # Symbole bestimmen
    refresh_all = "--all" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        symbols = [s.upper() for s in args]
        print(f"Fetche {len(symbols)} spezifische Ticker...")
    elif refresh_all:
        cur.execute("""
            SELECT t.symbol FROM tickers t JOIN watchlist w ON w.ticker_id = t.id ORDER BY t.symbol
        """)
        symbols = [r[0] for r in cur.fetchall()]
        print(f"Refresh aller {len(symbols)} Watchlist-Ticker...")
    else:
        # Alle Ticker ohne aktuelle Daten (aelter als heute)
        cur.execute("""
            SELECT t.symbol
            FROM tickers t
            JOIN watchlist w ON w.ticker_id = t.id
            LEFT JOIN LATERAL (
                SELECT MAX(date) AS max_date FROM ohlcv_data WHERE ticker_id = t.id
            ) o ON true
            WHERE o.max_date IS NULL OR o.max_date < CURRENT_DATE
            ORDER BY t.symbol
        """)
        symbols = [r[0] for r in cur.fetchall()]
        print(f"Fetche {len(symbols)} Watchlist-Ticker ohne heutige Daten...")

    if not symbols:
        print("Nichts zu tun.")
        return

    success = 0
    for i, sym in enumerate(symbols):
        if fetch_ticker(sym, cur):
            success += 1
        conn.commit()
        # Rate-Limit safety: kleiner Delay zwischen Requests
        if i < len(symbols) - 1:
            import time
            time.sleep(1)

    cur.close()
    conn.close()
    print(f"\n{success}/{len(symbols)} erfolgreich")


if __name__ == "__main__":
    main()
