"""
Backtest metrics calculation.
"""
import pandas as pd
import numpy as np


def calculate_metrics(trades, equity_curve, initial_balance):
    """
    Calculate comprehensive backtest metrics.
    
    Args:
        trades: List of trade dictionaries
        equity_curve: List of equity snapshots
        initial_balance: Starting balance
        
    Returns:
        Dictionary of metrics
    """
    if len(trades) == 0:
        return {
            'total_trades': 0,
            'total_return': 0,
            'total_return_pct': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Basic metrics
    wins = trades_df[trades_df['pnl'] > 0]
    losses = trades_df[trades_df['pnl'] <= 0]
    
    total_pnl = trades_df['pnl'].sum()
    total_return_pct = (total_pnl / initial_balance) * 100
    
    win_rate = len(wins) / len(trades) if len(trades) > 0 else 0
    
    profit_factor = 0
    if len(losses) > 0 and losses['pnl'].sum() != 0:
        profit_factor = abs(wins['pnl'].sum() / losses['pnl'].sum())
    
    # Sharpe ratio (simplified)
    if len(trades) > 1:
        returns = trades_df['return_pct'].values
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
    else:
        sharpe_ratio = 0
    
    # Max drawdown
    max_drawdown = 0
    if len(equity_curve) > 0:
        equity_df = pd.DataFrame(equity_curve)
        equity = equity_df['equity'].values
        
        peak = equity[0]
        for value in equity:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    
    return {
        'total_trades': len(trades),
        'winning_trades': len(wins),
        'losing_trades': len(losses),
        'total_return': total_pnl,
        'total_return_pct': total_return_pct,
        'win_rate': win_rate,
        'avg_win': wins['pnl'].mean() if len(wins) > 0 else 0,
        'avg_loss': losses['pnl'].mean() if len(losses) > 0 else 0,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown * 100
    }


def print_metrics(metrics):
    """
    Print metrics in a readable format.
    """
    print("\n=== Backtest Metrics ===")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Winning Trades: {metrics['winning_trades']}")
    print(f"Losing Trades: {metrics['losing_trades']}")
    print(f"Win Rate: {metrics['win_rate']*100:.2f}%")
    print(f"Total Return: ${metrics['total_return']:.2f} ({metrics['total_return_pct']:+.2f}%)")
    print(f"Avg Win: ${metrics['avg_win']:.2f}")
    print(f"Avg Loss: ${metrics['avg_loss']:.2f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
