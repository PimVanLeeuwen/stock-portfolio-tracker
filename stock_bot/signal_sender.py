"""Send a report via Signal REST API (signal-cli-rest-api)."""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

TIMEOUT = 30
MAX_RETRIES = 3


def send_report(message: str, sender: str, recipients: list[str]) -> bool:
    """POST *message* to Signal REST API.

    Returns True on success, False otherwise.
    """
    base_url = os.environ.get("SIGNAL_API_BASE", "http://signal:8080").rstrip("/")
    url = f"{base_url}/v2/send"

    payload = {
        "message": message,
        "number": sender,
        "recipients": recipients,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
            if resp.status_code < 300:
                logger.info("Signal message sent successfully (attempt %d)", attempt)
                return True
            logger.warning(
                "Signal API returned %d: %s (attempt %d/%d)",
                resp.status_code,
                resp.text[:200],
                attempt,
                MAX_RETRIES,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Signal send failed (attempt %d/%d): %s",
                attempt,
                MAX_RETRIES,
                exc,
            )

    logger.error("Signal send failed after %d attempts", MAX_RETRIES)
    return False

