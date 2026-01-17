from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class VerifyTargets5mResult:
    ok: bool
    rows: int
    classes: list[int]
    max_class_ratio: float
    horizon: int


def verify_targets_5m(
    *,
    targets_path: str | Path = Path("ai_data") / "targets" / "targets_5m.parquet",
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
    horizon: int = 3,
) -> VerifyTargets5mResult:
    if int(horizon) != 3:
        raise BinanceAITraderError("5m target contract requires horizon=3 (15 minutes)")

    targets_path = Path(targets_path)
    features_path = Path(features_path)

    if not targets_path.exists():
        raise BinanceAITraderError(f"Missing targets_5m parquet: {targets_path}")
    if not features_path.exists():
        raise BinanceAITraderError(f"Missing features_5m parquet: {features_path}")

    ydf = pd.read_parquet(targets_path)
    X = pd.read_parquet(features_path)

    if "timestamp" not in ydf.columns:
        raise BinanceAITraderError("targets_5m.parquet missing required column: timestamp")
    if "timestamp" not in X.columns:
        raise BinanceAITraderError("features_5m.parquet missing required column: timestamp")

    if "y" not in ydf.columns or "y_xgb" not in ydf.columns:
        raise BinanceAITraderError("targets_5m.parquet must contain columns: y, y_xgb")

    y_ts = pd.to_datetime(ydf["timestamp"], utc=True, errors="coerce")
    X_ts = pd.to_datetime(X["timestamp"], utc=True, errors="coerce")
    if y_ts.isna().any():
        raise BinanceAITraderError("targets_5m.parquet contains invalid timestamps")
    if X_ts.isna().any():
        raise BinanceAITraderError("features_5m.parquet contains invalid timestamps")

    expected_ts = X_ts.iloc[:-horizon].reset_index(drop=True)
    actual_ts = y_ts.reset_index(drop=True)

    if expected_ts.shape[0] != actual_ts.shape[0]:
        raise BinanceAITraderError(
            f"targets rows mismatch: expected {int(expected_ts.shape[0])} (features minus horizon) got {int(actual_ts.shape[0])}"
        )

    if not expected_ts.equals(actual_ts):
        raise BinanceAITraderError("Target index misalignment: y.index must equal X.index (minus horizon)")

    if ydf[["y", "y_xgb"]].isna().any().any():
        raise BinanceAITraderError("targets contain NaNs")

    vals = ydf["y"].astype(int)
    if not vals.isin([-1, 0, 1]).all():
        bad = sorted(set(vals.unique().tolist()) - {-1, 0, 1})
        raise BinanceAITraderError(f"targets y contains invalid classes: {bad}")

    xgb_vals = ydf["y_xgb"].astype(int)
    if not xgb_vals.isin([0, 1, 2]).all():
        bad = sorted(set(xgb_vals.unique().tolist()) - {0, 1, 2})
        raise BinanceAITraderError(f"targets y_xgb contains invalid classes: {bad}")

    classes = sorted(int(x) for x in vals.unique().tolist())
    if len(classes) < 2:
        raise BinanceAITraderError("targets must have at least 2 classes")

    counts = vals.value_counts(dropna=False)
    total = float(vals.shape[0])
    max_ratio = float((counts.max() / total) if total > 0 else 1.0)
    if max_ratio > 0.80:
        raise BinanceAITraderError(f"targets class imbalance too high: max_class_ratio={max_ratio:.3f} > 0.80")

    if not np.isfinite(ydf[["y", "y_xgb"]].to_numpy()).all():
        raise BinanceAITraderError("targets contain non-finite values")

    return VerifyTargets5mResult(
        ok=True,
        rows=int(vals.shape[0]),
        classes=classes,
        max_class_ratio=max_ratio,
        horizon=int(horizon),
    )
