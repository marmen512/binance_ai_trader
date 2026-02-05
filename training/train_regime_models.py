"""
Тренування окремих моделей для кожного режиму ринку.
"""
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from core.feature_builder import FeatureBuilder
from training.build_target import build_target
from core.regime_detector import RegimeDetector


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Побудова ознак...")
    fb = FeatureBuilder()
    df = fb.build(df)
    
    print("Побудова таргету...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    print("Визначення режимів...")
    detector = RegimeDetector()
    regimes = []
    
    for i in range(100, len(df)):
        window = df.iloc[:i+1]
        regime = detector.detect(window)
        regimes.append(regime)
    
    # Додаємо колонку режиму
    df = df.iloc[100:].copy()
    df['regime'] = regimes
    
    FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    
    # Тренуємо окрему модель для кожного режиму
    for regime in ['TREND', 'RANGE', 'VOLATILE']:
        print(f"\n{'='*50}")
        print(f"Тренування моделі для режиму {regime}...")
        
        regime_df = df[df['regime'] == regime].copy()
        
        if len(regime_df) < 100:
            print(f"Недостатньо даних для режиму {regime}, пропускаємо...")
            continue
        
        X = regime_df[FEATURES]
        y = regime_df['target']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        model = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42)
        model.fit(X_train, y_train)
        
        acc = model.score(X_test, y_test)
        print(f"Accuracy для {regime}: {acc:.4f}")
        print(f"Кількість зразків: {len(regime_df)}")
        
        # Зберігаємо модель
        model_path = f'models/model_{regime}.pkl'
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"Модель збережено: {model_path}")
    
    print(f"\n{'='*50}")
    print("Тренування завершено!")


if __name__ == '__main__':
    main()
