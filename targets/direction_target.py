from __future__ import annotations

import numpy as np
import pandas as pd

from data_pipeline.schema import OhlcvSchema


def build_direction_target(
    df: pd.DataFrame,
    *,
    horizon: int = 1,
    lower_q: float = 0.33,
    upper_q: float = 0.66,
    schema: OhlcvSchema | None = None,
) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    close = pd.to_numeric(out[s.close], errors="coerce")
    future = close.shift(-horizon)
    future_log_ret = np.log(future) - np.log(close)

    q_low = float(future_log_ret.quantile(lower_q))
    q_high = float(future_log_ret.quantile(upper_q))

    out["future_log_return"] = future_log_ret

    direction = pd.Series("FLAT", index=out.index, dtype="object")
    direction = direction.mask(future_log_ret > q_high, "UP")
    direction = direction.mask(future_log_ret < q_low, "DOWN")

    out["direction_target"] = direction
    out["direction_q_low"] = q_low
    out["direction_q_high"] = q_high
    return out
