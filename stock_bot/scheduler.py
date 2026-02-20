"""Scheduler – run once or on a daily schedule."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import pytz
import schedule

logger = logging.getLogger(__name__)


def run_scheduled(job_fn, cfg: dict) -> None:
    """Entry-point: run *job_fn* once or on a recurring schedule.

    If env ``RUN_ONCE=true``, execute once and return.
    Otherwise, schedule at the times given in ``cfg['schedule']``.
    """
    run_once = os.environ.get("RUN_ONCE", "").lower() in ("1", "true", "yes")
    if run_once:
        logger.info("RUN_ONCE=true → executing single run")
        job_fn()
        return

    tz_name = cfg["schedule"].get("timezone", "UTC")
    tz = pytz.timezone(tz_name)
    times: list[str] = cfg["schedule"].get("times", ["08:00"])

    for t in times:
        schedule.every().day.at(t, tz_name).do(job_fn)
        logger.info("Scheduled job at %s (%s)", t, tz_name)

    # Log next run
    _log_next_run(tz)

    while True:
        schedule.run_pending()
        time.sleep(30)


def _log_next_run(tz) -> None:
    """Log when the next scheduled job will fire."""
    nxt = schedule.next_run()
    if nxt:
        now = datetime.now(tz)
        logger.info("Next run: %s (now: %s)", nxt, now.strftime("%H:%M %Z"))
