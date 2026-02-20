"""Load and validate config.yml."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "/app/config.yml"


def _resolve_env_vars(value: Any) -> Any:
    """Recursively resolve ${ENV_VAR} placeholders in strings."""
    if isinstance(value, str) and "${" in value:
        import re

        def _replace(m: re.Match) -> str:
            return os.environ.get(m.group(1), "")

        return re.sub(r"\$\{([^}]+)}", _replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(i) for i in value]
    return value


def load_config(path: str | None = None) -> dict:
    """Load config from YAML file, falling back to sensible defaults."""
    config_path = path or os.environ.get("CONFIG_PATH", DEFAULT_CONFIG_PATH)
    p = Path(config_path)
    if not p.exists():
        # Try relative to this file's parent (repo root)
        alt = Path(__file__).resolve().parent.parent / "config.yml"
        if alt.exists():
            p = alt
        else:
            logger.error("Config file not found: %s", config_path)
            sys.exit(1)

    with open(p, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    cfg = _resolve_env_vars(cfg)

    # ---- Defaults ----
    cfg.setdefault("portfolio", {})
    cfg["portfolio"].setdefault("base_currency", "EUR")
    cfg["portfolio"].setdefault("positions", [])

    cfg.setdefault("report", {})
    cfg["report"].setdefault(
        "fields",
        [
            "last_price",
            "day_change_pct",
            "pnl_abs",
            "pnl_pct",
            "week_to_date_pct",
            "month_to_date_pct",
            "fiftytwo_wk_range",
        ],
    )
    cfg["report"].setdefault("sort_by", "day_change_pct")
    cfg["report"].setdefault("top_n", 10)
    cfg["report"].setdefault("include_index", [])

    cfg.setdefault("telegram", {})
    cfg["telegram"].setdefault("bot_token", "")
    cfg["telegram"].setdefault("chat_ids", [])
    cfg["telegram"].setdefault("header", "Daily Stock Report")
    cfg["telegram"].setdefault("footer", "— sent by stock-bot")

    cfg.setdefault("schedule", {})
    cfg["schedule"].setdefault("times", ["08:10"])
    cfg["schedule"].setdefault("timezone", "Europe/Amsterdam")

    return cfg

