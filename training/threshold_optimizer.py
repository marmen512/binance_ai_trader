"""
threshold_optimizer.py — оптимізує поріг впевненості для моделі.
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def threshold_optimizer():
    """Оптимізує поріг впевненості для моделі."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Діапазон порогів для тестування
    thresholds = [x / 100.0 for x in range(55, 74, 2)]  # 0.55 до 0.73 з кроком 0.02

    best_threshold = None
    best_balance = 0

    print("Оптимізація порогу впевненості...")
    print(f"Тестуємо пороги: {thresholds}")

    for threshold in thresholds:
        # Створюємо engine з поточним порогом
        engine = EnsembleEngine()
        engine.min_prob_override = threshold

        # Запускаємо бектест
        bt = AIBacktester(engine)
        results = bt.run(df)

        final_balance = results['final_balance']
        print(f"Поріг {threshold:.2f}: ${final_balance:.2f}")

        if final_balance > best_balance:
            best_balance = final_balance
            best_threshold = threshold

    print(f"\n{'='*50}")
    print(f"Найкращий поріг: {best_threshold:.2f}")
    print(f"Найкращий баланс: ${best_balance:.2f}")
    print(f"{'='*50}")


if __name__ == '__main__':
    threshold_optimizer()
