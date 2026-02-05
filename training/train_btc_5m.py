"""
Скрипт тренування моделі для BTCUSDT 5m з використанням специфічних ознак.

Цей скрипт завантажує дані, будує ознаки, створює цільову змінну,
тренує модель та зберігає її для використання у DecisionEngine.
"""

import pandas as pd
import sys
import os

# Додаємо кореневу директорію до PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target
from training.train_model import train_model


def prepare_btc_5m_data(input_path, output_path):
    """
    Підготовляє дані BTCUSDT 5m: будує ознаки та цільову змінну.
    
    Параметри:
        input_path (str): шлях до сирих даних (CSV з OHLCV)
        output_path (str): шлях для збереження підготовлених даних
    """
    print("=" * 60)
    print("Підготовка даних BTCUSDT 5m")
    print("=" * 60)
    
    # Завантажуємо сирі дані
    print(f"\n1. Завантаження даних з {input_path}...")
    df = pd.read_csv(input_path)
    print(f"   Завантажено {len(df)} записів")
    
    # Будуємо ознаки за допомогою FeatureBuilder
    print("\n2. Побудова технічних ознак...")
    builder = FeatureBuilder()
    df = builder.build(df)
    print(f"   Після побудови ознак: {len(df)} записів")
    print(f"   Колонки: {list(df.columns)}")
    
    # Вибираємо специфічні ознаки для BTC 5m моделі
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    print(f"\n3. Використовуємо ознаки: {feature_cols}")
    
    # Створюємо цільову змінну
    print("\n4. Створення цільової змінної...")
    df = build_target(df, horizon=5, threshold=0.004)
    print(f"   Після створення target: {len(df)} записів")
    
    # Статистика розподілу класів
    target_counts = df['target'].value_counts().sort_index()
    print(f"\n   Розподіл класів:")
    print(f"   SELL (-1): {target_counts.get(-1, 0)} ({target_counts.get(-1, 0)/len(df)*100:.1f}%)")
    print(f"   HOLD (0):  {target_counts.get(0, 0)} ({target_counts.get(0, 0)/len(df)*100:.1f}%)")
    print(f"   BUY (1):   {target_counts.get(1, 0)} ({target_counts.get(1, 0)/len(df)*100:.1f}%)")
    
    # Зберігаємо підготовлені дані
    print(f"\n5. Збереження підготовлених даних у {output_path}...")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Зберігаємо всі колонки (OHLCV, ознаки, target)
    df.to_csv(output_path, index=False)
    print(f"   Збережено!")
    
    return df


if __name__ == '__main__':
    # Шляхи до файлів
    raw_data_path = 'data/btcusdt_5m.csv'
    prepared_data_path = 'data/btcusdt_5m_features.csv'
    model_path = 'models/btc_5m_model.pkl'
    
    print("\n" + "=" * 60)
    print("ТРЕНУВАННЯ МОДЕЛІ BTCUSDT 5m")
    print("=" * 60)
    
    # Етап 1: Підготовка даних
    if not os.path.exists(raw_data_path):
        print(f"\nПомилка: файл {raw_data_path} не знайдено!")
        print("Спочатку запустіть: python scripts/download_btc_5m.py")
        sys.exit(1)
    
    df = prepare_btc_5m_data(raw_data_path, prepared_data_path)
    
    # Етап 2: Тренування моделі
    print("\n" + "=" * 60)
    print("Тренування моделі RandomForest")
    print("=" * 60 + "\n")
    
    results = train_model(
        data_path=prepared_data_path,
        model_path=model_path,
        test_size=0.2,
        random_state=42
    )
    
    # Підсумок
    print("\n" + "=" * 60)
    print("ТРЕНУВАННЯ ЗАВЕРШЕНО")
    print("=" * 60)
    print(f"\nТочність на тренувальному наборі: {results['train_score']:.4f}")
    print(f"Точність на тестовому наборі:     {results['test_score']:.4f}")
    print(f"Кількість ознак:                  {results['n_features']}")
    print(f"\nМодель збережено: {model_path}")
    print(f"\nДля тестування запустіть: python scripts/test_signal.py")
