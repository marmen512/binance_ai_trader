"""
Метрики для аналізу результатів бектесту.
"""
import pandas as pd
import numpy as np


def compute_metrics(trades: list) -> dict:
    """
    Обчислює метрики ефективності стратегії.
    
    Args:
        trades: Список угод з ключами 'pnl', 'return'
        
    Returns:
        Словник з метриками
    """
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0
        }
    
    df_trades = pd.DataFrame(trades)
    
    total_trades = len(df_trades)
    winning_trades = df_trades[df_trades['pnl'] > 0]
    losing_trades = df_trades[df_trades['pnl'] <= 0]
    
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    avg_win = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0.0
    avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0.0
    
    # Математичне очікування (expectancy)
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy
    }
