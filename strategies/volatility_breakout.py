from __future__ import annotations

import pandas as pd

from strategies.base_strategy import StrategyResult


class VolatilityBreakoutStrategy:
    name = "volatility_breakout"

    def __init__(self, *, width_min: float = 0.002) -> None:
        self.width_min = width_min

    def generate(self, df: pd.DataFrame) -> StrategyResult:
        out = df
        if "close" not in out.columns:
            pos = pd.Series(0, index=out.index, dtype="int")
            return StrategyResult(name=self.name, position=pos)

        close = pd.to_numeric(out["close"], errors="coerce")
        width = pd.to_numeric(out.get("bb_width_20"), errors="coerce") if "bb_width_20" in out.columns else None

        mid = close.rolling(window=20, min_periods=20).mean()
        std = close.rolling(window=20, min_periods=20).std()
        upper = mid + 2 * std
        lower = mid - 2 * std

        breakout_long = close > upper
        breakout_short = close < lower

        if width is not None:
            breakout_long = breakout_long & (width >= self.width_min)
            breakout_short = breakout_short & (width >= self.width_min)

        pos = pd.Series(0, index=out.index, dtype="int")
        pos = pos.mask(breakout_long, 1)
        pos = pos.mask(breakout_short, -1)

        return StrategyResult(name=self.name, position=pos)
