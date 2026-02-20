"""Plain-text report formatter for Signal delivery."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

MAX_REPORT_BYTES = 5500  # stay well under Signal's ~6 KB limit


def _fmt(val, fmt: str = ".2f", suffix: str = "") -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    return f"{val:{fmt}}{suffix}"


def _sign(val) -> str:
    """Return value with explicit +/- sign."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "  —"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


def format_report(
    metrics: list[dict],
    index_metrics: list[dict],
    cfg: dict,
    now: Optional[datetime] = None,
) -> str:
    """Build the complete plain-text report string."""
    if now is None:
        now = datetime.now(timezone.utc)

    header = cfg.get("telegram", cfg.get("signal", {})).get("header", "Daily Stock Report")
    footer = cfg.get("telegram", cfg.get("signal", {})).get("footer", "")
    sort_by = cfg["report"].get("sort_by", "day_change_pct")
    top_n = cfg["report"].get("top_n", 10)
    base_ccy = cfg["portfolio"].get("base_currency", "EUR")

    lines: list[str] = []

    # --- Header ---
    lines.append(header)
    lines.append(f"Date: {now.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append(f"Currency: {base_ccy}")
    lines.append("=" * 48)

    # --- Sort positions ---
    df = pd.DataFrame(metrics)
    if df.empty:
        lines.append("No position data available.")
        lines.append(footer)
        return "\n".join(lines)

    if sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False, na_position="last")
    df = df.head(top_n)

    # --- Table header ---
    lines.append(
        f"{'Sym':<8} {'Price':>9} {'Day%':>7} {'P/L':>10} {'P/L%':>7} "
        f"{'WTD%':>7} {'MTD%':>7} {'52wk Range':>20}"
    )
    lines.append("-" * 80)

    for _, row in df.iterrows():
        sym = str(row.get("symbol", ""))[:7]
        price = _fmt(row.get("last_price"), ".2f")
        day = _sign(row.get("day_change_pct"))
        pnl = _fmt(row.get("pnl_abs"), ",.2f") if row.get("pnl_abs") is not None else "  —"
        pnl_p = _sign(row.get("pnl_pct"))
        wtd = _sign(row.get("week_to_date_pct"))
        mtd = _sign(row.get("month_to_date_pct"))
        rng = str(row.get("fiftytwo_wk_range", "N/A"))

        lines.append(
            f"{sym:<8} {price:>9} {day:>7} {pnl:>10} {pnl_p:>7} "
            f"{wtd:>7} {mtd:>7} {rng:>20}"
        )

    # --- Index summary ---
    if index_metrics:
        lines.append("")
        lines.append("Indices:")
        lines.append("-" * 48)
        for idx in index_metrics:
            sym = str(idx.get("symbol", ""))
            price = _fmt(idx.get("last_price"), ",.2f")
            day = _sign(idx.get("day_change_pct"))
            lines.append(f"  {sym:<10} {price:>12}  {day:>7}")

    # --- Footer ---
    lines.append("")
    lines.append(footer)

    report = "\n".join(lines)

    # Truncate if too long
    encoded = report.encode("utf-8")
    if len(encoded) > MAX_REPORT_BYTES:
        logger.warning(
            "Report too large (%d bytes), truncating to %d",
            len(encoded),
            MAX_REPORT_BYTES,
        )
        report = encoded[:MAX_REPORT_BYTES].decode("utf-8", errors="ignore")
        report += "\n... (truncated)"

    return report

