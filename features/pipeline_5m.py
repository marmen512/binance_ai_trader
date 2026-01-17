from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.validators import (
    validate_funding_rate_5m,
    validate_open_interest_5m,
    validate_price_5m,
    validate_sentiment_agg_5m,
)


@dataclass(frozen=True)
class BuildFeatures5mResult:
    ok: bool
    rows_in: int
    rows_out: int
    feature_cols: list[str]
    output_path: str


def _zscore(s: pd.Series, window: int) -> pd.Series:
    mu = s.rolling(window, min_periods=window).mean()
    sd = s.rolling(window, min_periods=window).std(ddof=0)
    z = (s - mu) / sd
    return z


def _atr_14(df: pd.DataFrame) -> pd.Series:
    high = df["high"].astype("float64")
    low = df["low"].astype("float64")
    close = df["close"].astype("float64")
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(14, min_periods=14).mean()
    return atr


def _rsi(df: pd.DataFrame, period: int) -> pd.Series:
    close = df["close"].astype("float64")
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    roll_up = up.rolling(period, min_periods=period).mean()
    roll_down = down.rolling(period, min_periods=period).mean()
    rs = roll_up / roll_down
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def build_features_5m(
    *,
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
    funding_path: str | Path = Path("ai_data") / "derivatives" / "funding_rate_5m.parquet",
    oi_path: str | Path = Path("ai_data") / "derivatives" / "open_interest_5m.parquet",
    sentiment_path: str | Path = Path("ai_data") / "sentiment" / "aggregated" / "sentiment_5m.parquet",
    output_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
) -> BuildFeatures5mResult:
    pp = Path(price_path)
    fp = Path(funding_path)
    op = Path(oi_path)
    sp = Path(sentiment_path)

    for p in [pp, fp, op, sp]:
        if not p.exists():
            raise BinanceAITraderError(f"Missing input parquet: {p}")

    price = pd.read_parquet(pp)
    funding = pd.read_parquet(fp)
    oi = pd.read_parquet(op)
    sent = pd.read_parquet(sp)

    # Fail fast on upstream data quality.
    validate_price_5m(price, coverage_min=0.99)
    validate_funding_rate_5m(funding, nan_max_ratio=0.01)
    validate_open_interest_5m(oi, nan_max_ratio=0.01)
    validate_sentiment_agg_5m(sent, nan_max_ratio=0.01)

    df = price.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    funding2 = funding[["timestamp", "funding_rate"]].copy()
    funding2["timestamp"] = pd.to_datetime(funding2["timestamp"], utc=True, errors="coerce")

    oi2 = oi[["timestamp", "open_interest"]].copy()
    oi2["timestamp"] = pd.to_datetime(oi2["timestamp"], utc=True, errors="coerce")

    sent2 = sent[["timestamp", "sentiment_mean", "sentiment_trend", "sentiment_volatility"]].copy()
    sent2["timestamp"] = pd.to_datetime(sent2["timestamp"], utc=True, errors="coerce")

    df = df.merge(funding2, on="timestamp", how="left")
    df = df.merge(oi2, on="timestamp", how="left")
    df = df.merge(sent2, on="timestamp", how="left")

    rows_in = int(df.shape[0])

    close = df["close"].astype("float64")
    df["ret_1"] = np.log(close / close.shift(1))
    df["ret_3"] = np.log(close / close.shift(3))
    df["ret_6"] = np.log(close / close.shift(6))

    df["range_norm"] = (df["high"].astype("float64") - df["low"].astype("float64")) / close

    df["vol_z_48"] = _zscore(df["volume"].astype("float64"), window=48)

    df["atr_14"] = _atr_14(df)
    df["atr_norm"] = df["atr_14"] / close

    df["rsi_5"] = _rsi(df, period=5)
    df["rsi_14"] = _rsi(df, period=14)

    df["oi_delta"] = df["open_interest"].astype("float64").diff()

    # Lagged sentiment only (no real-time signal).
    df["sent_mean_lag1"] = df["sentiment_mean"].astype("float64").shift(1)
    df["sent_trend_lag1"] = df["sentiment_trend"].astype("float64").shift(1)
    df["sent_vol_lag1"] = df["sentiment_volatility"].astype("float64").shift(1)

    # Time bias features (UTC hour-of-day).
    hour = pd.to_datetime(df["timestamp"], utc=True).dt.hour.astype("float64")
    phase = 2.0 * np.pi * hour / 24.0
    df["hour_sin"] = np.sin(phase)
    df["hour_cos"] = np.cos(phase)

    feature_cols = [
        "ret_1",
        "ret_3",
        "ret_6",
        "range_norm",
        "vol_z_48",
        "atr_14",
        "atr_norm",
        "rsi_5",
        "rsi_14",
        "funding_rate",
        "oi_delta",
        "sent_mean_lag1",
        "sent_trend_lag1",
        "sent_vol_lag1",
        "hour_sin",
        "hour_cos",
    ]

    # Enforce <= 15 features (drop hour_cos first).
    if len(feature_cols) > 15:
        feature_cols = [c for c in feature_cols if c != "hour_cos"]

    keep = ["timestamp"] + feature_cols
    out = df[keep].copy()

    # Hard requirement for downstream: no NaNs / no inf.
    out = out.replace([np.inf, -np.inf], np.nan)
    out2 = out.dropna().reset_index(drop=True)
    if out2.empty:
        raise BinanceAITraderError("features_5m: empty after dropping NaNs")

    out_p = Path(output_path)
    if out_p.exists():
        raise BinanceAITraderError(f"Refusing to overwrite features dataset: {out_p}")
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out2.to_parquet(out_p, index=False)

    return BuildFeatures5mResult(
        ok=True,
        rows_in=rows_in,
        rows_out=int(out2.shape[0]),
        feature_cols=list(feature_cols),
        output_path=str(out_p),
    )
