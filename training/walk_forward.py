"""
Walk-Forward Testing - тестування з ковзаючим вікном.
"""
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from core.feature_builder import FeatureBuilder
from training.build_target import build_target
from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    # Параметри walk-forward
    train_size = 8000
    test_size = 2000
    step = 2000
    
    FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    
    print("Початок Walk-Forward тестування...")
    results = []
    
    start = 0
    window_num = 0
    
    while start + train_size + test_size <= len(df):
        window_num += 1
        train_end = start + train_size
        test_end = train_end + test_size
        
        print(f"\n{'='*60}")
        print(f"Вікно {window_num}: train [{start}:{train_end}], test [{train_end}:{test_end}]")
        
        # Тренувальні дані
        train_df = df.iloc[start:train_end].copy()
        fb = FeatureBuilder()
        train_df = fb.build(train_df)
        train_df = build_target(train_df, horizon=5, threshold=0.004)
        
        X_train = train_df[FEATURES]
        y_train = train_df['target']
        
        # Тренування моделі
        print("Тренування моделі для цього вікна...")
        model = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42)
        model.fit(X_train, y_train)
        
        # Зберігаємо тимчасову модель
        with open('models/tmp_wf.pkl', 'wb') as f:
            pickle.dump(model, f)
        
        # Тестові дані
        test_df = df.iloc[start:test_end].copy()
        
        # Підміняємо модель в ансамблі
        engine = EnsembleEngine()
        with open('models/tmp_wf.pkl', 'rb') as f:
            engine.models[0] = pickle.load(f)
        
        # Запускаємо бектест на тестовому вікні
        backtester = AIBacktester(engine, initial_balance=10000.0)
        final_balance, trades, equity = backtester.run(test_df, window_size=100)
        
        profit_pct = (final_balance / 10000.0 - 1) * 100
        print(f"Фінальний баланс: ${final_balance:.2f} ({profit_pct:+.2f}%)")
        print(f"Трейдів: {len(trades)}")
        
        results.append({
            'window': window_num,
            'final_balance': final_balance,
            'profit_pct': profit_pct,
            'trades': len(trades)
        })
        
        start += step
    
    print(f"\n{'='*60}")
    print("Результати Walk-Forward:")
    for r in results:
        print(f"  Вікно {r['window']}: ${r['final_balance']:.2f} ({r['profit_pct']:+.2f}%), трейдів: {r['trades']}")
    
    avg_profit = sum(r['profit_pct'] for r in results) / len(results)
    print(f"\nСередній прибуток: {avg_profit:+.2f}%")


if __name__ == '__main__':
    main()
