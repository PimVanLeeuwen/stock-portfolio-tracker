"""Telegram-friendly report formatter with HTML markup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

TG_MAX_CHARS = 4096


def _arrow(val) -> str:
    """Return a colored emoji based on sign."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "➖"
    return "🟢" if val >= 0 else "🔴"


def _sign(val) -> str:
    """Format a percentage with +/- sign."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def _money(val, ccy: str = "") -> str:
    """Format a monetary value with optional currency."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    sign = "+" if val >= 0 else ""
    s = f"{sign}{val:,.2f}" if val < 0 or val >= 0 else f"{val:,.2f}"
    return f"{s} {ccy}".strip() if ccy else s


def _price(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{val:,.2f}"


def format_report(
    metrics: list[dict],
    index_metrics: list[dict],
    cfg: dict,
    now: Optional[datetime] = None,
) -> str:
    """Build a Telegram HTML report optimized for mobile readability."""
    if now is None:
        now = datetime.now(timezone.utc)

    header = cfg.get("telegram", {}).get("header", "📈 Daily Stock Report")
    footer = cfg.get("telegram", {}).get("footer", "")
    sort_by = cfg["report"].get("sort_by", "day_change_pct")
    top_n = cfg["report"].get("top_n", 10)
    base_ccy = cfg["portfolio"].get("base_currency", "EUR")

    lines: list[str] = []

    # ── Header ──
    lines.append(f"<b>{header}</b>")
    lines.append(f"📅 {now.strftime('%a %d %b %Y, %H:%M')} UTC")
    lines.append("")

    # ── Sort positions ──
    df = pd.DataFrame(metrics)
    if df.empty:
        lines.append("No position data available.")
        lines.append("")
        lines.append(f"<i>{footer}</i>")
        return "\n".join(lines)

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False, na_position="last")
    df = df.head(top_n)

    # ── Position cards ──
    total_value = 0.0
    total_day_change = 0.0
    has_portfolio_data = False

    for _, row in df.iterrows():
        sym = str(row.get("symbol", ""))
        day_pct = row.get("day_change_pct")
        price = row.get("last_price")
        units = row.get("units", 0)
        arrow = _arrow(day_pct)

        # Position value
        pos_value = None
        if price is not None and units and units > 0:
            pos_value = price * units
            total_value += pos_value
            has_portfolio_data = True
            if day_pct is not None and row.get("prev_close") is not None:
                prev_value = row.get("prev_close") * units
                total_day_change += pos_value - prev_value

        # Title line: emoji + symbol + price
        lines.append(f"{arrow} <b>{sym}</b> — {_price(price)} {base_ccy}")

        # Units & position value
        if units and units > 0:
            val_str = f"  📦 {units:.0f} shares"
            if pos_value is not None:
                val_str += f" → <b>{_price(pos_value)} {base_ccy}</b>"
            lines.append(val_str)

        # Each stat on its own line
        lines.append(f"  Day:  {_sign(day_pct)}")

        wtd = row.get("week_to_date_pct")
        if wtd is not None:
            lines.append(f"  WTD: {_sign(wtd)}")

        mtd = row.get("month_to_date_pct")
        if mtd is not None:
            lines.append(f"  MTD: {_sign(mtd)}")

        rng = row.get("fiftytwo_wk_range", "N/A")
        if rng and rng != "N/A":
            lines.append(f"  52wk: {rng}")

        lines.append("")  # blank line between stocks

    # ── Portfolio summary ──
    if has_portfolio_data:
        lines.append("━━━ <b>Portfolio</b> ━━━")
        lines.append(f"💼 Value: <b>{_price(total_value)} {base_ccy}</b>")
        day_arrow = _arrow(total_day_change)
        sign = "+" if total_day_change >= 0 else ""
        lines.append(f"{day_arrow} Day: {sign}{total_day_change:,.2f} {base_ccy}")
        lines.append("")

    # ── Index summary ──
    if index_metrics:
        lines.append("━━━ <b>Indices</b> ━━━")
        for idx in index_metrics:
            sym = str(idx.get("symbol", ""))
            arrow = _arrow(idx.get("day_change_pct"))
            lines.append(
                f"{arrow} <b>{sym}</b>  {_price(idx.get('last_price'))}  {_sign(idx.get('day_change_pct'))}"
            )
        lines.append("")

    # ── Footer ──
    lines.append(f"<i>{footer}</i>")

    report = "\n".join(lines)

    # Telegram limit safety
    if len(report) > TG_MAX_CHARS:
        logger.warning("Report too long (%d chars), truncating", len(report))
        report = report[: TG_MAX_CHARS - 20] + "\n<i>… truncated</i>"

    return report

