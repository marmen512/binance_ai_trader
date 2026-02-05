"""
Специфічний скрипт тренування для BTC 5m даних.
Використовує власний набір ознак для BTC торгівлі.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

# Додаємо кореневу директорію до шляху
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def build_btc_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Будує специфічні ознаки для BTC 5m.
    
    Args:
        df: DataFrame з OHLCV даними
        
    Returns:
        DataFrame з новими ознаками
    """
    df = df.copy()
    
    # Базові прибутковості
    df['ret1'] = df['close'].pct_change(1)
    df['ret3'] = df['close'].pct_change(3)
    df['ret12'] = df['close'].pct_change(12)
    
    # Волатильність
    df['vol10'] = df['ret1'].rolling(10).std()
    
    # EMA
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_diff'] = (df['ema9'] - df['ema21']) / df['ema21']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # Тіло свічки
    df['body_pct'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-10)
    
    # Сплеск волатильності
    df['vol_spike'] = df['vol10'] / df['vol10'].rolling(50).mean()
    
    return df.dropna()


if __name__ == '__main__':
    print("=== Тренування BTC 5m моделі ===")
    
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
    
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    
    # Тренування RandomForest
    print("Тренування RandomForest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Оцінка
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")
    
    # Збереження
    model_path = 'models/btc_5m_model.pkl'
    os.makedirs('models', exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Модель збережено: {model_path}")
