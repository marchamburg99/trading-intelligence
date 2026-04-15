"""Shared yfinance Session mit Retry-Logik fuer Docker-Umgebungen."""
import time
import structlog
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = structlog.get_logger()

_session = None


def get_session() -> requests.Session:
    """Shared HTTP Session mit Retry + Connection Pooling."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=10,
            pool_maxsize=10,
        )
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
        _session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
    return _session


def yf_safe_download(tickers: list[str] | str, **kwargs) -> "pd.DataFrame":
    """yf.download mit shared Session und Retry."""
    import yfinance as yf
    session = get_session()
    kwargs.setdefault("session", session)
    kwargs.setdefault("threads", False)
    kwargs.setdefault("progress", False)
    return yf.download(tickers=tickers, **kwargs)


def yf_safe_ticker(symbol: str) -> "yf.Ticker":
    """yf.Ticker mit shared Session."""
    import yfinance as yf
    session = get_session()
    return yf.Ticker(symbol, session=session)
