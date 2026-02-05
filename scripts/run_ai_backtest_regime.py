"""
run_ai_backtest_regime.py — запускає бектест з RegimeModelEngine.
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.regime_model_engine import RegimeModelEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


def run_ai_backtest_regime():
    """Запускає AI бектест з RegimeModelEngine."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    print("Ініціалізація RegimeModelEngine...")
    engine = RegimeModelEngine()

    print("Ініціалізація AIBacktester...")
    bt = AIBacktester(engine, initial_balance=10000)

    print("Запуск бектесту з режимними моделями...")
    results = bt.run(df)

    print(f"\n{'='*50}")
    print(f"Фінальний баланс: ${results['final_balance']:.2f}")
    print(f"Початковий баланс: $10000.00")
    print(f"Прибуток/Збиток: ${results['final_balance'] - 10000:.2f}")
    print(f"Прибуток %: {((results['final_balance'] / 10000) - 1) * 100:.2f}%")
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
    run_ai_backtest_regime()
