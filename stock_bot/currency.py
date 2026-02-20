"""FX conversion helpers – convert instrument prices to base currency."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FINNHUB_BASE = "https://finnhub.io/api/v1"
AV_BASE = "https://www.alphavantage.co/query"
TIMEOUT = 15


# ---------------------------------------------------------------------------
# FX rate fetchers (spot)
# ---------------------------------------------------------------------------

def _finnhub_fx_rate(from_ccy: str, to_ccy: str) -> float | None:
    """Fetch FX rate from Finnhub forex/rates endpoint."""
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            f"{FINNHUB_BASE}/forex/rates",
            params={"token": api_key, "base": from_ccy},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        rate = data.get("quote", {}).get(to_ccy)
        if rate:
            return float(rate)
    except Exception:
        logger.debug("Finnhub FX failed for %s->%s", from_ccy, to_ccy, exc_info=True)
    return None


def _alphavantage_fx_rate(from_ccy: str, to_ccy: str) -> float | None:
    """Fetch FX rate from Alpha Vantage CURRENCY_EXCHANGE_RATE."""
    api_key = os.environ.get("ALPHAVANTAGE_API_KEY")
    if not api_key:
        return None
    try:
        resp = requests.get(
            AV_BASE,
            params={
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_ccy,
                "to_currency": to_ccy,
                "apikey": api_key,
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        rate = (
            data.get("Realtime Currency Exchange Rate", {}).get(
                "5. Exchange Rate"
            )
        )
        if rate:
            return float(rate)
    except Exception:
        logger.debug("AV FX failed for %s->%s", from_ccy, to_ccy, exc_info=True)
    return None


def _yfinance_fx_rate(from_ccy: str, to_ccy: str) -> float | None:
    """Fetch FX rate from yfinance ticker (e.g. EURUSD=X)."""
    import yfinance as yf

    ticker_str = f"{from_ccy}{to_ccy}=X"
    try:
        t = yf.Ticker(ticker_str)
        info = t.info or {}
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price:
            return float(price)
    except Exception:
        logger.debug("yfinance FX failed for %s", ticker_str, exc_info=True)
    return None


@lru_cache(maxsize=64)
def get_fx_rate(from_ccy: str, to_ccy: str) -> float:
    """Return the spot FX rate *from_ccy* → *to_ccy*.

    Priority: Finnhub → Alpha Vantage → yfinance.
    Returns 1.0 if currencies are the same; raises if no source works.
    """
    from_ccy = from_ccy.upper()
    to_ccy = to_ccy.upper()
    if from_ccy == to_ccy:
        return 1.0

    for fetcher in (_finnhub_fx_rate, _alphavantage_fx_rate, _yfinance_fx_rate):
        rate = fetcher(from_ccy, to_ccy)
        if rate is not None and rate > 0:
            logger.info(
                "FX %s→%s = %.6f (via %s)",
                from_ccy,
                to_ccy,
                rate,
                fetcher.__name__,
            )
            return rate

    logger.error("Could not fetch FX rate %s→%s – using 1.0", from_ccy, to_ccy)
    return 1.0


# ---------------------------------------------------------------------------
# Historical FX (for WTD / MTD conversions)
# ---------------------------------------------------------------------------

def get_fx_history(from_ccy: str, to_ccy: str, period: str = "1mo") -> pd.Series:
    """Return a pd.Series of daily FX rates (DatetimeIndex → float).

    Falls back to a flat series using the spot rate if history is unavailable.
    """
    from_ccy, to_ccy = from_ccy.upper(), to_ccy.upper()
    if from_ccy == to_ccy:
        return pd.Series(dtype=float)

    import yfinance as yf

    ticker_str = f"{from_ccy}{to_ccy}=X"
    try:
        t = yf.Ticker(ticker_str)
        hist = t.history(period=period)
        if not hist.empty:
            return hist["Close"]
    except Exception:
        logger.debug("FX history failed for %s", ticker_str, exc_info=True)

    # Fallback: flat series
    logger.warning(
        "FX history unavailable for %s→%s; using spot rate", from_ccy, to_ccy
    )
    return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# DataFrame converter
# ---------------------------------------------------------------------------

def convert_to_base(df: pd.DataFrame, base_currency: str) -> pd.DataFrame:
    """Convert price columns in *df* from their native currency to *base_currency*.

    Expects columns: last_price, prev_close, currency, fiftytwo_wk_low, fiftytwo_wk_high.
    Adds a column *fx_rate* and modifies price columns in-place.
    """
    base = base_currency.upper()
    price_cols = ["last_price", "prev_close", "fiftytwo_wk_low", "fiftytwo_wk_high"]
    fx_rates: list[float] = []

    for sym in df.index:
        ccy = str(df.at[sym, "currency"]).upper()
        rate = get_fx_rate(ccy, base)
        fx_rates.append(rate)
        for col in price_cols:
            val = df.at[sym, col]
            if pd.notna(val):
                df.at[sym, col] = float(val) * rate

    df["fx_rate"] = fx_rates
    df["currency"] = base
    return df

