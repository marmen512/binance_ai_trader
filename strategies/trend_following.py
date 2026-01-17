from __future__ import annotations

import pandas as pd

from strategies.base_strategy import StrategyResult


class TrendFollowingStrategy:
    name = "trend_following"

    def generate(self, df: pd.DataFrame) -> StrategyResult:
        out = df

        if "macd_hist" not in out.columns or "ema_26" not in out.columns or "close" not in out.columns:
            pos = pd.Series(0, index=out.index, dtype="int")
            return StrategyResult(name=self.name, position=pos)

        macd_hist = pd.to_numeric(out["macd_hist"], errors="coerce")
        ema_26 = pd.to_numeric(out["ema_26"], errors="coerce")
        close = pd.to_numeric(out["close"], errors="coerce")

        long = (macd_hist > 0) & (close >= ema_26)
        short = (macd_hist < 0) & (close <= ema_26)

        pos = pd.Series(0, index=out.index, dtype="int")
        pos = pos.mask(long, 1)
        pos = pos.mask(short, -1)

        return StrategyResult(name=self.name, position=pos)
