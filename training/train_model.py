"""
Загальний скрипт тренування моделі.
"""
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/candles.csv')
    
    print("Побудова ознак...")
    fb = FeatureBuilder()
    df = fb.build(df)
    
    print("Побудова таргету...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    # Загальні ознаки
    FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema9', 'ema21', 'ema_diff',
                'rsi', 'range', 'body', 'body_pct', 'vol_spike']
    X = df[FEATURES]
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    print("Тренування моделі...")
    model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=42)
    model.fit(X_train, y_train)
    
    acc = model.score(X_test, y_test)
    print(f"Model accuracy: {acc:.4f}")
    
    with open('models/signal_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("Модель збережено в models/signal_model.pkl")


if __name__ == '__main__':
    main()
