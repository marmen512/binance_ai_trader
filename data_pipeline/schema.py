from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OhlcvSchema:
    timestamp: str = "timestamp"
    open: str = "open"
    high: str = "high"
    low: str = "low"
    close: str = "close"
    volume: str = "volume"
