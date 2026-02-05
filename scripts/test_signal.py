"""
Тест генерації сигналів з EnsembleEngine.
"""
import pandas as pd
from core.ensemble_engine import EnsembleEngine


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Ініціалізація EnsembleEngine...")
    engine = EnsembleEngine()
    
    print("Генерація сигналу...")
    signal, confidence = engine.signal(df)
    
    print(f"\nСигнал: {signal}")
    print(f"Впевненість: {confidence:.4f}")


if __name__ == '__main__':
    main()
