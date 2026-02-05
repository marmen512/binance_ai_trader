"""
train_ensemble.py — тренує три моделі (RandomForest, GradientBoosting, ExtraTrees)
на даних BTC 5m та зберігає їх у models/.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.model_selection import train_test_split
import joblib
import sys
import os

# Додаємо кореневу директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def train_ensemble():
    """Тренує ансамбль моделей на BTC 5m даних."""
    print("Завантаження даних з data/btcusdt_5m.csv...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Будуємо фічі
    print("Побудова фіч...")
    fb = FeatureBuilder()
    df = fb.build(df)

    # Будуємо таргет
    print("Побудова таргету...")
    df = build_target(df, horizon=5, threshold=0.004)

    # Вибираємо фічі для моделі
    features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    X = df[features]
    y = df['target']

    # Мапимо таргет до 0, 1, 2 для sklearn
    # -1 -> 0 (SELL), 0 -> 1 (HOLD), 1 -> 2 (BUY)
    y_mapped = y.map({-1: 0, 0: 1, 1: 2})

    # Розділяємо дані
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_mapped, test_size=0.2, random_state=42, shuffle=False
    )

    print(f"Розмір тренувальної вибірки: {len(X_train)}, тестової: {len(X_test)}")

    # Тренуємо RandomForest
    print("Тренування RandomForest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf.fit(X_train, y_train)
    rf_acc = rf.score(X_test, y_test)
    print(f"RandomForest accuracy: {rf_acc:.4f}")
    joblib.dump(rf, 'models/rf_btc_5m.pkl')

    # Тренуємо GradientBoosting
    print("Тренування GradientBoosting...")
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    gb.fit(X_train, y_train)
    gb_acc = gb.score(X_test, y_test)
    print(f"GradientBoosting accuracy: {gb_acc:.4f}")
    joblib.dump(gb, 'models/gb_btc_5m.pkl')

    # Тренуємо ExtraTrees
    print("Тренування ExtraTrees...")
    et = ExtraTreesClassifier(n_estimators=100, max_depth=10, random_state=42)
    et.fit(X_train, y_train)
    et_acc = et.score(X_test, y_test)
    print(f"ExtraTrees accuracy: {et_acc:.4f}")
    joblib.dump(et, 'models/et_btc_5m.pkl')

    print("\nМоделі збережено у models/")
    print("  - models/rf_btc_5m.pkl")
    print("  - models/gb_btc_5m.pkl")
    print("  - models/et_btc_5m.pkl")


if __name__ == '__main__':
    train_ensemble()
