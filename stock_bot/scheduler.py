"""Scheduler – run once or on a daily schedule."""
        logger.info("Next run: %s (now: %s)", nxt, now.strftime("%H:%M %Z"))
        now = datetime.now(tz)
    if nxt:
    nxt = schedule.next_run()
    """Log when the next scheduled job will fire."""
def _log_next_run(tz) -> None:


        time.sleep(30)
        schedule.run_pending()
    while True:

    _log_next_run(tz)
    # Log next run

        logger.info("Scheduled job at %s (%s)", t, tz_name)
        schedule.every().day.at(t, tz_name).do(job_fn)
    for t in times:

    times: list[str] = cfg["schedule"].get("times", ["08:00"])
    tz = pytz.timezone(tz_name)
    tz_name = cfg["schedule"].get("timezone", "UTC")

        return
        job_fn()
        logger.info("RUN_ONCE=true → executing single run")
    if run_once:
    run_once = os.environ.get("RUN_ONCE", "").lower() in ("1", "true", "yes")
    """
    Otherwise, schedule at the times given in ``cfg['schedule']``.
    If env ``RUN_ONCE=true``, execute once and return.

    """Entry-point: run *job_fn* once or on a recurring schedule.
def run_scheduled(job_fn, cfg: dict) -> None:


logger = logging.getLogger(__name__)

import schedule
import pytz

from datetime import datetime
import time
import os
import logging

from __future__ import annotations


