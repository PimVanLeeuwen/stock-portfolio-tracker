"""Send a report via Telegram Bot API."""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

TIMEOUT = 30
MAX_RETRIES = 3
# Telegram message limit is 4096 chars; we chunk if needed.
TG_MAX_LEN = 4096


def send_report(message: str, bot_token: str, chat_ids: list[str]) -> bool:
    """Send *message* to one or more Telegram chats.

    Uses the Bot API: POST https://api.telegram.org/bot<token>/sendMessage
    Returns True if at least one chat succeeded.
    """
    if not bot_token:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set and not in config – cannot send")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    any_ok = False

    for chat_id in chat_ids:
        # Chunk the message if it exceeds Telegram's limit
        chunks = _chunk_message(message, TG_MAX_LEN)
        for chunk in chunks:
            ok = _post_message(url, chat_id, chunk)
            if ok:
                any_ok = True

    return any_ok


def _post_message(url: str, chat_id: str, text: str) -> bool:
    """POST a single message to Telegram with retries."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
            data = resp.json()
            if data.get("ok"):
                logger.info(
                    "Telegram message sent to %s (attempt %d)", chat_id, attempt
                )
                return True
            logger.warning(
                "Telegram API error for chat %s: %s (attempt %d/%d)",
                chat_id,
                data.get("description", resp.text[:200]),
                attempt,
                MAX_RETRIES,
            )
        except requests.RequestException as exc:
            logger.warning(
                "Telegram send failed for chat %s (attempt %d/%d): %s",
                chat_id,
                attempt,
                MAX_RETRIES,
                exc,
            )
    logger.error("Telegram send to %s failed after %d attempts", chat_id, MAX_RETRIES)
    return False


def _chunk_message(text: str, max_len: int) -> list[str]:
    """Split text into chunks of at most *max_len* characters, on newlines."""
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Find last newline within limit
        cut = text.rfind("\n", 0, max_len)
        if cut <= 0:
            cut = max_len
        chunks.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return chunks

