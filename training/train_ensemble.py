"""
Ensemble Model Training Script
Trains RandomForest, GradientBoosting, and ExtraTrees models
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
import joblib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def train_ensemble():
    """Train ensemble models on BTC 5m data"""
    
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
    print(f"Target distribution: {np.bincount(y_train.astype(int) + 1)}")
    
    # Train Random Forest
    print("\nTraining Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_score = rf.score(X_test, y_test)
    print(f"Random Forest test accuracy: {rf_score:.4f}")
    joblib.dump(rf, 'models/rf_btc_5m.pkl')
    print("Saved: models/rf_btc_5m.pkl")
    
    # Train Gradient Boosting
    print("\nTraining Gradient Boosting...")
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    gb.fit(X_train, y_train)
    gb_score = gb.score(X_test, y_test)
    print(f"Gradient Boosting test accuracy: {gb_score:.4f}")
    joblib.dump(gb, 'models/gb_btc_5m.pkl')
    print("Saved: models/gb_btc_5m.pkl")
    
    # Train Extra Trees
    print("\nTraining Extra Trees...")
    et = ExtraTreesClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    et.fit(X_train, y_train)
    et_score = et.score(X_test, y_test)
    print(f"Extra Trees test accuracy: {et_score:.4f}")
    joblib.dump(et, 'models/et_btc_5m.pkl')
    print("Saved: models/et_btc_5m.pkl")
    
    print("\nEnsemble training complete!")


if __name__ == '__main__':
    train_ensemble()
