"""Provider manager – cascade through providers by priority."""

from __future__ import annotations

import logging

import pandas as pd

from stock_bot.providers.base import StockProvider
from stock_bot.providers.finnhub_provider import FinnhubProvider
from stock_bot.providers.alphavantage_provider import AlphaVantageProvider
from stock_bot.providers.yfinance_provider import YFinanceProvider

logger = logging.getLogger(__name__)


def _build_provider_chain() -> list[StockProvider]:
    """Instantiate providers in priority order: Finnhub -> Alpha Vantage -> yfinance."""
    chain: list[StockProvider] = []
    for cls in (FinnhubProvider, AlphaVantageProvider):
        try:
            chain.append(cls())
            logger.info("Provider available: %s", cls.__name__)
        except ValueError as exc:
            logger.info("Provider skipped (%s): %s", cls.__name__, exc)
    # yfinance is always available as the final fallback
    chain.append(YFinanceProvider())
    logger.info("Provider available: YFinanceProvider (fallback)")
    return chain


class ProviderManager:
    """Try each provider in turn; first success wins."""

    def __init__(self) -> None:
        self.chain = _build_provider_chain()

    def get_snapshot(self, symbols: list[str]) -> pd.DataFrame:
        for provider in self.chain:
            try:
                df = provider.get_snapshot(symbols)
                # Validate we got at least some prices
                if df["last_price"].notna().any():
                    logger.info(
                        "Snapshot served by %s", type(provider).__name__
                    )
                    return df
                logger.warning(
                    "%s returned all-NaN snapshot, trying next",
                    type(provider).__name__,
                )
            except Exception:
                logger.warning(
                    "%s snapshot failed, trying next",
                    type(provider).__name__,
                    exc_info=True,
                )
        # Return empty frame as last resort
        logger.error("All providers failed for snapshot")
        return pd.DataFrame(
            columns=[
                "last_price",
                "prev_close",
                "currency",
                "fiftytwo_wk_low",
                "fiftytwo_wk_high",
            ]
        )

    def get_history(self, symbol: str, period: str = "1mo") -> pd.DataFrame:
        for provider in self.chain:
            try:
                df = provider.get_history(symbol, period)
                if not df.empty:
                    return df
            except Exception:
                logger.warning(
                    "%s history(%s) failed, trying next",
                    type(provider).__name__,
                    symbol,
                    exc_info=True,
                )
        logger.error("All providers failed for history(%s)", symbol)
        return pd.DataFrame()

