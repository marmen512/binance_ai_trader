"""
Metrics - обчислення метрик бектесту.

Функції для аналізу результатів трейдів.
"""


def compute_metrics(trades):
    """
    Обчислює метрики ефективності на основі списку трейдів.
    
    Args:
        trades: список словників з ключами 'pnl'
        
    Returns:
        dict: метрики (winrate, avg_win, avg_loss, expectancy)
    """
    if not trades:
        return {
            'total_trades': 0,
            'winrate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'expectancy': 0.0
        }
    
    # Підрахунок виграшів та програшів
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [t['pnl'] for t in trades if t['pnl'] < 0]
    
    total_trades = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    
    # Winrate
    winrate = win_count / total_trades if total_trades > 0 else 0.0
    
    # Середній виграш та програш
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    
    # Expectancy (математичне очікування)
    expectancy = (winrate * avg_win) + ((1 - winrate) * avg_loss)
    
    return {
        'total_trades': total_trades,
        'win_count': win_count,
        'loss_count': loss_count,
        'winrate': winrate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'expectancy': expectancy
    }
