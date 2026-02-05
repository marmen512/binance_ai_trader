"""
Модуль побудови цільової змінної (target) для класифікації.
Створює мультикласову ціль: -1 (продаж), 0 (утримання), 1 (купівля).
"""
import pandas as pd
import numpy as np


def build_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.004) -> pd.DataFrame:
    """
    Будує мультикласову цільову змінну на основі майбутньої прибутковості.
    
    Args:
        df: DataFrame з колонкою 'close'
        horizon: Горизонт прогнозу (кількість періодів вперед)
        threshold: Поріг для класифікації (напр., 0.004 = 0.4%)
        
    Returns:
        DataFrame з колонкою 'target': -1 (SELL), 0 (HOLD), 1 (BUY)
    """
    df = df.copy()
    
    # Обчислюємо майбутню прибутковість
    df['future_return'] = df['close'].shift(-horizon) / df['close'] - 1
    
    # Створюємо мультикласову ціль
    df['target'] = 0  # HOLD за замовчуванням
    df.loc[df['future_return'] > threshold, 'target'] = 1   # BUY
    df.loc[df['future_return'] < -threshold, 'target'] = -1  # SELL
    
    # Видаляємо колонку future_return (не потрібна для тренування)
    df = df.drop(columns=['future_return'])
    
    return df.dropna()
