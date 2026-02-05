"""
Запуск мета-бектесту.
"""
import pandas as pd
from core.build_meta import build_meta_engine
from ai_backtest.meta_backtest import MetaBacktester
from ai_backtest.metrics import compute_metrics


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("\nПобудова MetaEngine...")
    meta_engine = build_meta_engine()
    
    print("\nЗапуск мета-бектесту...")
    backtester = MetaBacktester(meta_engine, initial_balance=10000.0)
    final_balance, trades, equity = backtester.run(df, window_size=100)
    
    print(f"\n{'='*60}")
    print("РЕЗУЛЬТАТИ МЕТА-БЕКТЕСТУ")
    print(f"{'='*60}")
    print(f"Початковий баланс: $10,000.00")
    print(f"Фінальний баланс: ${final_balance:.2f}")
    print(f"Прибуток/збиток: ${final_balance - 10000:.2f} ({(final_balance/10000 - 1)*100:.2f}%)")
    print(f"{'='*60}\n")
    
    metrics = compute_metrics(trades)
    print("Метрики:")
    print(f"  Всього трейдів: {metrics['total_trades']}")
    print(f"  Виграшних: {metrics['win_count']}")
    print(f"  Програшних: {metrics['loss_count']}")
    print(f"  Winrate: {metrics['winrate']*100:.2f}%")
    print(f"  Середній виграш: ${metrics['avg_win']:.2f}")
    print(f"  Середній програш: ${metrics['avg_loss']:.2f}")
    print(f"  Expectancy: ${metrics['expectancy']:.2f}")
    
    print(f"\n{'='*60}")
    print("Ваги двигунів:")
    weights = meta_engine.tracker.get_weights()
    for name, weight in weights.items():
        score = meta_engine.tracker.scores[name]
        trades_count = meta_engine.tracker.trade_counts[name]
        wins = meta_engine.tracker.win_counts[name]
        print(f"  {name}: {weight*100:.2f}% (скор: {score:.2f}, трейдів: {trades_count}, виграшів: {wins})")


if __name__ == '__main__':
    main()
