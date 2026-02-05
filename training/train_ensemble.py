"""
Тренування ансамблю моделей на BTC 5m даних.
"""
import pandas as pd
import pickle
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.model_selection import train_test_split
from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def main():
    print("Завантаження даних...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Побудова ознак...")
    fb = FeatureBuilder()
    df = fb.build(df)
    
    print("Побудова таргету...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    # Підготовка даних
    FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema9', 'ema21', 'ema_diff', 
                'rsi', 'range', 'body', 'body_pct', 'vol_spike']
    X = df[FEATURES]
    y = df['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
    
    # Тренування Random Forest
    print("Тренування Random Forest...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=7, random_state=42)
    rf.fit(X_train, y_train)
    rf_acc = rf.score(X_test, y_test)
    print(f"Random Forest accuracy: {rf_acc:.4f}")
    
    with open('models/rf_btc_5m.pkl', 'wb') as f:
        pickle.dump(rf, f)
    
    # Тренування Gradient Boosting
    print("Тренування Gradient Boosting...")
    gb = GradientBoostingClassifier(n_estimators=200, max_depth=4, random_state=42)
    gb.fit(X_train, y_train)
    gb_acc = gb.score(X_test, y_test)
    print(f"Gradient Boosting accuracy: {gb_acc:.4f}")
    
    with open('models/gb_btc_5m.pkl', 'wb') as f:
        pickle.dump(gb, f)
    
    # Тренування Extra Trees
    print("Тренування Extra Trees...")
    et = ExtraTreesClassifier(n_estimators=400, max_depth=8, random_state=42)
    et.fit(X_train, y_train)
    et_acc = et.score(X_test, y_test)
    print(f"Extra Trees accuracy: {et_acc:.4f}")
    
    with open('models/et_btc_5m.pkl', 'wb') as f:
        pickle.dump(et, f)
    
    print("Моделі збережено!")


if __name__ == '__main__':
    main()
