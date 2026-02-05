"""
Adaptive retraining: Retrain RandomForest on most recent data.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os


def prepare_features(df):
    """
    Prepare features from OHLCV data.
    """
    features = pd.DataFrame()
    
    # Price-based features
    features['returns'] = df['close'].pct_change()
    features['sma_20_diff'] = (df['close'] - df['close'].rolling(20).mean()) / df['close'].rolling(20).mean()
    features['sma_50_diff'] = (df['close'] - df['close'].rolling(50).mean()) / df['close'].rolling(50).mean()
    
    # Volume features
    features['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
    
    # Volatility
    features['volatility'] = df['close'].pct_change().rolling(20).std()
    
    # Target: future return direction
    # Positive return = BUY (2), Negative = SELL (0), Near zero = HOLD (1)
    future_returns = df['close'].pct_change(5).shift(-5)
    
    # Classification thresholds
    buy_threshold = 0.002  # 0.2% gain
    sell_threshold = -0.002  # 0.2% loss
    
    target = pd.Series(1, index=df.index)  # Default HOLD
    target[future_returns > buy_threshold] = 2  # BUY
    target[future_returns < sell_threshold] = 0  # SELL
    
    return features, target


def train_adaptive_model():
    """
    Retrain RandomForest on most recent 12k rows of data.
    """
    print("[AdaptiveRetrain] Starting adaptive retraining...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[AdaptiveRetrain] Error: {data_path} not found")
        print("[AdaptiveRetrain] Please run scripts/download_btc_5m.py first")
        return
    
    df = pd.read_csv(data_path)
    print(f"[AdaptiveRetrain] Loaded {len(df)} rows from {data_path}")
    
    # Use most recent 12k rows
    df = df.tail(12000).copy()
    print(f"[AdaptiveRetrain] Using most recent {len(df)} rows")
    
    # Prepare features and target
    X, y = prepare_features(df)
    
    # Remove NaN values
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]
    
    print(f"[AdaptiveRetrain] Training samples: {len(X)}")
    print(f"[AdaptiveRetrain] Class distribution: {y.value_counts().to_dict()}")
    
    # Train RandomForest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X.values, y.values)
    print("[AdaptiveRetrain] Model trained")
    
    # Save model
    output_path = "models/adaptive_latest.pkl"
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, output_path)
    print(f"[AdaptiveRetrain] Model saved to {output_path}")
    
    # Print feature importance
    importance = pd.DataFrame({
        'feature': X.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\n[AdaptiveRetrain] Feature importance:")
    print(importance.to_string(index=False))


if __name__ == '__main__':
    train_adaptive_model()
