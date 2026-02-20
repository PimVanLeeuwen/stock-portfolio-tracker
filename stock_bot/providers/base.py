"""Abstract base class for stock-data providers."""

from __future__ import annotations

import abc

import pandas as pd


class StockProvider(abc.ABC):
    """Return a DataFrame with at least these columns:

    symbol, last_price, prev_close, currency,
    fiftytwo_wk_low, fiftytwo_wk_high
    """

    @abc.abstractmethod
    def get_snapshot(self, symbols: list[str]) -> pd.DataFrame:
        """Fetch current quotes for *symbols*.

        Returns a DataFrame indexed by symbol.
        """

    @abc.abstractmethod
    def get_history(
        self, symbol: str, period: str = "1mo"
    ) -> pd.DataFrame:
        """Return OHLCV history for a single symbol.

        *period*: '5d', '1mo', '1y', etc.
        Returns a DataFrame with DatetimeIndex and at least a 'Close' column.
        """

