"""
Run AI backtest with ensemble engine.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ensemble_engine import EnsembleEngine
from ai_backtest.engine import AIBacktester
from ai_backtest.metrics import print_metrics


def run_backtest():
    """
    Run backtest using ensemble engine.
    """
    print("[RunBacktest] Starting ensemble backtest...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[RunBacktest] Error: {data_path} not found")
        print("[RunBacktest] Please run scripts/download_btc_5m.py first")
        return
    
    df = pd.read_csv(data_path)
    print(f"[RunBacktest] Loaded {len(df)} rows")
    
    # Create engine
    engine = EnsembleEngine()
    
    # Run backtest
    backtester = AIBacktester(df, engine, initial_balance=10000)
    metrics = backtester.run()
    
    # Print results
    print_metrics(metrics)


if __name__ == '__main__':
    run_backtest()
