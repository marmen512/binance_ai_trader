"""
Тренування BTC-специфічної моделі на 5m даних.
"""
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def main():
    print("Завантаження даних BTC 5m...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Побудова ознак...")
    fb = FeatureBuilder()
    df = fb.build(df)
    
    print("Побудова таргету...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    # BTC-специфічні ознаки
    FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    X = df[FEATURES]
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    print("Тренування BTC-специфічної моделі...")
    model = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42)
    model.fit(X_train, y_train)
    
    acc = model.score(X_test, y_test)
    print(f"BTC Model accuracy: {acc:.4f}")
    
    with open('models/btc_5m_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("Модель збережено в models/btc_5m_model.pkl")


if __name__ == '__main__':
    main()
