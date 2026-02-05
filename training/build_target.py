"""
build_target — будує цільову змінну (target) на основі майбутньої прибутковості.

Створює колонку 'target' з класами:
  1  — BUY (очікується зростання > threshold)
  0  — HOLD (очікується невелика зміна)
  -1 — SELL (очікується падіння < -threshold)
"""

import pandas as pd


def build_target(df, horizon=5, threshold=0.004):
    """
    Будує цільову змінну на основі майбутньої прибутковості.

    Args:
        df (pd.DataFrame): DataFrame з колонкою 'close'
        horizon (int): Горизонт прогнозування (кількість періодів)
        threshold (float): Поріг для класифікації (наприклад, 0.004 = 0.4%)

    Returns:
        pd.DataFrame: DataFrame з колонками 'target' та 'future_return', без NaN
    """
    df = df.copy()

    # Обчислюємо майбутню прибутковість
    df['future_return'] = df['close'].pct_change(horizon).shift(-horizon)

    # Класифікуємо на основі порогу
    df['target'] = 0  # HOLD за замовчуванням
    df.loc[df['future_return'] > threshold, 'target'] = 1   # BUY
    df.loc[df['future_return'] < -threshold, 'target'] = -1  # SELL

    return df.dropna()
