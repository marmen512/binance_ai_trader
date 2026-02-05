"""
Модуль побудови ознак для торгового алгоритму.

Цей модуль містить клас FeatureBuilder для створення технічних індикаторів
та похідних ознак з OHLCV даних.
"""

import pandas as pd
import numpy as np


class FeatureBuilder:
    """
    Клас для побудови технічних ознак з OHLCV даних.
    
    Очікувані колонки у вхідному DataFrame:
    - timestamp: мітка часу
    - open: ціна відкриття
    - high: максимальна ціна
    - low: мінімальна ціна
    - close: ціна закриття
    - volume: обсяг торгів
    """
    
    def build(self, df):
        """
        Обчислює технічні індикатори та ознаки на основі OHLCV даних.
        
        Створює наступні ознаки:
        - ret1, ret3, ret12: прибутковість за 1, 3, 12 періодів
        - vol10: 10-періодна волатильність (стандартне відхилення прибутковості)
        - ema_diff: різниця між EMA(12) та EMA(26)
        - rsi: індекс відносної сили (14 періодів)
        - body: розмір тіла свічки (close - open)
        - body_pct: відсоток тіла свічки відносно діапазону high-low
        - vol_spike: спайк обсягу (поточний обсяг / середній обсяг за 20 періодів)
        
        Параметри:
            df (pd.DataFrame): DataFrame з OHLCV даними
            
        Повертає:
            pd.DataFrame: DataFrame з додатковими колонками ознак, без NaN значень
        """
        df = df.copy()
        
        # Прибутковість за різні періоди
        df['ret1'] = df['close'].pct_change(1)  # 1-періодна прибутковість
        df['ret3'] = df['close'].pct_change(3)  # 3-періодна прибутковість
        df['ret12'] = df['close'].pct_change(12)  # 12-періодна прибутковість
        
        # Волатильність (стандартне відхилення прибутковості за 10 періодів)
        df['vol10'] = df['ret1'].rolling(10).std()
        
        # Різниця між швидкою та повільною EMA
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['ema_diff'] = ema12 - ema26
        
        # RSI (Relative Strength Index) - індекс відносної сили
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Ознаки свічкового аналізу
        df['body'] = df['close'] - df['open']  # Розмір тіла свічки
        range_ = df['high'] - df['low']
        df['body_pct'] = df['body'] / range_.replace(0, np.nan)  # Відсоток тіла
        
        # Спайк обсягу (поточний обсяг відносно середнього)
        vol_ma20 = df['volume'].rolling(20).mean()
        df['vol_spike'] = df['volume'] / vol_ma20.replace(0, np.nan)
        
        # Видаляємо рядки з NaN значеннями
        return df.dropna()
