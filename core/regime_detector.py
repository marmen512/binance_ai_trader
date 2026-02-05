"""
RegimeDetector — визначає ринковий режим (VOLATILE, TREND, RANGE).
"""

import pandas as pd


class RegimeDetector:
    """Детектор ринкових режимів."""

    def detect(self, window_df):
        """
        Визначає режим ринку на основі вікна даних.

        Args:
            window_df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            str: 'VOLATILE', 'TREND', або 'RANGE'
        """
        if len(window_df) < 50:
            return 'RANGE'

        # Обчислюємо волатильність (rolling std за 20 періодів)
        volatility = window_df['close'].rolling(20).std().iloc[-1]

        # Обчислюємо тренд метрику (EMA 20 / EMA 50)
        ema20 = window_df['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        ema50 = window_df['close'].ewm(span=50, adjust=False).mean().iloc[-1]
        
        trend_metric = (ema20 - ema50) / ema50 if ema50 != 0 else 0

        # Визначаємо режим
        if volatility > 0.02:
            return 'VOLATILE'
        elif abs(trend_metric) > 0.004:
            return 'TREND'
        else:
            return 'RANGE'
