#!/usr/bin/env python
"""
Training pipeline for signal prediction model.

Trains a multi-class classifier to predict trading signals (BUY/HOLD/SELL)
based on OHLCV features.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def build_target(df: pd.DataFrame, horizon: int = 1, threshold: float = 0.004, binary: bool = False) -> pd.Series:
    """
    Build target variable based on future returns.
    
    Args:
        df: DataFrame with 'close' column
        horizon: Number of periods to look ahead
        threshold: Return threshold for classification
        binary: If True, build binary target (0/1), else multi-class (-1/0/1)
    
    Returns:
        Series with target values
    """
    # Calculate future returns
    future_close = df['close'].shift(-horizon)
    future_return = (future_close - df['close']) / df['close']
    
    if binary:
        # Binary: 1 if future_return > threshold, else 0
        target = (future_return > threshold).astype(int)
    else:
        # Multi-class: 1 (BUY), 0 (HOLD), -1 (SELL)
        target = pd.Series(0, index=df.index)
        target[future_return > threshold] = 1
        target[future_return < -threshold] = -1
    
    return target


def main():
    parser = argparse.ArgumentParser(description='Train signal prediction model')
    parser.add_argument('--candles', type=str, required=True,
                        help='Path to candles CSV file (timestamp,open,high,low,close,volume)')
    parser.add_argument('--out', type=str, default='models/signal_model.pkl',
                        help='Output path for trained model artifact')
    parser.add_argument('--horizon', type=int, default=1,
                        help='Number of periods to look ahead for target')
    parser.add_argument('--threshold', type=float, default=0.004,
                        help='Return threshold for classification')
    parser.add_argument('--binary', action='store_true',
                        help='Train binary classifier instead of multi-class')
    parser.add_argument('--multiclass', action='store_true', default=True,
                        help='Train multi-class classifier (default)')
    
    args = parser.parse_args()
    
    # Load required packages
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.impute import SimpleImputer
        from sklearn.metrics import classification_report, roc_auc_score
        from sklearn.model_selection import TimeSeriesSplit
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        import joblib
    except ImportError as e:
        print(f"Error: Required package not installed: {e}")
        print("Please install: pip install scikit-learn joblib")
        sys.exit(1)
    
    # Try to import LightGBM (optional)
    try:
        import lightgbm as lgb
        has_lgb = True
    except ImportError:
        has_lgb = False
        print("LightGBM not available, using RandomForest instead")
    
    # Import features module
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from app.core.features import compute_ohlcv_features
    except ImportError:
        print("Error: Could not import app.core.features")
        print("Make sure you're running from the repository root")
        sys.exit(1)
    
    # Read candles data
    print(f"Loading candles from {args.candles}")
    df = pd.read_csv(args.candles)
    
    # Ensure required columns exist
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"Error: Missing required columns: {missing_cols}")
        sys.exit(1)
    
    print(f"Loaded {len(df)} candles")
    
    # Compute features
    print("Computing features...")
    df = compute_ohlcv_features(df)
    
    # Build target
    binary_mode = args.binary and not args.multiclass
    print(f"Building {'binary' if binary_mode else 'multi-class'} target...")
    df['target'] = build_target(df, horizon=args.horizon, threshold=args.threshold, binary=binary_mode)
    
    # Remove rows with NaN target (last N rows)
    df = df[df['target'].notna()].copy()
    
    # Define feature columns (exclude OHLCV and target)
    feature_cols = [
        'return', 'log_return',
        'high_low_spread', 'open_close_spread', 'candle_body',
        'atr_14_norm',
        'ema_9_21_cross', 'ema_9_50_cross',
        'rsi_14',
        'macd_norm', 'macd_hist',
        'volatility_10', 'volatility_30',
        'volume_spike', 'volume_change'
    ]
    
    # Prepare feature matrix and target
    X = df[feature_cols].copy()
    y = df['target'].copy()
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Target distribution:\n{y.value_counts().sort_index()}")
    
    # Build preprocessor pipeline
    print("Building preprocessor pipeline...")
    preprocessor = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value=0)),
        ('scaler', StandardScaler())
    ])
    
    # Fit preprocessor and transform features
    X_transformed = preprocessor.fit_transform(X)
    
    # Train model
    print("Training model...")
    if has_lgb and not binary_mode:
        # Use LightGBM for multi-class
        model = lgb.LGBMClassifier(
            objective='multiclass',
            num_class=3,
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
    elif has_lgb and binary_mode:
        # Use LightGBM for binary
        model = lgb.LGBMClassifier(
            objective='binary',
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
            n_jobs=-1,
            verbose=-1
        )
    else:
        # Fall back to RandomForest
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
    
    # Time series cross-validation
    print("Evaluating with TimeSeriesSplit...")
    tscv = TimeSeriesSplit(n_splits=3)
    
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X_transformed)):
        X_train, X_val = X_transformed[train_idx], X_transformed[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        
        print(f"\nFold {fold + 1}:")
        print(classification_report(y_val, y_pred, zero_division=0))
        
        # ROC AUC (if applicable)
        if hasattr(model, 'predict_proba') and len(np.unique(y)) > 2:
            try:
                y_proba = model.predict_proba(X_val)
                # One-vs-rest ROC AUC for multi-class
                roc_auc = roc_auc_score(y_val, y_proba, multi_class='ovr', average='macro')
                print(f"ROC AUC (macro): {roc_auc:.4f}")
            except Exception as e:
                print(f"Could not compute ROC AUC: {e}")
    
    # Train final model on all data
    print("\nTraining final model on all data...")
    model.fit(X_transformed, y)
    
    # Save model artifact
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    artifact = {
        'model': model,
        'preprocessor': preprocessor,
        'feature_names': feature_cols
    }
    
    print(f"Saving model to {output_path}")
    joblib.dump(artifact, output_path)
    
    print("\nTraining complete!")
    print(f"Model saved to: {output_path}")
    print(f"Features used: {len(feature_cols)}")
    print(f"Feature names: {', '.join(feature_cols)}")


if __name__ == '__main__':
    main()
