from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.schema import OhlcvSchema


def add_volume_features(df: pd.DataFrame, schema: OhlcvSchema | None = None) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    close = out[s.close]
    vol = out[s.volume]

    ret = close.diff()
    direction = np.sign(ret).fillna(0)
    out["obv"] = (direction * vol).cumsum()

    rolling_mean = vol.rolling(window=20, min_periods=20).mean()
    rolling_std = vol.rolling(window=20, min_periods=20).std()
    out["volume_z_20"] = (vol - rolling_mean) / rolling_std.replace(0, pd.NA)

    out["volume_ema_20"] = vol.ewm(span=20, adjust=False).mean()

    return out
