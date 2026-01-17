from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


def validate_price_1h(df: pd.DataFrame, *, min_rows: int = 1000) -> None:
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"Price dataset missing columns: {missing}")

    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if ts.isna().any():
        raise BinanceAITraderError("Price dataset has invalid timestamps")

    if ts.duplicated().any():
        raise BinanceAITraderError("Price dataset has duplicate timestamps")

    if not ts.is_monotonic_increasing:
        raise BinanceAITraderError("Price dataset timestamps are not monotonic increasing")

    # Enforce 1H grid (exact deltas).
    if ts.size >= 3:
        diffs = ts.diff().dropna().dt.total_seconds()
        diffs = diffs[(diffs > 0) & pd.notna(diffs)]
        if not diffs.empty:
            med = float(diffs.median())
            if abs(med - 3600.0) > 15.0:
                raise BinanceAITraderError(f"Price dataset is not 1H (median diff={med}s)")

    if int(df.shape[0]) < int(min_rows):
        raise BinanceAITraderError(f"Price dataset too small: rows={df.shape[0]}")


def validate_sentiment_agg_1h(df: pd.DataFrame, *, min_rows: int = 50) -> None:
    required = ["timestamp", "sentiment_mean", "sentiment_std", "sentiment_count"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"Sentiment aggregated missing columns: {missing}")

    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    if ts.isna().any():
        raise BinanceAITraderError("Sentiment aggregated has invalid timestamps")

    if not ts.is_monotonic_increasing:
        raise BinanceAITraderError("Sentiment aggregated timestamps are not monotonic increasing")

    if df[required].isna().any().any():
        raise BinanceAITraderError("Sentiment aggregated contains NaNs")

    if int(df.shape[0]) < int(min_rows):
        raise BinanceAITraderError(f"Sentiment aggregated too small: rows={df.shape[0]}")


def validate_parquet_exists(path: str | Path) -> None:
    if not Path(path).exists():
        raise BinanceAITraderError(f"Missing parquet: {path}")


def _coerce_ts(ts: pd.Series) -> pd.Series:
    return pd.to_datetime(ts, utc=True, errors="coerce")


def _require_monotonic_unique(ts: pd.Series, *, name: str) -> pd.Series:
    ts2 = _coerce_ts(ts)
    if ts2.isna().any():
        raise BinanceAITraderError(f"{name}: invalid timestamps")
    if ts2.duplicated().any():
        raise BinanceAITraderError(f"{name}: duplicate timestamps")
    if not ts2.is_monotonic_increasing:
        raise BinanceAITraderError(f"{name}: timestamps not monotonic increasing")
    return ts2


def _require_5m_grid(ts: pd.Series, *, name: str, tolerance_s: float = 2.0) -> None:
    if ts.size < 3:
        raise BinanceAITraderError(f"{name}: too few rows")
    diffs = ts.diff().dropna().dt.total_seconds()
    diffs = diffs[(diffs > 0) & np.isfinite(diffs)]
    if diffs.empty:
        raise BinanceAITraderError(f"{name}: cannot infer frequency")
    med = float(diffs.median())
    if abs(med - 300.0) > float(tolerance_s):
        raise BinanceAITraderError(f"{name}: not 5m grid (median diff={med}s)")


def _coverage_ratio_fixed(ts: pd.Series, *, freq: str) -> float:
    if ts.size < 2:
        return 0.0
    start = ts.iloc[0]
    end = ts.iloc[-1]
    if end <= start:
        return 0.0
    full = pd.date_range(start=start, end=end, freq=freq, tz="UTC")
    if full.size <= 0:
        return 0.0
    return float(min(1.0, ts.size / full.size))


def _require_fresh(ts: pd.Series, *, name: str, max_lag_s: int = 600) -> None:
    if ts.empty:
        raise BinanceAITraderError(f"{name}: empty dataset")
    now = datetime.now(timezone.utc)
    last = ts.iloc[-1].to_pydatetime()
    lag_s = (now - last).total_seconds()
    if lag_s > float(max_lag_s):
        raise BinanceAITraderError(f"{name}: stale data (lag_s={lag_s:.0f} > {max_lag_s})")


def validate_price_5m(
    df: pd.DataFrame,
    *,
    min_rows: int = 1000,
    coverage_min: float = 0.99,
    require_freshness: bool = False,
    max_lag_s: int = 600,
) -> None:
    required = ["timestamp", "open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"price_5m: missing columns: {missing}")

    out = df.copy()
    out["timestamp"] = _require_monotonic_unique(out["timestamp"], name="price_5m")
    _require_5m_grid(out["timestamp"], name="price_5m")

    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if out[["open", "high", "low", "close", "volume"]].isna().any().any():
        raise BinanceAITraderError("price_5m: NaNs present")

    if (out["volume"] < 0).any():
        raise BinanceAITraderError("price_5m: negative volume")
    if (out[["open", "high", "low", "close"]] <= 0).any().any():
        raise BinanceAITraderError("price_5m: non-positive prices")
    if (out["high"] < out[["open", "close", "low"]].max(axis=1)).any():
        raise BinanceAITraderError("price_5m: high violates OHLC")
    if (out["low"] > out[["open", "close", "high"]].min(axis=1)).any():
        raise BinanceAITraderError("price_5m: low violates OHLC")
    if (out["high"] < out["low"]).any():
        raise BinanceAITraderError("price_5m: high < low")

    if int(out.shape[0]) < int(min_rows):
        raise BinanceAITraderError(f"price_5m: too few rows: {out.shape[0]}")

    cov = _coverage_ratio_fixed(out["timestamp"], freq="5min")
    if cov < float(coverage_min):
        raise BinanceAITraderError(f"price_5m: coverage < {coverage_min:.2%}: {cov:.3f}")

    if require_freshness:
        _require_fresh(out["timestamp"], name="price_5m", max_lag_s=int(max_lag_s))


def validate_funding_rate_5m(
    df: pd.DataFrame,
    *,
    nan_max_ratio: float = 0.01,
    require_freshness: bool = False,
    max_lag_s: int = 600,
) -> None:
    required = ["timestamp", "funding_rate"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"funding_rate_5m: missing columns: {missing}")

    out = df.copy()
    out["timestamp"] = _require_monotonic_unique(out["timestamp"], name="funding_rate_5m")
    _require_5m_grid(out["timestamp"], name="funding_rate_5m")
    out["funding_rate"] = pd.to_numeric(out["funding_rate"], errors="coerce")

    nan_ratio = float(out["funding_rate"].isna().mean())
    if nan_ratio > float(nan_max_ratio):
        raise BinanceAITraderError(f"funding_rate_5m: NaN ratio too high: {nan_ratio:.4f}")

    if require_freshness:
        _require_fresh(out["timestamp"], name="funding_rate_5m", max_lag_s=int(max_lag_s))


def validate_open_interest_5m(
    df: pd.DataFrame,
    *,
    nan_max_ratio: float = 0.01,
    require_freshness: bool = False,
    max_lag_s: int = 600,
) -> None:
    required = ["timestamp", "open_interest"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"open_interest_5m: missing columns: {missing}")

    out = df.copy()
    out["timestamp"] = _require_monotonic_unique(out["timestamp"], name="open_interest_5m")
    _require_5m_grid(out["timestamp"], name="open_interest_5m")
    out["open_interest"] = pd.to_numeric(out["open_interest"], errors="coerce")

    nan_ratio = float(out["open_interest"].isna().mean())
    if nan_ratio > float(nan_max_ratio):
        raise BinanceAITraderError(f"open_interest_5m: NaN ratio too high: {nan_ratio:.4f}")

    if require_freshness:
        _require_fresh(out["timestamp"], name="open_interest_5m", max_lag_s=int(max_lag_s))


def validate_sentiment_agg_5m(
    df: pd.DataFrame,
    *,
    nan_max_ratio: float = 0.01,
    require_freshness: bool = False,
    max_lag_s: int = 600,
) -> None:
    required = ["timestamp", "sentiment_mean", "sentiment_std", "sentiment_trend", "sentiment_volatility"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise BinanceAITraderError(f"sentiment_5m: missing columns: {missing}")

    out = df.copy()
    out["timestamp"] = _require_monotonic_unique(out["timestamp"], name="sentiment_5m")
    _require_5m_grid(out["timestamp"], name="sentiment_5m")
    for c in required[1:]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    nan_ratio = float(out[required[1:]].isna().mean().max())
    if nan_ratio > float(nan_max_ratio):
        raise BinanceAITraderError(f"sentiment_5m: NaN ratio too high: {nan_ratio:.4f}")

    if require_freshness:
        _require_fresh(out["timestamp"], name="sentiment_5m", max_lag_s=int(max_lag_s))
