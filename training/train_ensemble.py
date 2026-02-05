"""
Тренування ансамблю моделей: RandomForest, GradientBoosting, ExtraTrees.
Кожна модель тренується окремо і зберігається в models/.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
import joblib
import sys
import os

# Додаємо кореневу директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from training.build_target import build_target


def build_btc_features(df: pd.DataFrame) -> pd.DataFrame:
    """Будує ознаки для BTC 5m."""
    df = df.copy()
    
    df['ret1'] = df['close'].pct_change(1)
    df['ret3'] = df['close'].pct_change(3)
    df['ret12'] = df['close'].pct_change(12)
    df['vol10'] = df['ret1'].rolling(10).std()
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_diff'] = (df['ema9'] - df['ema21']) / df['ema21']
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['body_pct'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
    df['vol_spike'] = df['vol10'] / df['vol10'].rolling(50).mean()
    
    return df.dropna()


if __name__ == '__main__':
    print("=== Тренування ансамблю моделей ===")
    
    # Завантаження даних
    data_path = 'data/btcusdt_5m.csv'
    if not os.path.exists(data_path):
        print(f"Помилка: файл {data_path} не знайдено!")
        print("Запустіть спочатку: python scripts/download_btc_5m.py")
        sys.exit(1)
    
    df = pd.read_csv(data_path)
    print(f"Завантажено {len(df)} записів")
    
    # Побудова ознак
    df = build_btc_features(df)
    print(f"Після побудови ознак: {len(df)} записів")
    
    # Побудова таргета
    df = build_target(df, horizon=5, threshold=0.004)
    print(f"Після побудови таргета: {len(df)} записів")
    
    # Ознаки для моделі
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
    
    # Часово-впорядковане розділення
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    X_train = train_df[feature_cols]
    y_train = train_df['target']
    X_test = test_df[feature_cols]
    y_test = test_df['target']
    
    print(f"\nTrain: {len(X_train)}, Test: {len(X_test)}")
    print(f"Розподіл класів у train: {y_train.value_counts().to_dict()}")
    
    os.makedirs('models', exist_ok=True)
    
    # 1. RandomForest
    print("\n[1/3] Тренування RandomForest...")
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    rf_model.fit(X_train, y_train)
    rf_train_acc = rf_model.score(X_train, y_train)
    rf_test_acc = rf_model.score(X_test, y_test)
    print(f"RF Train accuracy: {rf_train_acc:.4f}")
    print(f"RF Test accuracy: {rf_test_acc:.4f}")
    
    rf_path = 'models/rf_btc_5m.pkl'
    joblib.dump(rf_model, rf_path)
    print(f"Збережено: {rf_path}")
    
    # 2. GradientBoosting
    print("\n[2/3] Тренування GradientBoosting...")
    gb_model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42
    )
    gb_model.fit(X_train, y_train)
    gb_train_acc = gb_model.score(X_train, y_train)
    gb_test_acc = gb_model.score(X_test, y_test)
    print(f"GB Train accuracy: {gb_train_acc:.4f}")
    print(f"GB Test accuracy: {gb_test_acc:.4f}")
    
    gb_path = 'models/gb_btc_5m.pkl'
    joblib.dump(gb_model, gb_path)
    print(f"Збережено: {gb_path}")
    
    # 3. ExtraTrees
    print("\n[3/3] Тренування ExtraTrees...")
    et_model = ExtraTreesClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    et_model.fit(X_train, y_train)
    et_train_acc = et_model.score(X_train, y_train)
    et_test_acc = et_model.score(X_test, y_test)
    print(f"ET Train accuracy: {et_train_acc:.4f}")
    print(f"ET Test accuracy: {et_test_acc:.4f}")
    
    et_path = 'models/et_btc_5m.pkl'
    joblib.dump(et_model, et_path)
    print(f"Збережено: {et_path}")
    
    print("\n=== Тренування завершено ===")
    print("Моделі збережено:")
    print(f"  - {rf_path}")
    print(f"  - {gb_path}")
    print(f"  - {et_path}")
