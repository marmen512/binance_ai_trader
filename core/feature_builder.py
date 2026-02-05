"""
Модуль побудови ознак для моделі AI.
Feature engineering pipeline для створення технічних індикаторів.
"""
import pandas as pd
import numpy as np


class FeatureBuilder:
    """Будівельник ознак для торгових сигналів."""
    
    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Обчислює технічні індикатори та повертає датафрейм з ознаками.
        
        Args:
            df: DataFrame з колонками open, high, low, close, volume
            
        Returns:
            DataFrame з новими ознаками
        """
        df = df.copy()
        
        # Прибутковість (Returns)
        df['ret_1'] = df['close'].pct_change(1)
        df['ret_5'] = df['close'].pct_change(5)
        
        # Волатильність
        df['volatility_10'] = df['ret_1'].rolling(10).std()
        
        # EMA (Exponential Moving Average)
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_diff'] = (df['ema_9'] - df['ema_21']) / df['ema_21']
        
        # RSI (Relative Strength Index)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Діапазон та тіло свічки
        df['range'] = (df['high'] - df['low']) / df['close']
        df['body'] = (df['close'] - df['open']) / df['close']
        df['body_pct'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
        
        return df.dropna()
