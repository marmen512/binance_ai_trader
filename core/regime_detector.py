"""
RegimeDetector - визначення режиму ринку.
"""
import pandas as pd


class RegimeDetector:
    """
    Визначає поточний режим ринку: VOLATILE, TREND або RANGE.
    """
    
    def detect(self, df: pd.DataFrame) -> str:
        """
        Визначає режим ринку на основі волатильності та тренду.
        
        Args:
            df: DataFrame з колонкою 'close'
            
        Returns:
            str: 'VOLATILE', 'TREND' або 'RANGE'
        """
        # Обчислюємо прибутковість
        returns = df['close'].pct_change()
        
        # Волатильність (останнє значення rolling std)
        vol = returns.rolling(window=20).std().iloc[-1]
        
        # Тренд (різниця EMA)
        ema20 = df['close'].ewm(span=20, adjust=False).mean()
        ema50 = df['close'].ewm(span=50, adjust=False).mean()
        trend = abs((ema20.iloc[-1] - ema50.iloc[-1]) / df['close'].iloc[-1])
        
        # Визначаємо режим
        if vol > 0.02:
            return 'VOLATILE'
        elif trend > 0.004:
            return 'TREND'
        else:
            return 'RANGE'
