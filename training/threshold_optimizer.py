"""
Threshold Optimizer
Optimizes probability thresholds for signal filtering
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from core.ensemble_engine import EnsembleEngine
from core.regime_detector import RegimeDetector
from core.probability_gate import ProbabilityGate
from core.position_sizer import PositionSizer
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


def optimize_threshold():
    """Optimize probability threshold for ensemble engine"""
    
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    df = df.dropna()
    
    # Test different thresholds
    thresholds = [0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    
    print("\n" + "="*70)
    print("THRESHOLD OPTIMIZATION")
    print("="*70)
    
    best_threshold = None
    best_return = -float('inf')
    results_list = []
    
    for threshold in thresholds:
        print(f"\nTesting threshold: {threshold:.2f}")
        
        # Create engine with min_prob_override
        engine = EnsembleEngine(min_prob_override=threshold)
        
        # Create backtester
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
        
        # Run backtest
        results = backtester.run(df)
        metrics = compute_metrics(
            results['trades'],
            results['equity_curve'],
            results['initial_balance']
        )
        
        print(f"  Total Return: {results['total_return']:.2f}%")
        print(f"  Num Trades: {results['num_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.2f}%")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
        
        results_list.append({
            'threshold': threshold,
            'total_return': results['total_return'],
            'num_trades': results['num_trades'],
            'win_rate': metrics['win_rate'],
            'sharpe_ratio': metrics['sharpe_ratio']
        })
        
        if results['total_return'] > best_return:
            best_return = results['total_return']
            best_threshold = threshold
    
    # Print summary
    print("\n" + "="*70)
    print("OPTIMIZATION SUMMARY")
    print("="*70)
    print(f"\nBest Threshold: {best_threshold:.2f}")
    print(f"Best Return: {best_return:.2f}%")
    
    print("\nAll Results:")
    results_df = pd.DataFrame(results_list)
    print(results_df.to_string(index=False))


if __name__ == '__main__':
    optimize_threshold()
