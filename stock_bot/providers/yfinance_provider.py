"""yfinance provider – always available (no API key required)."""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from stock_bot.providers.base import StockProvider

logger = logging.getLogger(__name__)


class YFinanceProvider(StockProvider):
    """Uses the yfinance library to pull quotes and history."""

    def get_snapshot(self, symbols: list[str]) -> pd.DataFrame:
        rows: list[dict] = []
        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info or {}
                rows.append(
                    {
                        "symbol": sym,
                        "last_price": info.get("currentPrice")
                        or info.get("regularMarketPrice")
                        or info.get("previousClose"),
                        "prev_close": info.get("regularMarketPreviousClose")
                        or info.get("previousClose"),
                        "currency": (info.get("currency") or "USD").upper(),
                        "fiftytwo_wk_low": info.get("fiftyTwoWeekLow"),
                        "fiftytwo_wk_high": info.get("fiftyTwoWeekHigh"),
                    }
                )
            except Exception:
                logger.warning("yfinance: failed to fetch %s", sym, exc_info=True)
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
        df = pd.DataFrame(rows).set_index("symbol")
        return df

    def get_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning("yfinance: empty history for %s period=%s", symbol, period)
        return hist

