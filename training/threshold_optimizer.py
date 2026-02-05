"""
Threshold optimizer: find optimal probability threshold for trading signals.
"""
import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester


def optimize_threshold():
    """
    Loop through probability thresholds to find the best one.
    """
    print("[ThresholdOptimizer] Starting threshold optimization...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[ThresholdOptimizer] Error: {data_path} not found")
        return
    
    df = pd.read_csv(data_path)
    print(f"[ThresholdOptimizer] Loaded {len(df)} rows")
    
    # Use last 20% for testing
    test_size = int(len(df) * 0.2)
    test_df = df.tail(test_size).copy()
    print(f"[ThresholdOptimizer] Testing on last {test_size} rows")
    
    # Create engine
    try:
        engine = EnsembleEngine()
        print(f"[ThresholdOptimizer] Loaded ensemble with {len(engine.models)} models")
    except Exception as e:
        print(f"[ThresholdOptimizer] Error loading engine: {e}")
        return
    
    # Test thresholds from 0.55 to 0.73 step 0.02
    thresholds = np.arange(0.55, 0.74, 0.02)
    results = []
    
    for threshold in thresholds:
        print(f"\n[ThresholdOptimizer] Testing threshold: {threshold:.2f}")
        
        # Set threshold override
        engine.min_prob_override = threshold
        
        # Run backtest
        try:
            backtester = AIBacktester(test_df, engine, initial_balance=10000)
            backtester.run()
            final_balance = backtester.get_balance()
            total_return = (final_balance - 10000) / 10000 * 100
            
            print(f"[ThresholdOptimizer] Threshold {threshold:.2f}: ${final_balance:.2f} ({total_return:+.2f}%)")
            results.append({
                'threshold': threshold,
                'final_balance': final_balance,
                'return_pct': total_return
            })
        except Exception as e:
            print(f"[ThresholdOptimizer] Backtest error: {e}")
            results.append({
                'threshold': threshold,
                'final_balance': 10000,
                'return_pct': 0
            })
    
    # Find best threshold
    print("\n[ThresholdOptimizer] Results summary:")
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    best_result = results_df.loc[results_df['final_balance'].idxmax()]
    print(f"\n[ThresholdOptimizer] Best threshold: {best_result['threshold']:.2f}")
    print(f"[ThresholdOptimizer] Best final balance: ${best_result['final_balance']:.2f}")
    print(f"[ThresholdOptimizer] Best return: {best_result['return_pct']:+.2f}%")


if __name__ == '__main__':
    optimize_threshold()
