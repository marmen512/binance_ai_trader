from __future__ import annotations

import pandas as pd

from data_pipeline.schema import OhlcvSchema


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))

    # Edge cases
    # - avg_loss == 0 and avg_gain > 0 -> RSI = 100
    # - avg_gain == 0 and avg_loss > 0 -> RSI = 0
    # - both == 0 -> RSI = 50
    both_zero = (avg_gain == 0) & (avg_loss == 0)
    loss_zero = (avg_loss == 0) & (avg_gain > 0)
    gain_zero = (avg_gain == 0) & (avg_loss > 0)

    rsi = rsi.mask(loss_zero, 100.0)
    rsi = rsi.mask(gain_zero, 0.0)
    rsi = rsi.mask(both_zero, 50.0)

    return rsi


def add_technical_features(df: pd.DataFrame, schema: OhlcvSchema | None = None) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    close = out[s.close]

    out["sma_10"] = close.rolling(window=10, min_periods=10).mean()
    out["sma_20"] = close.rolling(window=20, min_periods=20).mean()
    out["ema_12"] = _ema(close, span=12)
    out["ema_26"] = _ema(close, span=26)

    out["rsi_14"] = _rsi(close, period=14)

    macd = out["ema_12"] - out["ema_26"]
    signal = macd.ewm(span=9, adjust=False).mean()
    out["macd"] = macd
    out["macd_signal"] = signal
    out["macd_hist"] = macd - signal

    return out
