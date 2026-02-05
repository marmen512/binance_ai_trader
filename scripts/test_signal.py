"""
Скрипт тестування сигналів від ансамблевого двигуна.
"""
import pandas as pd
import sys
import os

# Додаємо кореневу директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ensemble_engine import EnsembleEngine
from training.train_ensemble import build_btc_features


if __name__ == '__main__':
    print("=== Тестування Сигналів ===\n")
    
    # Завантаження даних
    data_path = 'data/btcusdt_5m.csv'
    if not os.path.exists(data_path):
        print(f"Помилка: файл {data_path} не знайдено!")
        print("Запустіть спочатку: python scripts/download_btc_5m.py")
        sys.exit(1)
    
    df = pd.read_csv(data_path)
    print(f"Завантажено {len(df)} записів")
    
    # Побудова ознак
    df = build_btc_features(df)
    print(f"Після побудови ознак: {len(df)} записів\n")
    
    # Ініціалізація двигуна
    print("Завантаження ансамблевого двигуна...")
    try:
        engine = EnsembleEngine()
    except FileNotFoundError as e:
        print(f"Помилка: {e}")
        print("Запустіть спочатку: python training/train_ensemble.py")
        sys.exit(1)
    
    print()
    
    # Тестування на останніх 10 свічках
    print("Останні 10 сигналів:")
    print("-" * 80)
    
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    
    for i in range(len(df) - 10, len(df)):
        row = df.iloc[i]
        features = {col: row[col] for col in feature_cols}
        
        signal, confidence = engine.signal(features)
        
        timestamp = row.get('timestamp', f'Row {i}')
        price = row['close']
        
        print(f"{timestamp} | Price: ${price:.2f} | Signal: {signal:4s} | Confidence: {confidence:.3f}")
    
    print("-" * 80)
    print("\nТестування завершено!")
