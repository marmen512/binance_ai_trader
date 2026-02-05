"""
Plot equity curve from backtest.
"""
import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def plot_equity():
    """
    Run backtest and plot equity curve.
    """
    print("[PlotEquity] Running backtest...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[PlotEquity] Error: {data_path} not found")
        return
    
    df = pd.read_csv(data_path)
    
    # Create engine and run backtest
    engine = EnsembleEngine()
    backtester = AIBacktester(df, engine, initial_balance=10000)
    backtester.run()
    
    # Get equity curve
    equity_df = pd.DataFrame(backtester.equity_curve)
    
    if len(equity_df) == 0:
        print("[PlotEquity] No equity data to plot")
        return
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(equity_df['bar'], equity_df['equity'], label='Equity', linewidth=2)
    plt.axhline(y=10000, color='r', linestyle='--', label='Initial Balance')
    plt.xlabel('Bar')
    plt.ylabel('Equity ($)')
    plt.title('Backtest Equity Curve')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Save plot
    output_path = 'equity_curve.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"[PlotEquity] Saved equity curve to {output_path}")
    
    plt.close()


if __name__ == '__main__':
    plot_equity()
