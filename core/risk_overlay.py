from dataclasses import dataclass
from typing import Dict


@dataclass
class MarketState:
    volatility: float      # 0..1
    drawdown: float        # 0..1
    regime: str            # "trend" | "chop" | "panic"


class RiskOverlay:
    """
    Adjusts allocations based on global market stress.
    """

    def __init__(self):
        pass

    def stress_factor(self, state: MarketState) -> float:
        factor = 1.0

        # volatility penalty
        if state.volatility > 0.8:
            factor *= 0.6
        elif state.volatility > 0.6:
            factor *= 0.8

        # drawdown penalty
        if state.drawdown > 0.3:
            factor *= 0.5
        elif state.drawdown > 0.15:
            factor *= 0.75

        # regime penalty
        if state.regime == "panic":
            factor *= 0.5
        elif state.regime == "chop":
            factor *= 0.8

        return max(factor, 0.1)

    def apply(
        self,
        allocations: Dict[str, float],
        state: MarketState
    ) -> Dict[str, float]:

        factor = self.stress_factor(state)

        return {
            k: round(v * factor, 2)
            for k, v in allocations.items()
        }
