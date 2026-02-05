"""
FeatureBuilder — будує ознаки з OHLCV для моделі.

Очікувані колонки у вхідному DataFrame:
  open, high, low, close, volume

Створює:
  ret1, ret3, ret12 — прості повернення за 1, 3, 12 періодів
  vol10 — волатильність (rolling std за 10 періодів)
  ema9, ema21 — експоненційні ковзні середні
  ema_diff — різниця ema9 - ema21
  rsi — індекс відносної сили (RSI 14)
  range — high - low
  body — abs(close - open)
  body_pct — body / close
  vol_spike — volume / volume.rolling(20).mean()
"""

import pandas as pd


class FeatureBuilder:
    """Клас для побудови фіч з OHLCV даних."""

    def build(self, df):
        """
        Будує всі фічі з OHLCV даних.

        Args:
            df (pd.DataFrame): DataFrame з колонками open, high, low, close, volume

        Returns:
            pd.DataFrame: DataFrame з усіма фічами, без NaN рядків
        """
        df = df.copy()

        # Повернення (returns)
        df['ret1'] = df['close'].pct_change(1)
        df['ret3'] = df['close'].pct_change(3)
        df['ret12'] = df['close'].pct_change(12)

        # Волатильність
        df['vol10'] = df['close'].rolling(10).std()

        # EMA
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_diff'] = df['ema9'] - df['ema21']

        # RSI 14
        df['rsi'] = self._compute_rsi(df['close'], 14)

        # Range and body
        df['range'] = df['high'] - df['low']
        df['body'] = abs(df['close'] - df['open'])
        df['body_pct'] = df['body'] / df['close']

        # Volume spike
        vol_ma = df['volume'].rolling(20).mean()
        df['vol_spike'] = df['volume'] / vol_ma

        return df.dropna()

    def _compute_rsi(self, series, period=14):
        """Обчислює RSI індикатор."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
