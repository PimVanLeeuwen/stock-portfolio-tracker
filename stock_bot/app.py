#!/usr/bin/env python3
"""stock-bot – daily portfolio report via Signal."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

import pandas as pd

from stock_bot.config import load_config
from stock_bot.providers.provider_manager import ProviderManager
from stock_bot.currency import convert_to_base
from stock_bot.calculations import compute_position_metrics
from stock_bot.report import format_report
from stock_bot.signal_sender import send_report
from stock_bot.scheduler import run_scheduled

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("stock-bot")


# ---------------------------------------------------------------------------
# Core job
# ---------------------------------------------------------------------------

def _run_job() -> None:
    """Fetch data, compute metrics, format and send the report."""
    cfg = load_config()
    base_ccy = cfg["portfolio"].get("base_currency", "EUR")
    positions = cfg["portfolio"].get("positions", [])

    if not positions:
        logger.error("No positions configured – nothing to do")
        _exit_if_run_once(1)
        return

    manager = ProviderManager()

    # ---- Snapshot ----
    symbols = [p["symbol"] for p in positions]
    logger.info("Fetching snapshot for %d symbols …", len(symbols))
    snapshot = manager.get_snapshot(symbols)

    if snapshot.empty:
        logger.error("Snapshot is empty – aborting")
        _exit_if_run_once(1)
        return

    # ---- FX conversion ----
    snapshot = convert_to_base(snapshot, base_ccy)

    # ---- Position metrics ----
    now = datetime.now(timezone.utc)
    metrics: list[dict] = []
    for pos in positions:
        sym = pos["symbol"]
        if sym not in snapshot.index:
            logger.warning("Symbol %s not in snapshot – skipping", sym)
            continue

        row = snapshot.loc[sym]
        # Fetch 1-month history for WTD/MTD
        hist = manager.get_history(sym, period="1mo")

        # If history is in a different currency, we need FX conversion of history
        # Apply FX to Close column if needed
        if not hist.empty and "Close" in hist.columns:
            # The snapshot fx_rate already tells us the conversion factor
            fx = float(row.get("fx_rate", 1.0))
            if fx != 1.0:
                hist = hist.copy()
                hist.loc[:, "Close"] = hist["Close"] * fx

        cost_basis = pos.get("cost_basis")  # may be None
        units = pos.get("units", 0)
        fx_rate = row.get("fx_rate", 1.0)

        m = compute_position_metrics(
            symbol=sym,
            snapshot_row=row,
            history_1mo=hist,
            units=units,
            cost_basis=cost_basis,
            fx_rate=fx_rate,
            today=now,
        )
        metrics.append(m)

    # ---- Index summary ----
    index_symbols = cfg["report"].get("include_index", [])
    index_metrics: list[dict] = []
    if index_symbols:
        logger.info("Fetching index snapshot for %s", index_symbols)
        idx_snap = manager.get_snapshot(index_symbols)
        # indices don't usually need FX conversion, but do it anyway
        idx_snap = convert_to_base(idx_snap, base_ccy)
        for sym in index_symbols:
            if sym in idx_snap.index:
                r = idx_snap.loc[sym]
                index_metrics.append(
                    {
                        "symbol": sym,
                        "last_price": r.get("last_price"),
                        "day_change_pct": (
                            ((r["last_price"] - r["prev_close"]) / r["prev_close"] * 100)
                            if pd.notna(r.get("last_price")) and pd.notna(r.get("prev_close")) and r["prev_close"] != 0
                            else None
                        ),
                    }
                )

    # ---- Report ----
    report_text = format_report(metrics, index_metrics, cfg, now=now)
    logger.info("Report generated (%d bytes)", len(report_text.encode()))
    logger.debug("Report:\n%s", report_text)

    # ---- Send ----
    sender = cfg["signal"].get("sender", "")
    recipients = cfg["signal"].get("recipients", [])
    if not sender or not recipients:
        logger.warning("Signal sender/recipients not configured – printing report to stdout")
        print(report_text)
    else:
        ok = send_report(report_text, sender, recipients)
        if not ok:
            logger.error("Failed to send report via Signal")
            _exit_if_run_once(1)
            return

    logger.info("Job completed successfully")


def _exit_if_run_once(code: int) -> None:
    """Exit with *code* if RUN_ONCE is set."""
    if os.environ.get("RUN_ONCE", "").lower() in ("1", "true", "yes"):
        sys.exit(code)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("stock-bot starting")
    cfg = load_config()
    try:
        run_scheduled(_run_job, cfg)
    except KeyboardInterrupt:
        logger.info("Interrupted – shutting down")
    except Exception:
        logger.critical("Fatal error", exc_info=True)
        _exit_if_run_once(1)


if __name__ == "__main__":
    main()

