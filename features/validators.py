from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.validators import validate_price_5m


@dataclass(frozen=True)
class VerifyFeatures5mResult:
    ok: bool
    rows: int
    feature_cols: list[str]


def verify_features_5m(
    *,
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
) -> VerifyFeatures5mResult:
    fp = Path(features_path)
    pp = Path(price_path)

    if not fp.exists():
        raise BinanceAITraderError(f"features_5m: missing parquet: {fp}")
    if not pp.exists():
        raise BinanceAITraderError(f"features_5m: missing price parquet: {pp}")

    df = pd.read_parquet(fp)
    if "timestamp" not in df.columns:
        raise BinanceAITraderError("features_5m: missing timestamp")

    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if df["timestamp"].isna().any():
        raise BinanceAITraderError("features_5m: invalid timestamps")
    if df["timestamp"].duplicated().any():
        raise BinanceAITraderError("features_5m: duplicate timestamps")
    if not df["timestamp"].is_monotonic_increasing:
        raise BinanceAITraderError("features_5m: timestamps not monotonic increasing")

    feature_cols = [c for c in df.columns if c != "timestamp"]
    if not feature_cols:
        raise BinanceAITraderError("features_5m: no feature columns")
    if len(feature_cols) > 15:
        raise BinanceAITraderError(f"features_5m: too many features: {len(feature_cols)}")

    # No NaNs / inf.
    arr = df[feature_cols].to_numpy(dtype=np.float64)
    if not np.isfinite(arr).all():
        raise BinanceAITraderError("features_5m: non-finite values detected")
    if np.isnan(arr).any():
        raise BinanceAITraderError("features_5m: NaNs detected")

    # Ensure timestamps are on the price 5m grid.
    price = pd.read_parquet(pp)
    validate_price_5m(price, coverage_min=0.99)
    pts = pd.to_datetime(price["timestamp"], utc=True)
    fts = df["timestamp"]
    if not fts.isin(pts).all():
        raise BinanceAITraderError("features_5m: timestamps are not a subset of price_5m timestamps")

    # Sanity ranges.
    if "atr_norm" in df.columns:
        v = df["atr_norm"].astype("float64")
        if not ((v > 0.0) & (v < 0.2)).all():
            raise BinanceAITraderError("features_5m: atr_norm out of expected range (0, 0.2)")

    for c in ["ret_1", "ret_3", "ret_6"]:
        if c in df.columns:
            m = float(df[c].astype("float64").mean())
            if abs(m) > 0.01:
                raise BinanceAITraderError(f"features_5m: {c} mean too far from 0: {m}")

    # Enforce sentiment lag-only usage.
    forbidden = {"sentiment_mean", "sentiment_trend", "sentiment_volatility"}
    bad = [c for c in df.columns if c in forbidden]
    if bad:
        raise BinanceAITraderError(f"features_5m: forbidden non-lag sentiment columns present: {bad}")

    return VerifyFeatures5mResult(ok=True, rows=int(df.shape[0]), feature_cols=feature_cols)
