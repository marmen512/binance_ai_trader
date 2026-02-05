"""
test_signal.py — тестує EnsembleEngine на останніх даних.
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ensemble_engine import EnsembleEngine


def test_signal():
    """Тестує сигнал від EnsembleEngine."""
    print("Завантаження останніх даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Беремо останні 100 рядків для контексту
    recent_df = df.tail(100)

    print("Ініціалізація EnsembleEngine...")
    engine = EnsembleEngine()

    print("Генерація сигналу...")
    signal, confidence = engine.signal(recent_df)

    print(f"\nСигнал: {signal}")
    print(f"Впевненість: {confidence:.4f}")


if __name__ == '__main__':
    test_signal()
