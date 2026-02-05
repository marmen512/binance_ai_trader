"""
Детектор ринкового режиму.
Визначає поточний режим: VOLATILE, TREND, RANGE.
"""
import pandas as pd
import numpy as np


class RegimeDetector:
    """
    Детектор ринкового режиму на основі волатильності та тренду.
    """
    
    def __init__(self, vol_window=20, trend_window_short=20, trend_window_long=50):
        """
        Ініціалізація детектора.
        
        Args:
            vol_window: Вікно для обчислення волатильності
            trend_window_short: Коротке вікно для EMA тренду
            trend_window_long: Довге вікно для EMA тренду
        """
        self.vol_window = vol_window
        self.trend_window_short = trend_window_short
        self.trend_window_long = trend_window_long
    
    def detect(self, df: pd.DataFrame) -> str:
        """
        Визначає поточний режим ринку.
        
        Args:
            df: DataFrame з колонкою 'close'
            
        Returns:
            'VOLATILE', 'TREND', або 'RANGE'
        """
        # Обчислення волатильності
        returns = df['close'].pct_change()
        volatility = returns.rolling(self.vol_window).std().iloc[-1]
        
        # Обчислення тренду
        ema_short = df['close'].ewm(span=self.trend_window_short, adjust=False).mean().iloc[-1]
        ema_long = df['close'].ewm(span=self.trend_window_long, adjust=False).mean().iloc[-1]
        trend_metric = abs(ema_short - ema_long) / ema_long
        
        # Визначення режиму
        # Високоволатильний режим
        if volatility > 0.02:
            return 'VOLATILE'
        
        # Трендовий режим
        if trend_metric > 0.01:
            return 'TREND'
        
        # Флетовий режим
        return 'RANGE'
