"""
Запуск AI бектесту з EnsembleEngine.
"""
import pandas as pd
from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Ініціалізація EnsembleEngine...")
    engine = EnsembleEngine()
    
    print("Запуск бектесту...")
    backtester = AIBacktester(engine, initial_balance=10000.0)
    final_balance, trades, equity = backtester.run(df, window_size=100)
    
    print(f"\n{'='*50}")
    print(f"Початковий баланс: $10,000.00")
    print(f"Фінальний баланс: ${final_balance:.2f}")
    print(f"Прибуток/збиток: ${final_balance - 10000:.2f} ({(final_balance/10000 - 1)*100:.2f}%)")
    print(f"{'='*50}\n")
    
    metrics = compute_metrics(trades)
    print("Метрики:")
    print(f"  Всього трейдів: {metrics['total_trades']}")
    print(f"  Виграшних: {metrics['win_count']}")
    print(f"  Програшних: {metrics['loss_count']}")
    print(f"  Winrate: {metrics['winrate']*100:.2f}%")
    print(f"  Середній виграш: ${metrics['avg_win']:.2f}")
    print(f"  Середній програш: ${metrics['avg_loss']:.2f}")
    print(f"  Expectancy: ${metrics['expectancy']:.2f}")


if __name__ == '__main__':
    main()
