"""
Train BTC 5m Model
Trains a single Random Forest model for BTC 5m trading
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def train_btc_5m():
    """Train BTC 5m model"""
    
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    
    print("Building targets...")
    df = build_target(df, horizon=6)
    
    # Drop NaN rows
    df = df.dropna()
    
    # Select features for training
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 
                    'range', 'body', 'body_pct', 'vol_spike']
    
    X = df[feature_cols].values
    y = df['target'].values
    
    # Split train/test (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"Training set size: {len(X_train)}")
    print(f"Test set size: {len(X_test)}")
    
    # Train Random Forest
    print("\nTraining Random Forest...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    
    score = model.score(X_test, y_test)
    print(f"Test accuracy: {score:.4f}")
    
    # Save model
    output_path = 'models/btc_5m_model.pkl'
    joblib.dump(model, output_path)
    print(f"Saved: {output_path}")


if __name__ == '__main__':
    train_btc_5m()
