"""
Central logging utilities.

ARCHITECTURAL RULES:
- Read-only
- No training logic
- No model updates
- Safe to use in replay, paper monitoring, offline preprocessing
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    stream: Optional[object] = None,
) -> logging.Logger:
    """
    Create a simple, consistent logger.

    This logger is intentionally minimal and side-effect free.
    """

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # already configured

    logger.setLevel(level)

    handler = logging.StreamHandler(stream or sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False

    return logger
