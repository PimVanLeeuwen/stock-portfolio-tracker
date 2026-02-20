"""Finnhub provider – requires FINNHUB_API_KEY env var."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import pandas as pd
import requests

from stock_bot.providers.base import StockProvider

logger = logging.getLogger(__name__)

BASE_URL = "https://finnhub.io/api/v1"
TIMEOUT = 15


class FinnhubProvider(StockProvider):
    """Uses Finnhub REST API for stock quotes and candle history."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("FINNHUB_API_KEY", "")
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY not set")

    # ---- helpers ----
    def _get(self, path: str, params: dict | None = None) -> dict:
        params = params or {}
        params["token"] = self.api_key
        resp = requests.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # ---- interface ----
    def get_snapshot(self, symbols: list[str]) -> pd.DataFrame:
        rows: list[dict] = []
        for sym in symbols:
            try:
                quote = self._get("/quote", {"symbol": sym})
                profile = self._get("/stock/profile2", {"symbol": sym})
                rows.append(
                    {
                        "symbol": sym,
                        "last_price": quote.get("c"),
                        "prev_close": quote.get("pc"),
                        "currency": (profile.get("currency") or "USD").upper(),
                        "fiftytwo_wk_low": quote.get("l"),   # day low as fallback
                        "fiftytwo_wk_high": quote.get("h"),  # day high as fallback
                    }
                )
            except Exception:
                logger.warning("Finnhub: failed to fetch %s", sym, exc_info=True)
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
        period_map = {"5d": 5, "1mo": 30, "3mo": 90, "1y": 365}
        days = period_map.get(period, 30)
        now = int(datetime.utcnow().timestamp())
        start = int((datetime.utcnow() - timedelta(days=days)).timestamp())
        data = self._get(
            "/stock/candle",
            {"symbol": symbol, "resolution": "D", "from": start, "to": now},
        )
        if data.get("s") != "ok":
            logger.warning("Finnhub: no candle data for %s", symbol)
            return pd.DataFrame()
        df = pd.DataFrame(
            {
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"],
                "Volume": data["v"],
            },
            index=pd.to_datetime(data["t"], unit="s", utc=True),
        )
        df.index.name = "Date"
        return df

