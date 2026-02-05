"""
Walk-forward validation: train on sliding windows and test on out-of-sample data.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


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


def walk_forward_validation():
    """
    Walk-forward validation with sliding windows.
    """
    print("[WalkForward] Starting walk-forward validation...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[WalkForward] Error: {data_path} not found")
        return
    
    df = pd.read_csv(data_path)
    print(f"[WalkForward] Loaded {len(df)} rows")
    
    # Walk-forward parameters
    train_window = 5000  # Train on 5000 bars
    test_window = 1000   # Test on 1000 bars
    step = 1000          # Slide by 1000 bars
    
    results = []
    os.makedirs("models", exist_ok=True)
    
    # Sliding windows
    start = 0
    window_num = 0
    
    while start + train_window + test_window <= len(df):
        window_num += 1
        train_end = start + train_window
        test_end = train_end + test_window
        
        print(f"\n[WalkForward] Window {window_num}: train[{start}:{train_end}] test[{train_end}:{test_end}]")
        
        # Prepare training data
        train_df = df.iloc[start:train_end].copy()
        X_train, y_train = prepare_features(train_df)
        
        # Remove NaN
        mask_train = ~(X_train.isna().any(axis=1) | y_train.isna())
        X_train = X_train[mask_train]
        y_train = y_train[mask_train]
        
        print(f"[WalkForward] Training on {len(X_train)} samples")
        
        # Train model
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=20,
            min_samples_leaf=10,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train.values, y_train.values)
        
        # Save as temporary walk-forward model
        temp_model_path = "models/tmp_wf.pkl"
        joblib.dump(model, temp_model_path)
        
        # Load into ensemble engine (replace first model)
        try:
            engine = EnsembleEngine()
            if len(engine.models) > 0:
                engine.models[0] = model
                print(f"[WalkForward] Inserted WF model into ensemble position 0")
        except Exception as e:
            print(f"[WalkForward] Could not load into ensemble: {e}")
        
        # Prepare test data
        test_df = df.iloc[train_end:test_end].copy()
        
        # Run backtest on test window
        try:
            backtester = AIBacktester(test_df, engine, initial_balance=10000)
            backtester.run()
            final_balance = backtester.get_balance()
            
            print(f"[WalkForward] Window {window_num} final balance: ${final_balance:.2f}")
            results.append(final_balance)
        except Exception as e:
            print(f"[WalkForward] Backtest error: {e}")
            results.append(10000)
        
        # Move to next window
        start += step
    
    # Summary
    print(f"\n[WalkForward] Walk-forward validation complete")
    print(f"[WalkForward] Windows tested: {len(results)}")
    if len(results) > 0:
        print(f"[WalkForward] Mean final balance: ${np.mean(results):.2f}")
        print(f"[WalkForward] Std final balance: ${np.std(results):.2f}")
        print(f"[WalkForward] Min: ${np.min(results):.2f}, Max: ${np.max(results):.2f}")


if __name__ == '__main__':
    walk_forward_validation()
