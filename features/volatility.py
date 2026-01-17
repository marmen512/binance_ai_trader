from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.schema import OhlcvSchema


def _true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def add_volatility_features(df: pd.DataFrame, schema: OhlcvSchema | None = None) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    close = out[s.close]
    high = out[s.high]
    low = out[s.low]

    out["log_return"] = np.log(close).diff()
    out["ret_1"] = close.pct_change(1)

    tr = _true_range(high=high, low=low, close=close)
    out["atr_14"] = tr.rolling(window=14, min_periods=14).mean()

    out["vol_20"] = out["log_return"].rolling(window=20, min_periods=20).std()

    mid = close.rolling(window=20, min_periods=20).mean()
    std = close.rolling(window=20, min_periods=20).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    out["bb_width_20"] = (upper - lower) / mid.replace(0, pd.NA)

    return out
