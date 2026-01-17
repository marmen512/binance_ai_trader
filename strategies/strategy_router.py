from __future__ import annotations

import pandas as pd

from strategies.base_strategy import StrategyResult
from strategies.mean_reversion import MeanReversionStrategy
from strategies.trend_following import TrendFollowingStrategy
from strategies.volatility_breakout import VolatilityBreakoutStrategy


class StrategyRouter:
    def __init__(self) -> None:
        self._trend = TrendFollowingStrategy()
        self._range = MeanReversionStrategy()
        self._high_vol = VolatilityBreakoutStrategy()

    def route(self, df: pd.DataFrame) -> StrategyResult:
        if "market_regime" not in df.columns:
            pos = pd.Series(0, index=df.index, dtype="int")
            return StrategyResult(name="router", position=pos)

        regime = df["market_regime"].astype("object")
        low_liq = df["low_liquidity_flag"].fillna(False) if "low_liquidity_flag" in df.columns else None

        pos = pd.Series(0, index=df.index, dtype="int")

        if (regime == "TREND").any():
            r = self._trend.generate(df)
            pos = pos.mask(regime == "TREND", r.position)

        if (regime == "RANGE").any():
            r = self._range.generate(df)
            pos = pos.mask(regime == "RANGE", r.position)

        if (regime == "HIGH_VOL").any():
            r = self._high_vol.generate(df)
            pos = pos.mask(regime == "HIGH_VOL", r.position)

        if low_liq is not None:
            pos = pos.mask(low_liq, 0)

        return StrategyResult(name="strategy_router", position=pos)
