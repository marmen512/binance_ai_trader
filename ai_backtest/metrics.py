"""
Модуль для обчислення метрик бектесту.
"""
import pandas as pd
import numpy as np


def compute_metrics(trades: list) -> dict:
    """
    Обчислює метрики ефективності торгівлі.
    
    Args:
        trades: список угод з полями 'type', 'price', 'size'
        
    Returns:
        dict з метриками: num_trades, winrate, avg_win, avg_loss, expectancy
    """
    if len(trades) == 0:
        return {
            'num_trades': 0,
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0
        }
    
    # Групуємо угоди в пари (вхід-вихід)
    pairs = []
    for i in range(0, len(trades) - 1, 2):
        if i + 1 < len(trades):
            buy_trade = trades[i]
            sell_trade = trades[i + 1]
            
            if buy_trade['type'] == 'BUY' and sell_trade['type'] == 'SELL':
                # Обчислюємо прибуток/збиток
                entry_price = buy_trade['price']
                exit_price = sell_trade['price']
                pnl = (exit_price - entry_price) * buy_trade['size']
                pnl -= buy_trade['fee'] + sell_trade['fee']
                
                pairs.append({
                    'entry': entry_price,
                    'exit': exit_price,
                    'pnl': pnl
                })
    
    if len(pairs) == 0:
        return {
            'num_trades': len(trades),
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0
        }
    
    # Обчислюємо метрики
    pnls = [p['pnl'] for p in pairs]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    
    num_trades = len(pairs)
    winrate = len(wins) / num_trades if num_trades > 0 else 0.0
    avg_win = np.mean(wins) if len(wins) > 0 else 0.0
    avg_loss = np.mean(losses) if len(losses) > 0 else 0.0
    expectancy = np.mean(pnls) if len(pnls) > 0 else 0.0
    
    return {
        'num_trades': num_trades,
        'winrate': winrate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy
    }
