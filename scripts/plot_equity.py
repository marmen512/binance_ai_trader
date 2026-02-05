"""
plot_equity.py — малює графік equity curve.
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def plot_equity():
    """Малює equity curve бектесту."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    print("Запуск бектесту...")
    engine = EnsembleEngine()
    bt = AIBacktester(engine)
    results = bt.run(df)

    print("Побудова графіку...")
    plt.figure(figsize=(12, 6))
    plt.plot(results['equity_curve'])
    plt.title('Equity Curve')
    plt.xlabel('Time')
    plt.ylabel('Balance ($)')
    plt.grid(True)
    plt.tight_layout()
    
    output_path = 'equity_curve.png'
    plt.savefig(output_path)
    print(f"Графік збережено у {output_path}")
    plt.show()


if __name__ == '__main__':
    plot_equity()
