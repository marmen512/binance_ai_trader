"""
Побудова цільової змінної (target) для класифікації.

Обчислює майбутню прибутковість і створює мітки: 1 (BUY), -1 (SELL), 0 (HOLD)
"""
import pandas as pd


def build_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.004) -> pd.DataFrame:
    """
    Створює цільову змінну для класифікації на основі майбутньої прибутковості.
    
    Args:
        df: DataFrame з колонкою 'close'
        horizon: кількість періодів для прогнозу (default=5)
        threshold: поріг для класифікації (default=0.004 = 0.4%)
        
    Returns:
        DataFrame з доданою колонкою 'target':
            1 - якщо майбутня прибутковість > threshold (BUY)
            -1 - якщо майбутня прибутковість < -threshold (SELL)
            0 - інакше (HOLD)
    """
    df = df.copy()
    
    # Обчислюємо майбутню прибутковість
    future_close = df['close'].shift(-horizon)
    future_return = (future_close - df['close']) / df['close']
    
    # Створюємо мітки
    df['target'] = 0
    df.loc[future_return > threshold, 'target'] = 1
    df.loc[future_return < -threshold, 'target'] = -1
    
    # Видаляємо NaN
    return df.dropna()
