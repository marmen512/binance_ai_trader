"""
FeatureBuilder - побудова ознак з OHLCV даних.

Очікувані вхідні колонки: timestamp, open, high, low, close, volume
"""
import pandas as pd
import numpy as np


class FeatureBuilder:
    """
    Клас для побудови ознак з OHLCV даних для ML моделей.
    """

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Обчислює технічні індикатори та ознаки з OHLCV даних.
        
        Args:
            df: DataFrame з колонками timestamp, open, high, low, close, volume
            
        Returns:
            DataFrame з додатковими колонками ознак
        """
        df = df.copy()
        
        # Прибутковість за різні періоди
        df['ret1'] = df['close'].pct_change(1)
        df['ret3'] = df['close'].pct_change(3)
        df['ret12'] = df['close'].pct_change(12)
        
        # Волатильність (rolling std returns за 10 periods)
        df['vol10'] = df['ret1'].rolling(window=10).std()
        
        # EMA
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_diff'] = (df['ema9'] - df['ema21']) / df['close']
        
        # RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Range та body
        df['range'] = df['high'] - df['low']
        df['body'] = df['close'] - df['open']
        df['body_pct'] = df['body'] / df['close']
        
        # Volume spike
        vol_ma = df['volume'].rolling(window=20).mean()
        df['vol_spike'] = df['volume'] / vol_ma
        
        # Видаляємо NaN
        return df.dropna()
