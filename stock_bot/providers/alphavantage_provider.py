"""Alpha Vantage provider – requires ALPHAVANTAGE_API_KEY env var."""

from __future__ import annotations

import logging
import os

import pandas as pd
import requests

from stock_bot.providers.base import StockProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://www.alphavantage.co/query"
TIMEOUT = 15


class AlphaVantageProvider(StockProvider):
    """Uses Alpha Vantage REST API for stock quotes and history."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("ALPHAVANTAGE_API_KEY", "")
        if not self.api_key:
            raise ValueError("ALPHAVANTAGE_API_KEY not set")

    def _get(self, params: dict) -> dict:
        params["apikey"] = self.api_key
        resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # ---- interface ----
    def get_snapshot(self, symbols: list[str]) -> pd.DataFrame:
        rows: list[dict] = []
        for sym in symbols:
            try:
                data = self._get({"function": "GLOBAL_QUOTE", "symbol": sym})
                gq = data.get("Global Quote", {})
                # Try overview for currency + 52-wk range
                overview: dict = {}
                try:
                    overview = self._get({"function": "OVERVIEW", "symbol": sym})
                except Exception:
                    pass
                rows.append(
                    {
                        "symbol": sym,
                        "last_price": _float(gq.get("05. price")),
                        "prev_close": _float(gq.get("08. previous close")),
                        "currency": (overview.get("Currency") or "USD").upper(),
                        "fiftytwo_wk_low": _float(overview.get("52WeekLow")),
                        "fiftytwo_wk_high": _float(overview.get("52WeekHigh")),
                    }
                )
            except Exception:
                logger.warning(
                    "AlphaVantage: failed to fetch %s", sym, exc_info=True
                )
                rows.append(
                    {
                        "symbol": sym,
                        "last_price": None,
                        "prev_close": None,
                        "currency": "USD",
                        "fiftytwo_wk_low": None,
                        "fiftytwo_wk_high": None,
                    }
                )
        return pd.DataFrame(rows).set_index("symbol")

    def get_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        if period in ("5d", "1mo"):
            func = "TIME_SERIES_DAILY"
            outputsize = "compact"
        else:
            func = "TIME_SERIES_DAILY"
            outputsize = "full"
        data = self._get(
            {"function": func, "symbol": symbol, "outputsize": outputsize}
        )
        ts = data.get("Time Series (Daily)", {})
        if not ts:
            logger.warning("AlphaVantage: empty history for %s", symbol)
            return pd.DataFrame()
        records = []
        for date_str, vals in ts.items():
            records.append(
                {
                    "Date": pd.Timestamp(date_str),
                    "Open": float(vals["1. open"]),
                    "High": float(vals["2. high"]),
                    "Low": float(vals["3. low"]),
                    "Close": float(vals["4. close"]),
                    "Volume": int(vals["5. volume"]),
                }
            )
        df = pd.DataFrame(records).set_index("Date").sort_index()
        return df


def _float(v) -> float | None:
    """Safe float conversion."""
    if v is None:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

