from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.schema import OhlcvSchema


def add_time_features(df: pd.DataFrame, schema: OhlcvSchema | None = None) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    ts = pd.to_datetime(out[s.timestamp], utc=True, errors="coerce")

    out["hour"] = ts.dt.hour
    out["dayofweek"] = ts.dt.dayofweek
    out["day"] = ts.dt.day
    out["month"] = ts.dt.month

    out["hour_sin"] = np.sin(2 * np.pi * out["hour"] / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * out["hour"] / 24.0)
    out["dow_sin"] = np.sin(2 * np.pi * out["dayofweek"] / 7.0)
    out["dow_cos"] = np.cos(2 * np.pi * out["dayofweek"] / 7.0)

    return out
