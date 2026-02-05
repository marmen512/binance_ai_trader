"""
train_regime_models.py — тренує окремі моделі для кожного ринкового режиму.
"""

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target
from core.regime_detector import RegimeDetector


def train_regime_models():
    """Тренує окремі моделі для кожного режиму."""
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')

    # Будуємо фічі та таргет
    fb = FeatureBuilder()
    df_full = fb.build(df)
    df_full = build_target(df_full, horizon=5, threshold=0.004)

    # Визначаємо режим для кожного рядка
    rd = RegimeDetector()
    regimes = []

    print("Визначення режимів для кожного рядка...")
    for i in range(len(df_full)):
        window_start = max(0, i - 100)
        window = df[['open', 'high', 'low', 'close', 'volume']].iloc[window_start:i+1]
        regime = rd.detect(window) if len(window) >= 50 else 'RANGE'
        regimes.append(regime)

    df_full['regime'] = regimes

    features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']

    # Тренуємо модель для кожного режиму
    for regime in ['TREND', 'RANGE', 'VOLATILE']:
        print(f"\nТренування моделі для режиму {regime}...")
        
        regime_df = df_full[df_full['regime'] == regime]
        
        if len(regime_df) < 100:
            print(f"Недостатньо даних для режиму {regime} ({len(regime_df)} рядків)")
            continue

        X = regime_df[features]
        y = regime_df['target'].map({-1: 0, 0: 1, 1: 2})

        # Тренуємо RandomForest
        model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
        model.fit(X, y)

        # Зберігаємо модель
        model_path = f'models/model_{regime}.pkl'
        joblib.dump(model, model_path)
        print(f"Модель збережено у {model_path}")
        print(f"Кількість зразків: {len(X)}")

    print("\nВсі режимні моделі натреновані!")


if __name__ == '__main__':
    train_regime_models()
