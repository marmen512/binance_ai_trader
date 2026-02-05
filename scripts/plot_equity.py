"""
Plot equity curve - візуалізація кривої капіталу.
"""
import matplotlib.pyplot as plt


def plot_equity(equity, title="Equity Curve"):
    """
    Малює криву капіталу.
    
    Args:
        equity: список значень капіталу
        title: заголовок графіка
    """
    plt.figure(figsize=(12, 6))
    plt.plot(equity, linewidth=2)
    plt.title(title, fontsize=16)
    plt.xlabel('Time Steps', fontsize=12)
    plt.ylabel('Equity ($)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('equity_curve.png', dpi=150)
    print("Графік збережено в equity_curve.png")
    plt.show()


if __name__ == '__main__':
    # Приклад використання
    import pandas as pd
    from core.ensemble_engine import EnsembleEngine
    from ai_backtest.engine import AIBacktester
    
    df = pd.read_csv('data/btcusdt_5m.csv')
    engine = EnsembleEngine()
    backtester = AIBacktester(engine)
    final_balance, trades, equity = backtester.run(df, window_size=100)
    
    plot_equity(equity, title="AI Backtest Equity Curve")
