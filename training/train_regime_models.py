"""
Train Regime-Specific Models
Trains separate Random Forest models for each market regime
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from core.regime_detector import RegimeDetector
from training.build_target import build_target


def train_regime_models():
    """Train regime-specific models"""
    
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    
    print("Building targets...")
    df = build_target(df, horizon=6)
    df = df.dropna()
    
    print("Detecting regimes for all data points...")
    detector = RegimeDetector()
    
    regimes = []
    for i in range(100, len(df)):  # Need at least 100 rows for regime detection
        regime = detector.detect(df.iloc[:i+1])
        regimes.append(regime)
    
    # Pad with None for first 100 rows
    regimes = [None] * 100 + regimes
    df['regime'] = regimes
    
    # Remove None regimes
    df = df[df['regime'].notna()]
    
    print(f"\nRegime distribution:")
    print(df['regime'].value_counts())
    
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 
                    'range', 'body', 'body_pct', 'vol_spike']
    
    # Train model for each regime
    regimes_to_train = ['VOLATILE', 'TREND', 'RANGE']
    
    for regime in regimes_to_train:
        print(f"\n{'='*60}")
        print(f"Training model for regime: {regime}")
        print(f"{'='*60}")
        
        # Filter data for this regime
        regime_df = df[df['regime'] == regime]
        
        if len(regime_df) < 100:
            print(f"Not enough data for regime {regime} ({len(regime_df)} samples)")
            continue
        
        X = regime_df[feature_cols].values
        y = regime_df['target'].values
        
        print(f"Training samples: {len(X)}")
        print(f"Target distribution: {np.bincount(y.astype(int) + 1)}")
        
        # Split train/test (80/20)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]
        
        # Train Random Forest
        print(f"Training Random Forest for {regime}...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model.fit(X_train, y_train)
        
        score = model.score(X_test, y_test)
        print(f"Test accuracy: {score:.4f}")
        
        # Save model
        output_path = f'models/model_{regime}.pkl'
        joblib.dump(model, output_path)
        print(f"Saved: {output_path}")
    
    print("\n" + "="*60)
    print("Regime-specific training complete!")
    print("="*60)


if __name__ == '__main__':
    train_regime_models()
