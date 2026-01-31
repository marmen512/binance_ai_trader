from __future__ import annotations


class RiskScaler:
    """
    Converts drawdown → risk multiplier.

    Designed for smooth degradation instead of hard stops.
    """

    def __init__(
        self,
        dd_1: float = 5.0,
        dd_2: float = 10.0,
        dd_3: float = 15.0,
        dd_stop: float = 20.0,
    ):
        self.dd_1 = dd_1
        self.dd_2 = dd_2
        self.dd_3 = dd_3
        self.dd_stop = dd_stop

    def multiplier(self, drawdown_pct: float) -> float:
        if drawdown_pct >= self.dd_stop:
            return 0.0
        elif drawdown_pct >= self.dd_3:
            return 0.2
        elif drawdown_pct >= self.dd_2:
            return 0.4
        elif drawdown_pct >= self.dd_1:
            return 0.7
        else:
            return 1.0

    def scale_risk(self, base_risk: float, drawdown_pct: float) -> float:
        return base_risk * self.multiplier(drawdown_pct)
