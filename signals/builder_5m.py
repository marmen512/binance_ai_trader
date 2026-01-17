from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class BuildSignals5mResult:
    ok: bool
    rows_in: int
    rows_out: int
    output_path: str


def _require_xgboost():
    try:
        import xgboost as xgb  # noqa: F401

        return
    except Exception as e:
        raise BinanceAITraderError(
            "xgboost is required for build-signals-5m but is not installed. Install dependency: xgboost"
        ) from e


def build_signals_5m(
    *,
    model_dir: str | Path = Path("ai_data") / "models" / "xgb_5m",
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
    output_path: str | Path = Path("ai_data") / "signals" / "signals_5m.parquet",
    threshold: float = 0.55,
) -> BuildSignals5mResult:
    if float(threshold) != 0.55:
        raise BinanceAITraderError("Signal contract requires threshold=0.55 (do not change)")

    _require_xgboost()
    import xgboost as xgb

    model_dir = Path(model_dir)
    features_path = Path(features_path)
    output_path = Path(output_path)

    model_path = model_dir / "model.json"
    schema_path = model_dir / "feature_schema.json"

    if not model_path.exists():
        raise BinanceAITraderError(f"Missing training artifact: {model_path}")
    if not schema_path.exists():
        raise BinanceAITraderError(f"Missing training artifact: {schema_path}")

    if not features_path.exists():
        raise BinanceAITraderError(f"Missing features_5m parquet: {features_path}")

    if output_path.exists():
        raise BinanceAITraderError(f"Refusing to overwrite existing signals: {output_path}")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    feature_cols = schema.get("feature_cols")
    if not isinstance(feature_cols, list) or not feature_cols:
        raise BinanceAITraderError("feature_schema.json missing valid feature_cols")

    Xdf = pd.read_parquet(features_path)
    if "timestamp" not in Xdf.columns:
        raise BinanceAITraderError("features_5m.parquet missing required column: timestamp")

    missing = [c for c in feature_cols if c not in Xdf.columns]
    if missing:
        raise BinanceAITraderError(f"features_5m missing columns required by schema: {missing}")

    X = Xdf[feature_cols].to_numpy(dtype=np.float32)
    if not np.isfinite(X).all():
        raise BinanceAITraderError("features contain non-finite values")

    model = xgb.XGBClassifier()
    model.load_model(str(model_path))

    proba = model.predict_proba(X)
    if proba.ndim != 2 or proba.shape[1] != 3:
        raise BinanceAITraderError(f"Expected predict_proba to return shape (n,3) got {tuple(proba.shape)}")

    # Training target mapping contract: 0=sell, 1=hold, 2=buy
    p_sell = proba[:, 0]
    p_hold = proba[:, 1]
    p_buy = proba[:, 2]

    signal = np.zeros((proba.shape[0],), dtype=np.int64)
    signal[p_buy > threshold] = 1
    signal[(p_buy <= threshold) & (p_sell > threshold)] = -1

    out = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(Xdf["timestamp"], utc=True, errors="coerce"),
            "signal": signal,
            "p_buy": p_buy.astype(np.float64),
            "p_sell": p_sell.astype(np.float64),
            "p_hold": p_hold.astype(np.float64),
        }
    )

    if out["timestamp"].isna().any():
        raise BinanceAITraderError("features contain invalid timestamps")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)

    return BuildSignals5mResult(
        ok=True,
        rows_in=int(Xdf.shape[0]),
        rows_out=int(out.shape[0]),
        output_path=str(output_path),
    )
