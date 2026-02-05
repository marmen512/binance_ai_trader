"""
metrics.py — обчислює метрики ефективності трейдингу.
"""


def compute_metrics(trades):
    """
    Обчислює метрики ефективності на основі списку трейдів.

    Args:
        trades (list): Список трейдів з полем 'pnl'

    Returns:
        dict: Словник з метриками (winrate, avg_win, avg_loss, expectancy)
    """
    if not trades:
        return {
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0,
            'total_trades': 0
        }

    # Розділяємо на прибуткові та збиткові трейди
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['pnl'] <= 0]

    # Winrate — відсоток прибуткових трейдів
    winrate = len(wins) / len(trades) if trades else 0.0

    # Середній прибуток та збиток
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0

    # Expectancy — математичне очікування прибутку на трейд
    expectancy = (winrate * avg_win) + ((1 - winrate) * avg_loss)

    return {
        'winrate': winrate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy,
        'total_trades': len(trades)
    }
