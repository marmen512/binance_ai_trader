"""
Train ensemble models: RandomForest, GradientBoosting, ExtraTrees.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.model_selection import train_test_split
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
    future_returns = df['close'].pct_change(5).shift(-5)
    
    # Classification thresholds
    buy_threshold = 0.002
    sell_threshold = -0.002
    
    target = pd.Series(1, index=df.index)  # Default HOLD
    target[future_returns > buy_threshold] = 2  # BUY
    target[future_returns < sell_threshold] = 0  # SELL
    
    return features, target


def train_ensemble():
    """
    Train ensemble of RandomForest, GradientBoosting, and ExtraTrees.
    """
    print("[EnsembleTraining] Starting ensemble training...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[EnsembleTraining] Error: {data_path} not found")
        print("[EnsembleTraining] Please run scripts/download_btc_5m.py first")
        return
    
    df = pd.read_csv(data_path)
    print(f"[EnsembleTraining] Loaded {len(df)} rows from {data_path}")
    
    # Prepare features and target
    X, y = prepare_features(df)
    
    # Remove NaN values
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]
    
    print(f"[EnsembleTraining] Training samples: {len(X)}")
    print(f"[EnsembleTraining] Class distribution: {y.value_counts().to_dict()}")
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X.values, y.values, test_size=0.2, random_state=42
    )
    
    print(f"[EnsembleTraining] Train: {len(X_train)}, Test: {len(X_test)}")
    
    os.makedirs("models", exist_ok=True)
    
    # Train RandomForest
    print("\n[EnsembleTraining] Training RandomForest...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_score = rf.score(X_test, y_test)
    print(f"[EnsembleTraining] RandomForest test accuracy: {rf_score:.4f}")
    joblib.dump(rf, "models/rf_btc_5m.pkl")
    
    # Train GradientBoosting
    print("\n[EnsembleTraining] Training GradientBoosting...")
    gb = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42
    )
    gb.fit(X_train, y_train)
    gb_score = gb.score(X_test, y_test)
    print(f"[EnsembleTraining] GradientBoosting test accuracy: {gb_score:.4f}")
    joblib.dump(gb, "models/gb_btc_5m.pkl")
    
    # Train ExtraTrees
    print("\n[EnsembleTraining] Training ExtraTrees...")
    et = ExtraTreesClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    et.fit(X_train, y_train)
    et_score = et.score(X_test, y_test)
    print(f"[EnsembleTraining] ExtraTrees test accuracy: {et_score:.4f}")
    joblib.dump(et, "models/et_btc_5m.pkl")
    
    print("\n[EnsembleTraining] All models trained and saved")


if __name__ == '__main__':
    train_ensemble()
