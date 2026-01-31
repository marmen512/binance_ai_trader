from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, UTC
from typing import List


@dataclass
class EquityPoint:
    ts: str
    equity: float
    peak_equity: float
    drawdown_pct: float


class EquityTracker:
    """
    Tracks equity curve + rolling max + drawdown.
    """

    def __init__(self, starting_equity: float):
        self.starting_equity = starting_equity
        self.current_equity = starting_equity
        self.peak_equity = starting_equity
        self.history: List[EquityPoint] = []

    def update(self, pnl_delta: float) -> EquityPoint:
        self.current_equity += pnl_delta

        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        drawdown = 0.0
        if self.peak_equity > 0:
            drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100.0

        point = EquityPoint(
            ts=datetime.now(UTC).isoformat(),
            equity=self.current_equity,
            peak_equity=self.peak_equity,
            drawdown_pct=drawdown,
        )

        self.history.append(point)
        return point

    def get_drawdown_pct(self) -> float:
        if self.peak_equity == 0:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity * 100.0

    def snapshot(self) -> dict:
        return {
            "equity": self.current_equity,
            "peak_equity": self.peak_equity,
            "drawdown_pct": self.get_drawdown_pct(),
        }
