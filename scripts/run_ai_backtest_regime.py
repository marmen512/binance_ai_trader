"""
AI Backtest Runner with Regime Models
Run backtest using regime-specific models
"""
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from core.regime_model_engine import RegimeModelEngine
from core.regime_detector import RegimeDetector
from core.probability_gate import ProbabilityGate
from core.position_sizer import PositionSizer
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import compute_metrics


def run_backtest_regime():
    """Run AI backtest with regime-specific models"""
    
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    df = df.dropna()
    
    print("Initializing regime model engine...")
    engine = RegimeModelEngine()
    
    print("Initializing components...")
    regime_detector = RegimeDetector()
    probability_gate = ProbabilityGate()
    position_sizer = PositionSizer()
    
    print("Initializing backtester...")
    backtester = AIBacktester(
        engine=engine,
        regime_detector=regime_detector,
        probability_gate=probability_gate,
        position_sizer=position_sizer,
        initial_balance=10000,
        fee_rate=0.001
    )
    
    print("Running backtest...")
    results = backtester.run(df)
    
    print("\n" + "="*50)
    print("BACKTEST RESULTS (Regime Models)")
    print("="*50)
    print(f"Initial Balance: ${results['initial_balance']:.2f}")
    print(f"Final Balance: ${results['final_balance']:.2f}")
    print(f"Total Return: {results['total_return']:.2f}%")
    print(f"Number of Trades: {results['num_trades']}")
    
    # Compute additional metrics
    metrics = compute_metrics(
        results['trades'],
        results['equity_curve'],
        results['initial_balance']
    )
    
    print(f"\nWin Rate: {metrics['win_rate']:.2f}%")
    print(f"Average Return per Trade: {metrics['avg_return']:.2f}%")
    print(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    
    print("\nLast 5 trades:")
    for trade in results['trades'][-5:]:
        print(f"  {trade['timestamp']}: {trade['type']:4s} @ ${trade['price']:.2f} "
              f"(regime={trade['regime']}, conf={trade['confidence']:.2f})")


if __name__ == '__main__':
    run_backtest_regime()
