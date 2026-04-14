from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Text, Boolean,
    ForeignKey, Numeric, Index, Enum as SAEnum, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    AVOID = "AVOID"


class MacroStatus(str, enum.Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class Ticker(Base):
    __tablename__ = "tickers"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Numeric)
    exchange = Column(String(20))
    country = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    ohlcv = relationship("OHLCVData", back_populates="ticker", cascade="all, delete-orphan")
    indicators = relationship("Indicator", back_populates="ticker", cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="ticker", cascade="all, delete-orphan")
    sentiment_scores = relationship("SentimentScore", back_populates="ticker", cascade="all, delete-orphan")
    watchlist_entries = relationship("Watchlist", back_populates="ticker", cascade="all, delete-orphan")


class OHLCVData(Base):
    __tablename__ = "ohlcv_data"
    __table_args__ = (
        Index("ix_ohlcv_symbol_date", "ticker_id", "date", unique=True),
    )

    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Numeric(12, 4))
    high = Column(Numeric(12, 4))
    low = Column(Numeric(12, 4))
    close = Column(Numeric(12, 4))
    adj_close = Column(Numeric(12, 4))
    volume = Column(Numeric)
    created_at = Column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="ohlcv")


class Indicator(Base):
    __tablename__ = "indicators"
    __table_args__ = (
        Index("ix_indicators_ticker_date", "ticker_id", "date", unique=True),
    )

    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date = Column(Date, nullable=False)
    rsi_14 = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    ema_21 = Column(Float)
    ema_50 = Column(Float)
    ema_200 = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)
    atr_14 = Column(Float)
    obv = Column(Numeric)
    stoch_k = Column(Float)
    stoch_d = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="indicators")


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("ix_signals_ticker_date", "ticker_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date = Column(Date, nullable=False)
    signal_type = Column(SAEnum(SignalType), nullable=False)
    confidence = Column(Float, nullable=False)  # 0-100
    entry_price = Column(Numeric(12, 4))
    stop_loss = Column(Numeric(12, 4))
    take_profit = Column(Numeric(12, 4))
    risk_reward_ratio = Column(Float)
    position_size = Column(Float)  # Anzahl Aktien
    risk_rating = Column(Integer)  # 1-5
    expected_hold_days = Column(Integer)
    reasoning = Column(Text)
    ta_score = Column(Float)  # Technischer Sub-Score
    fundamental_score = Column(Float)
    sentiment_score_val = Column(Float)
    macro_score = Column(Float)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="signals")


class HedgeFundFiling(Base):
    __tablename__ = "hedge_fund_filings"

    id = Column(Integer, primary_key=True)
    fund_name = Column(String(255), nullable=False, index=True)
    cik = Column(String(20), nullable=False)
    filing_date = Column(Date, nullable=False)
    report_date = Column(Date)
    accession_number = Column(String(50), unique=True, nullable=False)
    total_value = Column(Numeric)
    created_at = Column(DateTime, server_default=func.now())

    positions = relationship("HedgeFundPosition", back_populates="filing", cascade="all, delete-orphan")


class HedgeFundPosition(Base):
    __tablename__ = "hedge_fund_positions"
    __table_args__ = (
        Index("ix_hfp_filing_symbol", "filing_id", "symbol"),
    )

    id = Column(Integer, primary_key=True)
    filing_id = Column(Integer, ForeignKey("hedge_fund_filings.id"), nullable=False)
    symbol = Column(String(20), index=True)
    company_name = Column(String(255))
    cusip = Column(String(9))
    value = Column(Numeric)  # in Tausend USD
    shares = Column(Numeric)
    change_type = Column(String(20))  # NEW, INCREASED, DECREASED, UNCHANGED, EXIT
    change_percent = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    filing = relationship("HedgeFundFiling", back_populates="positions")


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    authors = Column(Text)
    source = Column(String(100))  # SSRN, AQR, Two Sigma, Man Institute
    url = Column(String(500), unique=True)
    published_date = Column(Date)
    abstract = Column(Text)
    ai_summary = Column(Text)
    trading_implication = Column(Text)
    relevance_score = Column(Float)  # 0-100
    tags = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    source = Column(String(100))
    url = Column(String(500))
    published_at = Column(DateTime)
    content = Column(Text)
    sentiment = Column(Float)  # -1 bis 1
    related_symbols = Column(JSON)  # ["AAPL", "MSFT"]
    created_at = Column(DateTime, server_default=func.now())


class SentimentScore(Base):
    __tablename__ = "sentiment_scores"
    __table_args__ = (
        Index("ix_sentiment_ticker_date", "ticker_id", "date"),
    )

    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    date = Column(Date, nullable=False)
    news_sentiment = Column(Float)  # -1 bis 1
    reddit_sentiment = Column(Float)
    reddit_mentions = Column(Integer)
    put_call_ratio = Column(Float)
    fear_greed_index = Column(Float)  # 0-100
    composite_score = Column(Float)  # 0-100
    created_at = Column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="sentiment_scores")


class MacroData(Base):
    __tablename__ = "macro_data"

    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    indicator = Column(String(50), nullable=False, index=True)  # CPI, FED_FUNDS, YIELD_SPREAD, NFP, VIX
    value = Column(Float, nullable=False)
    previous_value = Column(Float)
    status = Column(SAEnum(MacroStatus))
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_macro_indicator_date", "indicator", "date", unique=True),
    )


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    notes = Column(Text)
    alert_price_above = Column(Numeric(12, 4))
    alert_price_below = Column(Numeric(12, 4))
    created_at = Column(DateTime, server_default=func.now())

    ticker = relationship("Ticker", back_populates="watchlist_entries")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    trade_date = Column(Date, nullable=False)
    direction = Column(String(10))  # LONG, SHORT
    entry_price = Column(Numeric(12, 4))
    exit_price = Column(Numeric(12, 4))
    position_size = Column(Integer)
    stop_loss = Column(Numeric(12, 4))
    take_profit = Column(Numeric(12, 4))
    pnl = Column(Numeric(12, 2))
    pnl_percent = Column(Float)
    setup_type = Column(String(100))
    notes = Column(Text)
    lessons = Column(Text)
    screenshot_url = Column(String(500))
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20))
    strategy = Column(String(100))
    start_date = Column(Date)
    end_date = Column(Date)
    total_trades = Column(Integer)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    max_drawdown = Column(Float)
    sharpe_ratio = Column(Float)
    total_return = Column(Float)
    equity_curve = Column(JSON)  # [{date, equity}, ...]
    trade_log = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())
