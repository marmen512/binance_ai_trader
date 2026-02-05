"""
run_meta_backtest.py — запускає бектест з MetaEngine.
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.build_meta import build_meta
from ai_backtest.meta_backtest import MetaBacktester
from ai_backtest.metrics import compute_metrics


def run_meta_backtest():
    """Запускає мета-бектест з комбінацією движків."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    print("Ініціалізація MetaEngine...")
    meta_engine = build_meta()

    print("Ініціалізація MetaBacktester...")
    bt = MetaBacktester(meta_engine, initial_balance=10000)

    print("Запуск мета-бектесту...")
    results = bt.run(df)

    print(f"\n{'='*50}")
    print(f"Фінальний баланс: ${results['balance']:.2f}")
    print(f"Початковий баланс: $10000.00")
    print(f"Прибуток/Збиток: ${results['balance'] - 10000:.2f}")
    print(f"Прибуток %: {((results['balance'] / 10000) - 1) * 100:.2f}%")
    print(f"{'='*50}")

    print(f"\nКількість трейдів: {len(results['trades'])}")

    if results['trades']:
        metrics = compute_metrics(results['trades'])
        print(f"\nМетрики:")
        print(f"  Winrate: {metrics['winrate']*100:.2f}%")
        print(f"  Середній прибуток: ${metrics['avg_win']:.2f}")
        print(f"  Середній збиток: ${metrics['avg_loss']:.2f}")
        print(f"  Expectancy: ${metrics['expectancy']:.2f}")


if __name__ == '__main__':
    run_meta_backtest()
