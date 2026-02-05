"""
Walk-Forward Training
Implements walk-forward optimization for time series cross-validation
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from core.ensemble_engine import EnsembleEngine
from core.regime_detector import RegimeDetector
from core.probability_gate import ProbabilityGate
from core.position_sizer import PositionSizer
from training.build_target import build_target
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


def walk_forward(train_size=5000, test_size=1000):
    """
    Perform walk-forward training and testing
    
    Args:
        train_size: Number of samples for training window
        test_size: Number of samples for testing window
    """
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    
    print("Building targets...")
    df = build_target(df, horizon=6)
    df = df.dropna()
    
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 
                    'range', 'body', 'body_pct', 'vol_spike']
    
    # Walk-forward loop
    start_idx = 0
    all_results = []
    
    while start_idx + train_size + test_size <= len(df):
        print(f"\n{'='*60}")
        print(f"Walk-forward iteration: train_idx={start_idx} to {start_idx+train_size}")
        print(f"                        test_idx={start_idx+train_size} to {start_idx+train_size+test_size}")
        
        # Split data
        train_df = df.iloc[start_idx:start_idx+train_size]
        test_df = df.iloc[start_idx:start_idx+train_size+test_size]
        
        X_train = train_df[feature_cols].values
        y_train = train_df['target'].values
        
        print(f"Training samples: {len(X_train)}")
        print(f"Target distribution: {np.bincount(y_train.astype(int) + 1)}")
        
        # Train temporary model
        print("Training Random Forest...")
        temp_model = RandomForestClassifier(
            n_estimators=100, 
            max_depth=10, 
            random_state=42, 
            n_jobs=-1
        )
        temp_model.fit(X_train, y_train)
        
        # Save temporary model
        joblib.dump(temp_model, 'models/tmp_wf.pkl')
        print("Saved temporary model: models/tmp_wf.pkl")
        
        # Create ensemble engine with temporary model as first model
        print("Creating ensemble engine...")
        engine = EnsembleEngine(
            model_paths=['models/tmp_wf.pkl', 'models/gb_btc_5m.pkl', 'models/et_btc_5m.pkl']
        )
        
        # Run backtest on test window
        print("Running backtest on test window...")
        regime_detector = RegimeDetector()
        probability_gate = ProbabilityGate()
        position_sizer = PositionSizer()
        
        backtester = AIBacktester(
            engine=engine,
            regime_detector=regime_detector,
            probability_gate=probability_gate,
            position_sizer=position_sizer,
            initial_balance=10000
        )
        
        results = backtester.run(test_df)
        metrics = compute_metrics(
            results['trades'],
            results['equity_curve'],
            results['initial_balance']
        )
        
        print(f"\nTest Results:")
        print(f"  Total Return: {results['total_return']:.2f}%")
        print(f"  Num Trades: {results['num_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.2f}%")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
        
        all_results.append({
            'start_idx': start_idx,
            'train_size': train_size,
            'test_size': test_size,
            'total_return': results['total_return'],
            'num_trades': results['num_trades'],
            'win_rate': metrics['win_rate'],
            'sharpe_ratio': metrics['sharpe_ratio']
        })
        
        # Move window forward
        start_idx += test_size
    
    # Summary
    print(f"\n{'='*60}")
    print("WALK-FORWARD SUMMARY")
    print(f"{'='*60}")
    results_df = pd.DataFrame(all_results)
    print(f"Average Return: {results_df['total_return'].mean():.2f}%")
    print(f"Average Win Rate: {results_df['win_rate'].mean():.2f}%")
    print(f"Average Sharpe: {results_df['sharpe_ratio'].mean():.2f}")
    print(f"Total Iterations: {len(all_results)}")


if __name__ == '__main__':
    walk_forward(train_size=5000, test_size=1000)
