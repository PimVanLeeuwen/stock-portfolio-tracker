"""Unit tests for app.calculations module."""

from datetime import datetime

import pandas as pd
import pytest

from stock_bot.calculations import (
    compute_position_metrics,
    day_change_pct,
    fiftytwo_wk_range_str,
    month_to_date_pct,
    period_change_pct,
    pnl_absolute,
    pnl_percent,
    week_to_date_pct,
)


# ---------------------------------------------------------------------------
# day_change_pct
# ---------------------------------------------------------------------------

class TestDayChangePct:
    def test_positive(self):
        assert day_change_pct(110.0, 100.0) == pytest.approx(10.0)

    def test_negative(self):
        assert day_change_pct(90.0, 100.0) == pytest.approx(-10.0)

    def test_zero_change(self):
        assert day_change_pct(100.0, 100.0) == pytest.approx(0.0)

    def test_none_last_price(self):
        assert day_change_pct(None, 100.0) is None

    def test_none_prev_close(self):
        assert day_change_pct(100.0, None) is None

    def test_zero_prev_close(self):
        assert day_change_pct(100.0, 0) is None


# ---------------------------------------------------------------------------
# pnl_absolute
# ---------------------------------------------------------------------------

class TestPnlAbsolute:
    def test_profit(self):
        result = pnl_absolute(last_price=160.0, cost_basis=148.2, units=12)
        assert result == pytest.approx((160.0 - 148.2) * 12)

    def test_loss(self):
        result = pnl_absolute(last_price=130.0, cost_basis=148.2, units=12)
        assert result == pytest.approx((130.0 - 148.2) * 12)

    def test_no_cost_basis(self):
        assert pnl_absolute(160.0, None, 12) is None

    def test_none_price(self):
        assert pnl_absolute(None, 148.2, 12) is None

    def test_zero_units(self):
        result = pnl_absolute(160.0, 148.2, 0)
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# pnl_percent
# ---------------------------------------------------------------------------

class TestPnlPercent:
    def test_profit(self):
        result = pnl_percent(160.0, 148.2)
        expected = ((160.0 - 148.2) / 148.2) * 100
        assert result == pytest.approx(expected)

    def test_loss(self):
        result = pnl_percent(130.0, 148.2)
        expected = ((130.0 - 148.2) / 148.2) * 100
        assert result == pytest.approx(expected)

    def test_no_cost_basis(self):
        assert pnl_percent(160.0, None) is None

    def test_zero_cost_basis(self):
        assert pnl_percent(160.0, 0) is None


# ---------------------------------------------------------------------------
# period_change_pct
# ---------------------------------------------------------------------------

def _make_history(dates_prices: list[tuple[str, float]]) -> pd.DataFrame:
    """Helper to build a tiny Close-only history DataFrame."""
    dates = [pd.Timestamp(d) for d, _ in dates_prices]
    prices = [p for _, p in dates_prices]
    return pd.DataFrame({"Close": prices}, index=pd.DatetimeIndex(dates, name="Date"))


class TestPeriodChangePct:
    def test_basic(self):
        hist = _make_history([
            ("2026-02-10", 100.0),
            ("2026-02-11", 102.0),
            ("2026-02-12", 105.0),
        ])
        ref = datetime(2026, 2, 10)
        result = period_change_pct(hist, ref)
        assert result == pytest.approx(5.0)

    def test_ref_before_data(self):
        """If ref is earlier than all data, fallback to earliest row."""
        hist = _make_history([
            ("2026-02-10", 100.0),
            ("2026-02-12", 110.0),
        ])
        ref = datetime(2026, 2, 5)
        result = period_change_pct(hist, ref)
        assert result == pytest.approx(10.0)

    def test_empty_history(self):
        assert period_change_pct(pd.DataFrame(), datetime(2026, 2, 10)) is None


# ---------------------------------------------------------------------------
# WTD / MTD
# ---------------------------------------------------------------------------

class TestWtdMtd:
    @pytest.fixture()
    def hist(self):
        return _make_history([
            ("2026-01-28", 100.0),
            ("2026-01-29", 101.0),
            ("2026-01-30", 102.0),
            ("2026-02-02", 103.0),
            ("2026-02-03", 104.0),
            ("2026-02-04", 106.0),
            ("2026-02-05", 105.0),
        ])

    def test_wtd(self, hist):
        today = datetime(2026, 2, 5)  # Thursday
        result = week_to_date_pct(hist, today)
        # Monday 2 Feb → ref = Fri 30 Jan (102), latest = 105
        expected = ((105 - 102) / 102) * 100
        assert result == pytest.approx(expected, rel=0.01)

    def test_mtd(self, hist):
        today = datetime(2026, 2, 5)
        result = month_to_date_pct(hist, today)
        # Ref: last day of Jan → 30 Jan (102), latest = 105
        expected = ((105 - 102) / 102) * 100
        assert result == pytest.approx(expected, rel=0.01)


# ---------------------------------------------------------------------------
# fiftytwo_wk_range_str
# ---------------------------------------------------------------------------

class TestFiftyTwoWkRange:
    def test_valid(self):
        assert fiftytwo_wk_range_str(120.50, 200.75) == "120.50 – 200.75"

    def test_none_low(self):
        assert fiftytwo_wk_range_str(None, 200.0) == "N/A"

    def test_none_high(self):
        assert fiftytwo_wk_range_str(120.0, None) == "N/A"


# ---------------------------------------------------------------------------
# compute_position_metrics (integration-style)
# ---------------------------------------------------------------------------

class TestComputePositionMetrics:
    def test_full_metrics(self):
        row = pd.Series({
            "last_price": 160.0,
            "prev_close": 155.0,
            "fiftytwo_wk_low": 120.0,
            "fiftytwo_wk_high": 180.0,
            "fx_rate": 1.0,
        })
        hist = _make_history([
            ("2026-01-28", 145.0),
            ("2026-01-30", 150.0),
            ("2026-02-03", 155.0),
            ("2026-02-05", 160.0),
        ])
        m = compute_position_metrics(
            symbol="AAPL",
            snapshot_row=row,
            history_1mo=hist,
            units=12,
            cost_basis=148.2,
            fx_rate=1.0,
            today=datetime(2026, 2, 5),
        )
        assert m["symbol"] == "AAPL"
        assert m["last_price"] == 160.0
        assert m["day_change_pct"] == pytest.approx(((160 - 155) / 155) * 100)
        assert m["pnl_abs"] == pytest.approx((160.0 - 148.2) * 12)
        assert m["pnl_pct"] == pytest.approx(((160 - 148.2) / 148.2) * 100)
        assert m["fiftytwo_wk_range"] == "120.00 – 180.00"

    def test_no_cost_basis(self):
        """P/L fields should be None when cost_basis is absent."""
        row = pd.Series({
            "last_price": 160.0,
            "prev_close": 155.0,
            "fiftytwo_wk_low": 120.0,
            "fiftytwo_wk_high": 180.0,
            "fx_rate": 1.0,
        })
        hist = _make_history([("2026-02-05", 160.0)])
        m = compute_position_metrics(
            symbol="ASML.AS",
            snapshot_row=row,
            history_1mo=hist,
            units=5,
            cost_basis=None,
            fx_rate=1.0,
            today=datetime(2026, 2, 5),
        )
        assert m["pnl_abs"] is None
        assert m["pnl_pct"] is None
        # Other fields should still be present
        assert m["day_change_pct"] is not None

    def test_fx_conversion(self):
        """cost_basis is multiplied by fx_rate."""
        row = pd.Series({
            "last_price": 160.0,  # already in EUR
            "prev_close": 155.0,
            "fiftytwo_wk_low": 120.0,
            "fiftytwo_wk_high": 180.0,
            "fx_rate": 0.92,
        })
        hist = _make_history([("2026-02-05", 160.0)])
        # cost_basis 148.2 USD × 0.92 = 136.344 EUR
        m = compute_position_metrics(
            symbol="AAPL",
            snapshot_row=row,
            history_1mo=hist,
            units=12,
            cost_basis=148.2,
            fx_rate=0.92,
            today=datetime(2026, 2, 5),
        )
        cb_eur = 148.2 * 0.92
        assert m["pnl_abs"] == pytest.approx((160.0 - cb_eur) * 12)
        assert m["pnl_pct"] == pytest.approx(((160.0 - cb_eur) / cb_eur) * 100)

