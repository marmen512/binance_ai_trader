"""
AI Backtest Metrics
Calculate performance metrics for backtest results
"""
import numpy as np
import pandas as pd


def compute_metrics(trades, equity_curve, initial_balance):
    """
    Compute performance metrics from backtest results
    
    Args:
        trades: List of trade dicts
        equity_curve: List of equity curve dicts
        initial_balance: Starting balance
        
    Returns:
        Dict with performance metrics
    """
    if not trades or not equity_curve:
        return {
            'total_return': 0,
            'num_trades': 0,
            'win_rate': 0,
            'avg_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
    
    # Convert to DataFrames
    trades_df = pd.DataFrame(trades)
    equity_df = pd.DataFrame(equity_curve)
    
    # Total return
    final_equity = equity_df['equity'].iloc[-1]
    total_return = (final_equity / initial_balance - 1) * 100
    
    # Number of trades
    num_trades = len(trades_df)
    
    # Win rate (need paired buy/sell trades)
    buy_trades = trades_df[trades_df['type'] == 'BUY']
    sell_trades = trades_df[trades_df['type'] == 'SELL']
    
    wins = 0
    losses = 0
    returns = []
    
    for i in range(min(len(buy_trades), len(sell_trades))):
        buy_price = buy_trades.iloc[i]['price']
        sell_price = sell_trades.iloc[i]['price']
        trade_return = (sell_price / buy_price - 1) * 100
        returns.append(trade_return)
        
        if trade_return > 0:
            wins += 1
        else:
            losses += 1
    
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    avg_return = np.mean(returns) if returns else 0
    
    # Max drawdown
    equity_series = equity_df['equity']
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Sharpe ratio (assuming daily data, annualized)
    equity_returns = equity_series.pct_change().dropna()
    if len(equity_returns) > 0 and equity_returns.std() > 0:
        sharpe_ratio = equity_returns.mean() / equity_returns.std() * np.sqrt(252)
    else:
        sharpe_ratio = 0
    
    return {
        'total_return': total_return,
        'num_trades': num_trades,
        'win_rate': win_rate,
        'avg_return': avg_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio
    }
