from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from core.config import AppConfig


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(config: AppConfig) -> logging.Logger:
    logger = logging.getLogger("binance_ai_trader")
    logger.setLevel(config.log_level.upper())

    if logger.handlers:
        return logger

    text_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    json_formatter = _JsonFormatter()

    console = logging.StreamHandler()
    if config.console_log_format.lower() == "json":
        console.setFormatter(json_formatter)
    else:
        console.setFormatter(text_formatter)
    logger.addHandler(console)

    log_dir: Path = config.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / config.log_file

    file_handler = RotatingFileHandler(
        filename=str(file_path),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(text_formatter)
    logger.addHandler(file_handler)

    if config.enable_json_file_log:
        json_file_path = log_dir / config.json_log_file
        json_file_handler = RotatingFileHandler(
            filename=str(json_file_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        json_file_handler.setFormatter(json_formatter)
        logger.addHandler(json_file_handler)

    logger.propagate = False
    return logger
