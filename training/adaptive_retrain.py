"""
Adaptive Retrain - адаптивне перенавчання на останніх даних.
"""
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    # Використовуємо останні 12000 рядків
    print("Використання останніх 12000 рядків для перенавчання...")
    df = df.tail(12000).copy()
    
    print("Побудова ознак...")
    fb = FeatureBuilder()
    df = fb.build(df)
    
    print("Побудова таргету...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    X = df[FEATURES]
    y = df['target']
    
    print("Тренування адаптивної моделі...")
    model = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42)
    model.fit(X, y)
    
    print("Збереження моделі в models/adaptive_latest.pkl...")
    with open('models/adaptive_latest.pkl', 'wb') as f:
        pickle.dump(model, f)
    
    print("✅ Адаптивна модель перенавчена та збережена!")


if __name__ == '__main__':
    main()
