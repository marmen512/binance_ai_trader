from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class VerifySignals5mResult:
    ok: bool
    rows: int
    signal_counts: dict[int, int]


def verify_signals_5m(
    *,
    signals_path: str | Path = Path("ai_data") / "signals" / "signals_5m.parquet",
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
) -> VerifySignals5mResult:
    signals_path = Path(signals_path)
    features_path = Path(features_path)

    if not signals_path.exists():
        raise BinanceAITraderError(f"Missing signals_5m parquet: {signals_path}")
    if not features_path.exists():
        raise BinanceAITraderError(f"Missing features_5m parquet: {features_path}")

    sdf = pd.read_parquet(signals_path)
    Xdf = pd.read_parquet(features_path)

    required = {"timestamp", "signal", "p_buy", "p_sell", "p_hold"}
    missing_cols = sorted(required - set(sdf.columns))
    if missing_cols:
        raise BinanceAITraderError(f"signals_5m missing required columns: {missing_cols}")

    if "timestamp" not in Xdf.columns:
        raise BinanceAITraderError("features_5m.parquet missing required column: timestamp")

    s_ts = pd.to_datetime(sdf["timestamp"], utc=True, errors="coerce").reset_index(drop=True)
    x_ts = pd.to_datetime(Xdf["timestamp"], utc=True, errors="coerce").reset_index(drop=True)

    if s_ts.isna().any() or x_ts.isna().any():
        raise BinanceAITraderError("signals/features contain invalid timestamps")

    if s_ts.shape[0] != x_ts.shape[0]:
        raise BinanceAITraderError(
            f"signals/features row mismatch: signals={int(s_ts.shape[0])} features={int(x_ts.shape[0])}"
        )

    if not s_ts.equals(x_ts):
        raise BinanceAITraderError("Index misalignment: signals timestamps must equal features timestamps")

    if sdf[["signal", "p_buy", "p_sell", "p_hold"]].isna().any().any():
        raise BinanceAITraderError("signals contain NaNs")

    arr = sdf[["signal", "p_buy", "p_sell", "p_hold"]].to_numpy(dtype=np.float64)
    if not np.isfinite(arr).all():
        raise BinanceAITraderError("signals contain non-finite values")

    sig = sdf["signal"].astype(int)
    if not sig.isin([-1, 0, 1]).all():
        bad = sorted(set(sig.unique().tolist()) - {-1, 0, 1})
        raise BinanceAITraderError(f"signals contain invalid classes: {bad}")

    for c in ["p_buy", "p_sell", "p_hold"]:
        v = sdf[c].astype(np.float64)
        if (v < -1e-9).any() or (v > 1.0 + 1e-9).any():
            raise BinanceAITraderError(f"{c} must be within [0,1]")

    s = sdf[["p_buy", "p_sell", "p_hold"]].sum(axis=1).to_numpy(dtype=np.float64)
    if not np.all(np.isfinite(s)):
        raise BinanceAITraderError("probability sums contain non-finite values")

    # tolerate tiny numerical drift
    if np.max(np.abs(s - 1.0)) > 1e-3:
        raise BinanceAITraderError("probabilities must sum to 1 (within tolerance)")

    counts = sig.value_counts().to_dict()
    signal_counts: dict[int, int] = {int(k): int(v) for k, v in counts.items()}

    return VerifySignals5mResult(ok=True, rows=int(sdf.shape[0]), signal_counts=signal_counts)
