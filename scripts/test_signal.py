"""
Test Signal Generator
Tests signal generation from ensemble engine
"""
import pandas as pd
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from core.ensemble_engine import EnsembleEngine


def test_signal():
    """Test signal generation"""
    
    print("Loading data...")
    df = pd.read_csv('data/btcusdt_5m.csv')
    
    print("Building features...")
    builder = FeatureBuilder()
    df = builder.build(df)
    
    # Drop NaN rows
    df = df.dropna()
    
    print("Initializing ensemble engine...")
    engine = EnsembleEngine()
    
    print("\nGenerating signal from last data point...")
    signal, confidence = engine.signal(df)
    
    print(f"Signal: {signal}")
    print(f"Confidence: {confidence:.4f}")
    
    print("\nTesting on last 10 data points:")
    for i in range(10):
        subset = df.iloc[:-(10-i)]
        if len(subset) > 100:  # Need enough data for features
            signal, confidence = engine.signal(subset)
            timestamp = df.iloc[-(10-i)]['timestamp'] if 'timestamp' in df.columns else f"Row {len(subset)}"
            print(f"{timestamp}: {signal:5s} (conf={confidence:.4f})")


if __name__ == '__main__':
    test_signal()
