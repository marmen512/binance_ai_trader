"""
Threshold Optimizer - оптимізація порогу ймовірності.
"""
import pandas as pd
from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Оптимізація порогу min_prob_override...")
    
    # Тестуємо різні пороги
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]
    results = []
    
    for threshold in thresholds:
        print(f"\nТестування порогу {threshold:.2f}...")
        
        engine = EnsembleEngine()
        engine.min_prob_override = threshold
        
        backtester = AIBacktester(engine, initial_balance=10000.0)
        final_balance, trades, equity = backtester.run(df, window_size=100)
        
        profit_pct = (final_balance / 10000.0 - 1) * 100
        
        results.append({
            'threshold': threshold,
            'final_balance': final_balance,
            'profit_pct': profit_pct,
            'trades': len(trades)
        })
        
        print(f"  Баланс: ${final_balance:.2f} ({profit_pct:+.2f}%)")
        print(f"  Трейдів: {len(trades)}")
    
    print(f"\n{'='*60}")
    print("Результати оптимізації:")
    for r in results:
        print(f"  Threshold {r['threshold']:.2f}: ${r['final_balance']:.2f} ({r['profit_pct']:+.2f}%), трейдів: {r['trades']}")
    
    # Найкращий поріг
    best = max(results, key=lambda x: x['final_balance'])
    print(f"\n🏆 Найкращий поріг: {best['threshold']:.2f}")
    print(f"   Баланс: ${best['final_balance']:.2f} ({best['profit_pct']:+.2f}%)")


if __name__ == '__main__':
    main()
