from __future__ import annotations

import pandas as pd

from data_pipeline.schema import OhlcvSchema


def build_trade_validity_target(
    df: pd.DataFrame,
    *,
    atr_min_pct: float = 0.0005,
    bb_width_min: float = 0.002,
    rsi_low: float = 30.0,
    rsi_high: float = 70.0,
    volume_z_min: float = -1.0,
    schema: OhlcvSchema | None = None,
) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    required = [s.close, "atr_14", "bb_width_20", "rsi_14", "volume_z_20"]
    for c in required:
        if c not in out.columns:
            out["trade_validity_target"] = "SKIP"
            return out

    close = pd.to_numeric(out[s.close], errors="coerce")
    atr = pd.to_numeric(out["atr_14"], errors="coerce")
    bb = pd.to_numeric(out["bb_width_20"], errors="coerce")
    rsi = pd.to_numeric(out["rsi_14"], errors="coerce")
    volz = pd.to_numeric(out["volume_z_20"], errors="coerce")

    atr_pct = atr / close.replace(0, pd.NA)
    out["atr_pct"] = atr_pct

    trade = (
        (atr_pct >= atr_min_pct)
        & (bb >= bb_width_min)
        & (rsi >= rsi_low)
        & (rsi <= rsi_high)
        & (volz >= volume_z_min)
    )

    out["trade_validity_target"] = trade.map(lambda x: "TRADE" if bool(x) else "SKIP")
    return out
