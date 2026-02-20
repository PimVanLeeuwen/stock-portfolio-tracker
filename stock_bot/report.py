"""Telegram-friendly report formatter with HTML markup."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

TG_MAX_CHARS = 4096


def _arrow(val) -> str:
    """Return a colored arrow emoji based on sign."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "➖"
    return "🟢" if val >= 0 else "🔴"


def _sign(val) -> str:
    """Format a percentage with +/- sign."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def _money(val) -> str:
    """Format a monetary value."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:,.2f}"


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
    lines.append(f"💰 All values in <b>{base_ccy}</b>")
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
    for _, row in df.iterrows():
        sym = str(row.get("symbol", ""))
        day_pct = row.get("day_change_pct")
        arrow = _arrow(day_pct)

        lines.append(f"{arrow} <b>{sym}</b>  {_price(row.get('last_price'))} {base_ccy}")

        details: list[str] = []
        details.append(f"Day: {_sign(day_pct)}")

        if row.get("pnl_abs") is not None:
            details.append(f"P/L: {_money(row.get('pnl_abs'))} ({_sign(row.get('pnl_pct'))})")

        wtd = row.get("week_to_date_pct")
        mtd = row.get("month_to_date_pct")
        if wtd is not None or mtd is not None:
            parts = []
            if wtd is not None:
                parts.append(f"WTD {_sign(wtd)}")
            if mtd is not None:
                parts.append(f"MTD {_sign(mtd)}")
            details.append(" · ".join(parts))

        rng = row.get("fiftytwo_wk_range", "N/A")
        if rng and rng != "N/A":
            details.append(f"52wk: {rng}")

        lines.append("    " + " | ".join(details[:2]))
        if len(details) > 2:
            lines.append("    " + " | ".join(details[2:]))
        lines.append("")

    # ── Index summary ──
    if index_metrics:
        lines.append("─── <b>Indices</b> ───")
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

