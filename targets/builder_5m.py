from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class BuildTargets5mResult:
    ok: bool
    rows_in: int
    rows_out: int
    horizon: int
    output_path: str


def build_targets_5m(
    *,
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
    output_path: str | Path = Path("ai_data") / "targets" / "targets_5m.parquet",
    horizon: int = 3,
) -> BuildTargets5mResult:
    if int(horizon) != 3:
        raise BinanceAITraderError("5m target contract requires horizon=3 (15 minutes)")

    features_path = Path(features_path)
    price_path = Path(price_path)
    output_path = Path(output_path)

    if not features_path.exists():
        raise BinanceAITraderError(f"Missing features_5m parquet: {features_path}")
    if not price_path.exists():
        raise BinanceAITraderError(f"Missing price_5m parquet: {price_path}")

    if output_path.exists():
        raise BinanceAITraderError(f"Refusing to overwrite existing targets: {output_path}")

    X = pd.read_parquet(features_path)
    if "timestamp" not in X.columns:
        raise BinanceAITraderError("features_5m.parquet missing required column: timestamp")

    X_ts = pd.to_datetime(X["timestamp"], utc=True, errors="coerce")
    if X_ts.isna().any():
        raise BinanceAITraderError("features_5m.parquet contains invalid timestamps")

    price = pd.read_parquet(price_path)
    if "timestamp" not in price.columns or "close" not in price.columns:
        raise BinanceAITraderError("price_5m parquet must contain columns: timestamp, close")

    p_ts = pd.to_datetime(price["timestamp"], utc=True, errors="coerce")
    if p_ts.isna().any():
        raise BinanceAITraderError("price_5m parquet contains invalid timestamps")

    price2 = price.copy()
    price2["timestamp"] = p_ts
    price2 = price2[["timestamp", "close"]].sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")

    merged = pd.DataFrame({"timestamp": X_ts}).merge(price2, on="timestamp", how="left")
    if merged["close"].isna().any():
        missing = int(merged["close"].isna().sum())
        raise BinanceAITraderError(
            f"price_5m missing close for {missing} feature timestamps; cannot build leakage-free targets"
        )

    merged = merged.sort_values("timestamp").reset_index(drop=True)

    close = merged["close"].astype(float)
    future_close = close.shift(-horizon)
    lr = np.log(future_close / close)

    y_sign = np.sign(lr).astype("float")
    y_sign = y_sign.replace({-0.0: 0.0})

    y = pd.Series(y_sign, name="y")
    y = y.iloc[:-horizon]

    out_ts = merged["timestamp"].iloc[:-horizon]

    y_int = y.astype(int)
    y_xgb = y_int.map({-1: 0, 0: 1, 1: 2}).astype(int)

    out = pd.DataFrame(
        {
            "timestamp": out_ts.reset_index(drop=True),
            "y": y_int.reset_index(drop=True),
            "y_xgb": y_xgb.reset_index(drop=True),
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)

    return BuildTargets5mResult(
        ok=True,
        rows_in=int(X.shape[0]),
        rows_out=int(out.shape[0]),
        horizon=int(horizon),
        output_path=str(output_path),
    )
