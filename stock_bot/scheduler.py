"""Scheduler – run once or on a cron schedule."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import pytz
from croniter import croniter

logger = logging.getLogger(__name__)


def run_scheduled(job_fn, cfg: dict) -> None:
    """Entry-point: run *job_fn* once or on a cron schedule.

    If env ``RUN_ONCE=true``, execute once and return.
    Otherwise, use CRON_SCHEDULE env var (default: ``10 8,17 * * 1-5``
    = 08:10 and 17:10 on weekdays) in the configured timezone.
    """
    run_once = os.environ.get("RUN_ONCE", "").lower() in ("1", "true", "yes")
    if run_once:
        logger.info("RUN_ONCE=true → executing single run")
        job_fn()
        return

    tz_name = os.environ.get("TZ", cfg.get("schedule", {}).get("timezone", "Europe/Amsterdam"))
    tz = pytz.timezone(tz_name)

    # Cron expression from env, fallback to config times, fallback to default
    cron_expr = os.environ.get("CRON_SCHEDULE", "")
    if not cron_expr:
        # Build cron from legacy config.yml times (e.g. ["08:10", "17:10"])
        times = cfg.get("schedule", {}).get("times", ["08:10"])
        cron_expr = _times_to_cron(times)

    logger.info("Cron schedule: '%s' (%s)", cron_expr, tz_name)

    while True:
        now = datetime.now(tz)
        cron = croniter(cron_expr, now)
        next_run = cron.get_next(datetime)
        wait_seconds = (next_run - now).total_seconds()

        logger.info(
            "Next run: %s (in %.0f min)",
            next_run.strftime("%H:%M %Z"),
            wait_seconds / 60,
        )

        time.sleep(max(wait_seconds, 1))
        logger.info("Running scheduled job")

        try:
            job_fn()
        except Exception:
            logger.error("Scheduled job failed", exc_info=True)


def _times_to_cron(times: list[str]) -> str:
    """Convert a list of HH:MM times to a cron expression.

    e.g. ["08:10", "17:10"] → "10 8,17 * * *"
    """
    minutes = set()
    hours = set()
    for t in times:
        parts = t.strip().split(":")
        hours.add(int(parts[0]))
        minutes.add(int(parts[1]))

    # If all times share the same minute, use a single minute value
    min_str = ",".join(str(m) for m in sorted(minutes))
    hr_str = ",".join(str(h) for h in sorted(hours))
    return f"{min_str} {hr_str} * * *"
