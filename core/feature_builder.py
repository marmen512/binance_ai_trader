"""
Модуль для побудови ознак з даних OHLCV.
"""
import pandas as pd
import numpy as np


class FeatureBuilder:
    """
    Клас для створення технічних індикаторів та ознак з свічкових даних.
    """
    
    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Будує ознаки з OHLCV даних.
        
        Вхідні колонки (обов'язкові): timestamp, open, high, low, close, volume
        
        Повертає DataFrame з наступними ознаками:
        - ret_1, ret_5: прибутковість за 1 та 5 періодів
        - volatility_10: волатильність за 10 періодів
        - ema_9, ema_21, ema_diff: експоненційні ковзні середні
        - rsi: індекс відносної сили (14 періодів)
        - range, body, body_pct: характеристики свічок
        
        Args:
            df: DataFrame з колонками timestamp, open, high, low, close, volume
            
        Returns:
            DataFrame з обчисленими ознаками (без NaN рядків)
        """
        df = df.copy()
        
        # Прибутковість
        df['ret_1'] = df['close'].pct_change(1)
        df['ret_5'] = df['close'].pct_change(5)
        
        # Волатильність
        df['volatility_10'] = df['ret_1'].rolling(10).std()
        
        # EMA
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_diff'] = df['ema_9'] - df['ema_21']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Характеристики свічок
        df['range'] = df['high'] - df['low']
        df['body'] = abs(df['close'] - df['open'])
        df['body_pct'] = df['body'] / df['range'].replace(0, np.nan)
        
        # Додаткові ознаки для BTC
        df['ret1'] = df['ret_1']
        df['ret3'] = df['close'].pct_change(3)
        df['ret12'] = df['close'].pct_change(12)
        df['vol10'] = df['volatility_10']
        df['vol_spike'] = df['volume'] / df['volume'].rolling(20).mean()
        
        return df.dropna()
