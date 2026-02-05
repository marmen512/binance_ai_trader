"""
Скрипт запуску AI бектесту з використанням ансамблевого двигуна.
"""
import pandas as pd
import sys
import os

# Додаємо кореневу директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics
from training.train_ensemble import build_btc_features


if __name__ == '__main__':
    print("=== Запуск AI Бектесту ===\n")
    
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
    
    # Ініціалізація ансамблевого двигуна
    print("Завантаження ансамблевого двигуна...")
    try:
        engine = EnsembleEngine()
    except FileNotFoundError as e:
        print(f"Помилка: {e}")
        print("Запустіть спочатку: python training/train_ensemble.py")
        sys.exit(1)
    
    print()
    
    # Ініціалізація бектестера
    backtester = AIBacktester(
        engine=engine,
        initial_balance=10000,
        fee=0.0004,
        slippage=0.0002
    )
    
    # Запуск бектесту
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    results = backtester.run(df, feature_cols)
    
    # Виведення результатів
    print(f"\n=== Результати Бектесту ===")
    print(f"Початковий баланс: $10,000")
    print(f"Фінальний баланс: ${results['final_balance']:.2f}")
    print(f"Прибуток: ${results['final_balance'] - 10000:.2f}")
    print(f"ROI: {(results['final_balance'] / 10000 - 1) * 100:.2f}%")
    
    # Метрики угод
    metrics = compute_metrics(results['trades'])
    print(f"\n=== Метрики Угод ===")
    print(f"Всього угод: {metrics['total_trades']}")
    print(f"Win Rate: {metrics['win_rate'] * 100:.2f}%")
    print(f"Середній виграш: ${metrics['avg_win']:.2f}")
    print(f"Середній програш: ${metrics['avg_loss']:.2f}")
    print(f"Expectancy: ${metrics['expectancy']:.2f}")
    
    # Збереження результатів
    import json
    os.makedirs('results', exist_ok=True)
    
    with open('results/backtest_results.json', 'w') as f:
        json.dump({
            'final_balance': results['final_balance'],
            'metrics': metrics,
            'num_trades': len(results['trades'])
        }, f, indent=2)
    
    # Збереження equity curve
    equity_df = pd.DataFrame(results['equity_curve'])
    equity_df.to_csv('results/equity_curve.csv', index=False)
    
    print(f"\nРезультати збережено:")
    print("  - results/backtest_results.json")
    print("  - results/equity_curve.csv")
