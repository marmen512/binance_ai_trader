from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DecisionConfig:
    max_leverage: float = 1.0
    min_signal: float = 0.0
    risk_vol_col: str = "vol_20"
    risk_atr_col: str = "atr_pct"


def _risk_scale(df: pd.DataFrame, cfg: DecisionConfig) -> pd.Series:
    if cfg.risk_atr_col in df.columns:
        atr = pd.to_numeric(df[cfg.risk_atr_col], errors="coerce")
        return atr.abs().replace(0.0, np.nan)

    if cfg.risk_vol_col in df.columns:
        vol = pd.to_numeric(df[cfg.risk_vol_col], errors="coerce")
        return vol.abs().replace(0.0, np.nan)

    return pd.Series(1.0, index=df.index, dtype="float64")


def predictions_to_position(df: pd.DataFrame, y_hat: pd.Series, cfg: DecisionConfig) -> pd.Series:
    risk = _risk_scale(df, cfg).ffill().bfill().fillna(1.0)
    raw = (y_hat / risk).replace([np.inf, -np.inf], 0.0).fillna(0.0)

    pos = raw.clip(-cfg.max_leverage, cfg.max_leverage)

    if cfg.min_signal > 0:
        pos = pos.mask(pos.abs() < cfg.min_signal, 0.0)

    if "low_liquidity_flag" in df.columns:
        low_liq = df["low_liquidity_flag"].fillna(False)
        pos = pos.mask(low_liq, 0.0)

    if "trade_validity_target" in df.columns:
        tv = df["trade_validity_target"].astype("object")
        pos = pos.mask(tv == "SKIP", 0.0)

    return pos.astype("float64")
