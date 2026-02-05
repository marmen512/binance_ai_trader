"""
Run AI backtest with regime-specific models.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.regime_model_engine import RegimeModelEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import print_metrics


def run_regime_backtest():
    """
    Run backtest using regime-specific models.
    """
    print("[RunRegimeBacktest] Starting regime-specific backtest...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[RunRegimeBacktest] Error: {data_path} not found")
        print("[RunRegimeBacktest] Please run scripts/download_btc_5m.py first")
        return
    
    df = pd.read_csv(data_path)
    print(f"[RunRegimeBacktest] Loaded {len(df)} rows")
    
    # Create regime engine
    engine = RegimeModelEngine()
    
    # Run backtest
    backtester = AIBacktester(df, engine, initial_balance=10000)
    metrics = backtester.run()
    
    # Print results
    print_metrics(metrics)


if __name__ == '__main__':
    run_regime_backtest()
