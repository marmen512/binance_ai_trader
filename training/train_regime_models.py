"""
Train regime-specific models: separate RandomForest per regime (TREND, RANGE, VOLATILE).
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.regime_detector import RegimeDetector


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


def train_regime_models():
    """
    Train separate models for each regime.
    """
    print("[RegimeTraining] Starting regime-specific model training...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[RegimeTraining] Error: {data_path} not found")
        print("[RegimeTraining] Please run scripts/download_btc_5m.py first")
        return
    
    df = pd.read_csv(data_path)
    print(f"[RegimeTraining] Loaded {len(df)} rows from {data_path}")
    
    # Detect regimes
    regime_detector = RegimeDetector()
    df = regime_detector.detect(df)
    
    print(f"[RegimeTraining] Regime distribution:")
    print(df['regime'].value_counts())
    
    # Prepare features
    X, y = prepare_features(df)
    
    # Remove NaN values
    mask = ~(X.isna().any(axis=1) | y.isna())
    X = X[mask]
    y = y[mask]
    df = df[mask]
    
    # Train model for each regime
    regimes = ['TREND', 'RANGE', 'VOLATILE']
    os.makedirs("models", exist_ok=True)
    
    for regime in regimes:
        print(f"\n[RegimeTraining] Training model for {regime}...")
        
        # Filter data for this regime
        regime_mask = df['regime'] == regime
        X_regime = X[regime_mask]
        y_regime = y[regime_mask]
        
        if len(X_regime) < 100:
            print(f"[RegimeTraining] Warning: Only {len(X_regime)} samples for {regime}, skipping")
            continue
        
        print(f"[RegimeTraining] {regime} samples: {len(X_regime)}")
        print(f"[RegimeTraining] Class distribution: {y_regime.value_counts().to_dict()}")
        
        # Train RandomForest
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_regime.values, y_regime.values)
        
        # Save model
        output_path = f"models/model_{regime}.pkl"
        joblib.dump(model, output_path)
        print(f"[RegimeTraining] {regime} model saved to {output_path}")


if __name__ == '__main__':
    train_regime_models()
