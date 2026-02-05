"""
Training pipeline for multiclass signal prediction model.

This script trains a model to predict future price movements:
- Class 1: significant positive return (> threshold)
- Class 0: neutral (between -threshold and +threshold)
- Class -1: significant negative return (< -threshold)

The trained model, preprocessor, and feature names are serialized together.
"""
import argparse
import os
import sys
import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.features import compute_ohlcv_features

from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Train multiclass signal prediction model'
    )
    parser.add_argument(
        '--candles',
        type=str,
        required=True,
        help='Path to candles CSV file (timestamp, open, high, low, close, volume)'
    )
    parser.add_argument(
        '--out',
        type=str,
        default='models/signal_model.pkl',
        help='Output path for serialized model (default: models/signal_model.pkl)'
    )
    parser.add_argument(
        '--horizon',
        type=int,
        default=1,
        help='Prediction horizon in candles (default: 1)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.004,
        help='Return threshold for positive/negative class (default: 0.004)'
    )
    parser.add_argument(
        '--force-rf',
        action='store_true',
        help='Force use of RandomForestClassifier instead of LightGBM'
    )
    parser.add_argument(
        '--test-size',
        type=float,
        default=0.2,
        help='Test set size fraction (default: 0.2)'
    )
    
    return parser.parse_args()


def load_candles(csv_path: str) -> pd.DataFrame:
    """Load candles from CSV file."""
    print(f"Loading candles from {csv_path}...")
    
    # Try to load with different column name variations
    df = pd.read_csv(csv_path)
    
    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()
    
    # Check for required columns
    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    print(f"Loaded {len(df)} candles")
    return df[required_cols]


def build_target(df: pd.DataFrame, horizon: int, threshold: float) -> pd.Series:
    """
    Build multiclass target based on future returns.
    
    Args:
        df: DataFrame with close prices
        horizon: Number of periods to look ahead
        threshold: Return threshold for positive/negative classification
        
    Returns:
        Series with target labels: 1 (positive), 0 (neutral), -1 (negative)
    """
    # Calculate future returns
    future_ret = df['close'].shift(-horizon) / df['close'] - 1.0
    
    # Create target based on thresholds
    target = pd.Series(0, index=df.index)
    target[future_ret > threshold] = 1
    target[future_ret < -threshold] = -1
    
    return target


def prepare_data(df: pd.DataFrame, horizon: int, threshold: float):
    """
    Prepare features and target for training.
    
    Args:
        df: Raw candles DataFrame
        horizon: Prediction horizon
        threshold: Return threshold
        
    Returns:
        X (features DataFrame), y (target Series), feature_names (list)
    """
    print("Computing features...")
    df_features = compute_ohlcv_features(df)
    
    print("Building target...")
    target = build_target(df, horizon, threshold)
    
    # Feature columns to use for training
    feature_cols = [
        'returns', 'log_returns', 'volatility', 'atr',
        'candle_body_pct', 'high_low_spread',
        'ema_fast', 'ema_slow', 'rsi', 'macd',
        'vol_spike', 'ret_1', 'ret_3', 'ret_5'
    ]
    
    # Extract features
    X = df_features[feature_cols].copy()
    y = target.copy()
    
    # Remove rows with NaN in target (last 'horizon' rows)
    valid_mask = y.notna()
    X = X[valid_mask]
    y = y[valid_mask]
    
    print(f"Dataset size: {len(X)} samples")
    print(f"Target distribution:\n{y.value_counts().sort_index()}")
    
    return X, y, feature_cols


def train_model(X_train, y_train, X_test, y_test, force_rf: bool = False):
    """
    Train classification model.
    
    Args:
        X_train, y_train: Training data
        X_test, y_test: Test data
        force_rf: Force use of RandomForestClassifier
        
    Returns:
        Trained model, preprocessor pipeline
    """
    # Create preprocessor pipeline
    print("Creating preprocessor pipeline...")
    preprocessor = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])
    
    # Fit preprocessor on training data
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    
    # Try to use LightGBM if available, else fallback to RandomForest
    model = None
    model_name = None
    
    if not force_rf:
        try:
            import lightgbm as lgb
            print("Training LightGBM classifier...")
            model = lgb.LGBMClassifier(
                objective='multiclass',
                num_class=3,
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
                verbosity=-1
            )
            model_name = "LightGBM"
        except ImportError:
            print("LightGBM not available, falling back to RandomForest")
            force_rf = True
    
    if force_rf or model is None:
        from sklearn.ensemble import RandomForestClassifier
        print("Training RandomForest classifier...")
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        model_name = "RandomForest"
    
    # Train model
    model.fit(X_train_processed, y_train)
    
    # Evaluate on test set
    print(f"\n{model_name} Model Evaluation:")
    y_pred = model.predict(X_test_processed)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Negative', 'Neutral', 'Positive']))
    
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Show feature importances if available
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        feature_names = X_train.columns
        feat_imp_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False)
        print("\nTop 10 Feature Importances:")
        print(feat_imp_df.head(10).to_string(index=False))
    
    return model, preprocessor


def save_artifact(model, preprocessor, feature_names: list, out_path: str):
    """
    Save model artifact with joblib.
    
    Args:
        model: Trained model
        preprocessor: Fitted preprocessor pipeline
        feature_names: List of feature names
        out_path: Output file path
    """
    # Create output directory if it doesn't exist
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    
    # Create artifact dictionary
    artifact = {
        'model': model,
        'preprocessor': preprocessor,
        'feature_names': feature_names
    }
    
    # Save with joblib
    print(f"\nSaving artifact to {out_path}...")
    joblib.dump(artifact, out_path)
    print(f"Artifact saved successfully ({os.path.getsize(out_path)} bytes)")


def main():
    """Main training pipeline."""
    args = parse_args()
    
    print("=" * 70)
    print("Signal Model Training Pipeline")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  Candles: {args.candles}")
    print(f"  Output: {args.out}")
    print(f"  Horizon: {args.horizon}")
    print(f"  Threshold: {args.threshold}")
    print(f"  Test size: {args.test_size}")
    print(f"  Force RF: {args.force_rf}")
    print("=" * 70)
    
    # Load candles
    df = load_candles(args.candles)
    
    # Prepare data
    X, y, feature_names = prepare_data(df, args.horizon, args.threshold)
    
    # Time-based split (train on first 80%, test on last 20%)
    split_idx = int(len(X) * (1 - args.test_size))
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y.iloc[:split_idx]
    y_test = y.iloc[split_idx:]
    
    print(f"\nTrain size: {len(X_train)}, Test size: {len(X_test)}")
    
    # Train model
    model, preprocessor = train_model(X_train, y_train, X_test, y_test, args.force_rf)
    
    # Save artifact
    save_artifact(model, preprocessor, feature_names, args.out)
    
    print("\n" + "=" * 70)
    print("Training completed successfully!")
    print("=" * 70)


if __name__ == '__main__':
    main()
