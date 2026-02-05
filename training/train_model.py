"""
train_model.py — загальний скрипт для тренування моделі.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def train_model():
    """Тренує модель та зберігає як signal_model.pkl."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Будуємо фічі
    fb = FeatureBuilder()
    df = fb.build(df)

    # Будуємо таргет
    df = build_target(df, horizon=5, threshold=0.004)

    # Вибираємо фічі
    features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    X = df[features]
    y = df['target'].map({-1: 0, 0: 1, 1: 2})

    # Розділяємо дані
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, shuffle=False
    )

    print(f"Тренування моделі...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    acc = model.score(X_test, y_test)
    print(f"Accuracy: {acc:.4f}")

    joblib.dump(model, 'models/signal_model.pkl')
    print("Модель збережено у models/signal_model.pkl")


if __name__ == '__main__':
    train_model()
