from __future__ import annotations
import pandas as pd
from strategies.base_strategy import StrategyResult


class MeanReversionStrategy:
    name = "mean_reversion"

    def __init__(self, *, rsi_low: float = 30.0, rsi_high: float = 70.0) -> None:
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high

    def generate(self, df: pd.DataFrame) -> StrategyResult:
        out = df
        if "rsi_14" not in out.columns:
            pos = pd.Series(0, index=out.index, dtype="int")
            return StrategyResult(name=self.name, position=pos)

        rsi = pd.to_numeric(out["rsi_14"], errors="coerce")
        long = rsi <= self.rsi_low
        short = rsi >= self.rsi_high

        pos = pd.Series(0, index=out.index, dtype="int")
        pos = pos.mask(long, 1)
        pos = pos.mask(short, -1)
        return StrategyResult(name=self.name, position=pos)
