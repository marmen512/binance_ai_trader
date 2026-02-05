"""
Test signal generation from engines.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ensemble_engine import EnsembleEngine
from core.regime_model_engine import RegimeModelEngine
from core.adaptive_engine import AdaptiveEngine


def test_signals():
    """
    Test signal generation from different engines.
    """
    print("[TestSignal] Testing signal generation...")
    
    # Load data
    data_path = "data/btcusdt_5m.csv"
    if not os.path.exists(data_path):
        print(f"[TestSignal] Error: {data_path} not found")
        print("[TestSignal] Please run scripts/download_btc_5m.py first")
        return
    
    df = pd.read_csv(data_path)
    print(f"[TestSignal] Loaded {len(df)} rows")
    
    # Use last 100 rows for testing
    test_df = df.tail(100).copy()
    
    # Test ensemble engine
    print("\n[TestSignal] Testing EnsembleEngine...")
    try:
        ensemble = EnsembleEngine()
        signal, prob = ensemble.signal(test_df)
        print(f"[TestSignal] Ensemble signal: {signal} (confidence: {prob:.3f})")
    except Exception as e:
        print(f"[TestSignal] Ensemble error: {e}")
    
    # Test regime model engine
    print("\n[TestSignal] Testing RegimeModelEngine...")
    try:
        regime_engine = RegimeModelEngine()
        signal, prob = regime_engine.signal(test_df)
        print(f"[TestSignal] Regime signal: {signal} (confidence: {prob:.3f})")
    except Exception as e:
        print(f"[TestSignal] Regime error: {e}")
    
    # Test adaptive engine
    print("\n[TestSignal] Testing AdaptiveEngine...")
    try:
        adaptive_engine = AdaptiveEngine()
        signal, prob = adaptive_engine.signal(test_df)
        print(f"[TestSignal] Adaptive signal: {signal} (confidence: {prob:.3f})")
    except Exception as e:
        print(f"[TestSignal] Adaptive error: {e}")


if __name__ == '__main__':
    test_signals()
