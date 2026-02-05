"""
Скрипт для тестування генерації торгових сигналів.

Завантажує історичні дані, ініціалізує DecisionEngine
та генерує тестові сигнали на останніх свічках.
"""

import pandas as pd
import sys
import os

# Додаємо кореневу директорію до PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.decision_engine import DecisionEngine
from core.risk_filter import risk_filter


def test_signal(data_path='data/btcusdt_5m.csv', model_path='models/btc_5m_model.pkl'):
    """
    Тестує генерацію сигналів на історичних даних.
    
    Параметри:
        data_path (str): шлях до CSV файлу з OHLCV даними
        model_path (str): шлях до навченої моделі
    """
    print("=" * 60)
    print("ТЕСТ ГЕНЕРАЦІЇ ТОРГОВИХ СИГНАЛІВ")
    print("=" * 60)
    
    # Перевіряємо наявність файлів
    if not os.path.exists(data_path):
        print(f"\nПомилка: файл {data_path} не знайдено!")
        print("Спочатку завантажте дані: python scripts/download_btc_5m.py")
        return
    
    if not os.path.exists(model_path):
        print(f"\nПомилка: модель {model_path} не знайдена!")
        print("Спочатку натренуйте модель: python training/train_btc_5m.py")
        return
    
    # Завантажуємо дані
    print(f"\n1. Завантаження даних з {data_path}...")
    df = pd.read_csv(data_path)
    print(f"   Завантажено {len(df)} свічок")
    print(f"   Період: {df['timestamp'].iloc[0]} - {df['timestamp'].iloc[-1]}")
    
    # Ініціалізуємо DecisionEngine
    print(f"\n2. Ініціалізація DecisionEngine...")
    engine = DecisionEngine(model_path=model_path)
    
    # Виводимо інфо про модель
    model_info = engine.get_model_info()
    print(f"   Тип моделі: {model_info['model_type']}")
    print(f"   Кількість ознак: {model_info['n_features']}")
    print(f"   Ознаки: {', '.join(model_info['feature_cols'])}")
    
    # Генерація сигналу на останніх даних
    print(f"\n3. Генерація сигналу на останніх {len(df)} свічках...")
    signal, prob = engine.signal(df)
    
    print(f"\n{'=' * 60}")
    print(f"РЕЗУЛЬТАТ")
    print(f"{'=' * 60}")
    print(f"Сигнал:      {signal}")
    print(f"Ймовірність: {prob:.4f} ({prob*100:.2f}%)")
    
    # Застосовуємо ризик-фільтр
    print(f"\n4. Застосування ризик-фільтру...")
    
    # Обчислюємо поточну волатильність (останні 10 свічок)
    recent_returns = df['close'].pct_change().tail(10)
    current_volatility = recent_returns.std()
    
    print(f"   Поточна волатильність: {current_volatility:.4f} ({current_volatility*100:.2f}%)")
    
    # Фільтруємо сигнал
    filtered_signal = risk_filter(
        signal=signal,
        prob=prob,
        volatility=current_volatility,
        min_prob=0.6,
        max_volatility=0.03
    )
    
    if filtered_signal != signal:
        print(f"\n   ⚠️  Сигнал змінено: {signal} -> {filtered_signal}")
    else:
        print(f"\n   ✓  Сигнал пройшов фільтр: {filtered_signal}")
    
    print(f"\n{'=' * 60}")
    print(f"ФІНАЛЬНИЙ СИГНАЛ: {filtered_signal}")
    print(f"{'=' * 60}")
    
    # Додаткова інформація про останню свічку
    print(f"\nІнформація про останню свічку:")
    last_candle = df.iloc[-1]
    print(f"  Timestamp: {last_candle['timestamp']}")
    print(f"  Open:      {last_candle['open']:.2f}")
    print(f"  High:      {last_candle['high']:.2f}")
    print(f"  Low:       {last_candle['low']:.2f}")
    print(f"  Close:     {last_candle['close']:.2f}")
    print(f"  Volume:    {last_candle['volume']:.2f}")
    

if __name__ == '__main__':
    test_signal()
