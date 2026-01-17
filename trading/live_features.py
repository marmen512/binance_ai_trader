from __future__ import annotations

import pandas as pd

from data_pipeline.normalization import normalize_columns
from features.copy_trader_stats import add_copy_trader_stats
from features.technical import add_technical_features
from features.time_features import add_time_features
from features.volatility import add_volatility_features
from features.volume import add_volume_features


def build_live_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build features for live/paper trading.

    Contract:
    - Uses the same feature set as offline training/paper loop.
    - No future leakage: features are computed row-wise from past rolling windows.
    - Drops rows with NaNs introduced by rolling windows.

    Input schema expects at least: timestamp/open/high/low/close/volume
    (timestamp must be UTC-aware or parseable).
    """

    out = normalize_columns(df)

    out = add_technical_features(out)
    out = add_volatility_features(out)
    out = add_volume_features(out)
    out = add_time_features(out)
    out = add_copy_trader_stats(out)

    return out.dropna().reset_index(drop=True)
