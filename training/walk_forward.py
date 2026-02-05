"""
walk_forward.py — walk-forward валідація з ковзним вікном.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target
from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def walk_forward():
    """Walk-forward валідація з ковзним вікном."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Будуємо фічі та таргет
    fb = FeatureBuilder()
    df = fb.build(df)
    df = build_target(df, horizon=5, threshold=0.004)

    features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']

    # Параметри walk-forward
    chunk = 4000  # Розмір тренувального вікна
    test = 1000   # Розмір тестового вікна

    results = []
    start = 0

    print("Запуск walk-forward валідації...")

    while start + chunk + test <= len(df):
        print(f"\nВікно: {start} - {start + chunk + test}")

        # Тренувальна та тестова вибірки
        train_df = df.iloc[start:start + chunk]
        test_df = df.iloc[start + chunk:start + chunk + test]

        X_train = train_df[features]
        y_train = train_df['target'].map({-1: 0, 0: 1, 1: 2})

        # Тренуємо модель
        print("Тренування моделі...")
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X_train, y_train)

        # Зберігаємо тимчасову модель
        joblib.dump(model, 'models/tmp_wf.pkl')

        # Підміняємо модель в EnsembleEngine
        engine = EnsembleEngine()
        engine.models[0] = joblib.load('models/tmp_wf.pkl')

        # Запускаємо бектест на тестових даних
        bt = AIBacktester(engine)
        
        # Відновлюємо OHLCV колонки для бектесту
        test_ohlcv = df[['open', 'high', 'low', 'close', 'volume']].iloc[start + chunk:start + chunk + test]
        bt_results = bt.run(test_ohlcv)

        final_balance = bt_results['final_balance']
        results.append(final_balance)

        print(f"Фінальний баланс на вікні: ${final_balance:.2f}")

        start += test

    print(f"\n{'='*50}")
    print(f"Walk-forward валідація завершена")
    print(f"Середній фінальний баланс: ${sum(results)/len(results):.2f}")
    print(f"Кількість вікон: {len(results)}")
    print(f"{'='*50}")


if __name__ == '__main__':
    walk_forward()
