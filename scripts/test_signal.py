"""
Скрипт для тестування генерації сигналів.

Завантажує дані, створює DecisionEngine та генерує сигнал.
"""
import sys
import os
import pandas as pd

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.decision_engine import DecisionEngine


def main():
    csv_path = 'data/btcusdt_5m.csv'
    
    print(f"Завантаження даних з {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print(f"Завантажено {len(df)} рядків даних")
    print(f"Останнє значення close: {df['close'].iloc[-1]}")
    
    # Створюємо DecisionEngine
    print("\nІніціалізація DecisionEngine...")
    engine = DecisionEngine(model_path='models/btc_5m_model.pkl')
    
    # Генеруємо сигнал
    print("Генерація сигналу...")
    signal, confidence = engine.signal(df)
    
    # Виводимо результат
    print("\n" + "="*50)
    print(f"Сигнал: {signal}")
    print(f"Впевненість: {confidence:.4f} ({confidence*100:.2f}%)")
    print("="*50)
    
    # Інтерпретація
    if signal == "BUY":
        print("✓ Модель рекомендує КУПИТИ")
    elif signal == "SELL":
        print("✗ Модель рекомендує ПРОДАТИ")
    else:
        print("○ Модель рекомендує УТРИМАТИСЯ")


if __name__ == '__main__':
    main()
