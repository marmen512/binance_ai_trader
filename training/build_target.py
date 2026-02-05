"""
Модуль для побудови цільової змінної для класифікації.
"""
import pandas as pd


def build_target(df: pd.DataFrame, horizon: int = 5, threshold: float = 0.004) -> pd.DataFrame:
    """
    Будує мульти-класову цільову змінну на основі майбутньої зміни ціни.
    
    Класи:
    - -1: ціна впаде більше ніж на threshold
    - 0: ціна залишиться в межах [-threshold, threshold]
    - 1: ціна зросте більше ніж на threshold
    
    Args:
        df: DataFrame зі стовпцем 'close'
        horizon: горизонт прогнозування (кількість періодів вперед)
        threshold: поріг для класифікації руху ціни (0.004 = 0.4%)
        
    Returns:
        DataFrame з доданою колонкою 'target'
    """
    df = df.copy()
    
    # Обчислюємо майбутню зміну ціни
    future_return = df['close'].shift(-horizon) / df['close'] - 1
    
    # Класифікуємо
    df['target'] = 0
    df.loc[future_return > threshold, 'target'] = 1
    df.loc[future_return < -threshold, 'target'] = -1
    
    # Видаляємо рядки без target (останні horizon рядків)
    df = df[:-horizon]
    
    return df
