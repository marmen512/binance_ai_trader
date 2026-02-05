"""
adaptive_retrain.py — адаптивне перенавчання моделі на останніх даних.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def adaptive_retrain():
    """Адаптивне перенавчання моделі на останніх 12000 рядках."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Беремо останні 12000 рядків
    df = df.tail(12000)
    print(f"Використовуємо останні {len(df)} рядків для перенавчання")

    # Будуємо фічі та таргет
    fb = FeatureBuilder()
    df = fb.build(df)
    df = build_target(df, horizon=5, threshold=0.004)

    features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    X = df[features]
    y = df['target'].map({-1: 0, 0: 1, 1: 2})

    print("Тренування адаптивної моделі...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X, y)

    # Зберігаємо модель
    joblib.dump(model, 'models/adaptive_latest.pkl')
    print("Модель збережено у models/adaptive_latest.pkl")


if __name__ == '__main__':
    adaptive_retrain()
