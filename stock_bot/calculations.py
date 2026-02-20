"""Portfolio metric calculations – pure functions, easy to test."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Single-position helpers
# ---------------------------------------------------------------------------

def day_change_pct(last_price: float, prev_close: float) -> Optional[float]:
    """Percentage change from previous close to last price."""
    if prev_close is None or prev_close == 0 or last_price is None:
        return None
    return ((last_price - prev_close) / prev_close) * 100.0


def pnl_absolute(
    last_price: float, cost_basis: Optional[float], units: float
) -> Optional[float]:
    """Absolute profit/loss in base currency."""
    if cost_basis is None or last_price is None:
        return None
    return (last_price - cost_basis) * units


def pnl_percent(
    last_price: float, cost_basis: Optional[float]
) -> Optional[float]:
    """P/L as percentage of cost basis."""
    if cost_basis is None or cost_basis == 0 or last_price is None:
        return None
    return ((last_price - cost_basis) / cost_basis) * 100.0


def period_change_pct(
    history: pd.DataFrame,
    reference_date: datetime,
) -> Optional[float]:
    """Compute % change from *reference_date*'s close to the latest close.

    *history* must have a DatetimeIndex and a 'Close' column.
    """
    if history.empty or "Close" not in history.columns:
        return None

    # Normalise index to tz-naive for comparison
    idx = history.index.tz_localize(None) if history.index.tz else history.index

    ref = pd.Timestamp(reference_date)
    if ref.tzinfo is not None:
        ref = ref.tz_localize(None)
    ref = ref.normalize()

    # Pick the last close on or before the reference date (positional lookup)
    mask = idx <= ref
    if not mask.any():
        # Fall back: use the earliest available close
        ref_close = float(history.iloc[0]["Close"])
    else:
        # Get the positional index of the last True in mask
        pos = mask.nonzero()[0][-1]
        ref_close = float(history.iloc[pos]["Close"])

    if ref_close == 0:
        return None

    latest_close = float(history.iloc[-1]["Close"])
    return ((latest_close - ref_close) / ref_close) * 100.0


def week_to_date_pct(history: pd.DataFrame, today: datetime | None = None) -> Optional[float]:
    """% change from last Monday's close (or Friday close if Monday unavailable)."""
    if today is None:
        today = datetime.now(timezone.utc)
    # Monday of the current week
    monday = today - timedelta(days=today.weekday())
    # We want the close *before* the week started → Friday = monday - 3 days
    ref = monday - timedelta(days=3)
    return period_change_pct(history, ref)


def month_to_date_pct(history: pd.DataFrame, today: datetime | None = None) -> Optional[float]:
    """% change from the last trading day of the previous month."""
    if today is None:
        today = datetime.now(timezone.utc)
    first_of_month = today.replace(day=1)
    ref = first_of_month - timedelta(days=1)  # last day prev month
    return period_change_pct(history, ref)


def fiftytwo_wk_range_str(low: Optional[float], high: Optional[float]) -> str:
    """Format 52-week range as a string."""
    if low is None or high is None:
        return "N/A"
    return f"{low:,.2f} – {high:,.2f}"


# ---------------------------------------------------------------------------
# Build metrics row for one position
# ---------------------------------------------------------------------------

def compute_position_metrics(
    symbol: str,
    snapshot_row: pd.Series,
    history_1mo: pd.DataFrame,
    units: float,
    cost_basis: Optional[float],
    fx_rate: float = 1.0,
    today: datetime | None = None,
) -> dict:
    """Return a dict of computed metrics for a single position.

    *snapshot_row* comes from the provider snapshot (already converted to base
    currency) and must have: last_price, prev_close, fiftytwo_wk_low,
    fiftytwo_wk_high.

    *cost_basis* may be None (in which case P/L fields are omitted).
    *fx_rate* is the rate that was applied to convert cost_basis into base
    currency (instrument ccy → base ccy).
    """
    lp = snapshot_row.get("last_price")
    pc = snapshot_row.get("prev_close")

    # Convert cost_basis to base currency if provided
    cb_base = cost_basis * fx_rate if cost_basis is not None else None

    return {
        "symbol": symbol,
        "units": units,
        "last_price": lp,
        "day_change_pct": day_change_pct(lp, pc),
        "pnl_abs": pnl_absolute(lp, cb_base, units),
        "pnl_pct": pnl_percent(lp, cb_base),
        "week_to_date_pct": week_to_date_pct(history_1mo, today),
        "month_to_date_pct": month_to_date_pct(history_1mo, today),
        "fiftytwo_wk_range": fiftytwo_wk_range_str(
            snapshot_row.get("fiftytwo_wk_low"),
            snapshot_row.get("fiftytwo_wk_high"),
        ),
    }

