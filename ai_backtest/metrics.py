"""
Модуль обчислення метрик торгової стратегії.

Розраховує статистичні показники ефективності торгівлі
на основі списку виконаних угод.
"""

import numpy as np


def compute_metrics(trades):
    """
    Обчислює метрики ефективності торгової стратегії.
    
    Розраховує:
    - Winrate: відсоток прибуткових угод
    - Average win: середній прибуток на прибуткову угоду
    - Average loss: середній збиток на збиткову угоду
    - Expectancy: математичне очікування прибутку на угоду
    - Profit factor: відношення загального прибутку до загального збитку
    
    Параметри:
        trades (list): список словників з інформацією про угоди.
                      Кожна угода повинна мати поле 'pnl_pct' (якщо це вихід з позиції)
                      
    Повертає:
        dict: словник з метриками стратегії
    """
    if not trades:
        return {
            'total_trades': 0,
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0,
            'profit_factor': 0.0
        }
    
    # Фільтруємо тільки угоди з PnL (виходи з позицій)
    pnl_trades = [t for t in trades if 'pnl_pct' in t]
    
    if not pnl_trades:
        return {
            'total_trades': len(trades),
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0,
            'profit_factor': 0.0
        }
    
    # Розділяємо на прибуткові та збиткові
    pnls = [t['pnl_pct'] for t in pnl_trades]
    wins = [pnl for pnl in pnls if pnl > 0]
    losses = [pnl for pnl in pnls if pnl < 0]
    
    # Кількість угод
    n_trades = len(pnl_trades)
    n_wins = len(wins)
    n_losses = len(losses)
    
    # Winrate (відсоток прибуткових угод)
    winrate = n_wins / n_trades if n_trades > 0 else 0.0
    
    # Середній прибуток та збиток
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    
    # Математичне очікування (expectancy)
    # E = (Winrate × AvgWin) + ((1 - Winrate) × AvgLoss)
    expectancy = (winrate * avg_win) + ((1 - winrate) * avg_loss)
    
    # Profit Factor (відношення загального прибутку до загального збитку)
    total_wins = sum(wins) if wins else 0.0
    total_losses = abs(sum(losses)) if losses else 0.0
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0.0
    
    # Максимальна просадка (maximum drawdown)
    equity_curve = []
    running_capital = 1.0  # Нормалізований капітал
    for pnl in pnls:
        running_capital *= (1 + pnl)
        equity_curve.append(running_capital)
    
    if equity_curve:
        peak = equity_curve[0]
        max_dd = 0.0
        for equity in equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            if dd > max_dd:
                max_dd = dd
    else:
        max_dd = 0.0
    
    return {
        'total_trades': n_trades,
        'winning_trades': n_wins,
        'losing_trades': n_losses,
        'winrate': winrate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'profit_factor': profit_factor,
        'max_drawdown': max_dd,
        'total_profit': sum(pnls)
    }


def print_metrics(metrics):
    """
    Виводить метрики у читабельному форматі.
    
    Параметри:
        metrics (dict): словник з метриками від compute_metrics
    """
    print("\n" + "=" * 60)
    print("МЕТРИКИ СТРАТЕГІЇ")
    print("=" * 60)
    
    print(f"\nЗагальна статистика:")
    print(f"  Всього угод:      {metrics['total_trades']}")
    print(f"  Прибуткових угод: {metrics['winning_trades']}")
    print(f"  Збиткових угод:   {metrics['losing_trades']}")
    
    print(f"\nВинагороди:")
    print(f"  Winrate:          {metrics['winrate']*100:.2f}%")
    print(f"  Середній прибуток: {metrics['avg_win']*100:.2f}%")
    print(f"  Середній збиток:   {metrics['avg_loss']*100:.2f}%")
    
    print(f"\nПоказники ефективності:")
    print(f"  Expectancy:       {metrics['expectancy']*100:.2f}%")
    print(f"  Profit Factor:    {metrics['profit_factor']:.2f}")
    print(f"  Max Drawdown:     {metrics['max_drawdown']*100:.2f}%")
    print(f"  Загальний прибуток: {metrics['total_profit']*100:.2f}%")
    
    print("=" * 60)
