"""
Скрипт для запуску AI бектесту торгової стратегії.

Завантажує дані, ініціалізує DecisionEngine та AIBacktester,
запускає симуляцію торгівлі та виводить метрики.
"""

import pandas as pd
import sys
import os

# Додаємо кореневу директорію до PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.decision_engine import DecisionEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics, print_metrics


def run_backtest(data_path='data/btcusdt_5m.csv', 
                 model_path='models/btc_5m_model.pkl',
                 initial_capital=10000,
                 window_size=100):
    """
    Запускає AI бектест на історичних даних.
    
    Параметри:
        data_path (str): шлях до CSV файлу з OHLCV даними
        model_path (str): шлях до навченої моделі
        initial_capital (float): початковий капітал у USDT
        window_size (int): розмір вікна для генерації сигналів
    """
    print("\n" + "=" * 60)
    print("AI БЕКТЕСТ ТОРГОВОЇ СТРАТЕГІЇ")
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
    
    # Ініціалізуємо AIBacktester
    print(f"\n3. Ініціалізація AIBacktester...")
    backtester = AIBacktester(
        decision_engine=engine,
        initial_capital=initial_capital,
        fee_rate=0.001,  # 0.1% комісія
        slippage=0.0005  # 0.05% проковзування
    )
    
    # Запускаємо бектест
    print(f"\n4. Запуск бектесту...")
    equity_curve, trades = backtester.run(
        df=df,
        window_size=window_size,
        use_risk_filter=True
    )
    
    # Обчислюємо метрики
    print(f"\n5. Обчислення метрик...")
    metrics = compute_metrics(trades)
    
    # Виводимо метрики
    print_metrics(metrics)
    
    # Зберігаємо результати
    print(f"\n6. Збереження результатів...")
    
    # Зберігаємо криву капіталу
    equity_path = 'data/equity_curve.csv'
    equity_curve.to_csv(equity_path, index=False)
    print(f"   Крива капіталу збережена: {equity_path}")
    
    # Зберігаємо угоди
    trades_path = 'data/trades.csv'
    trades_df = pd.DataFrame(trades)
    trades_df.to_csv(trades_path, index=False)
    print(f"   Угоди збережені: {trades_path}")
    
    print(f"\n" + "=" * 60)
    print("БЕКТЕСТ ЗАВЕРШЕНО")
    print("=" * 60)
    print(f"\nДля візуалізації запустіть: python scripts/plot_equity.py")
    
    return equity_curve, trades, metrics


if __name__ == '__main__':
    run_backtest()
