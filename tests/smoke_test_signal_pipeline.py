"""
Smoke test for AI signal pipeline.

This script:
1. Trains a model on data/candles.csv
2. Runs DecisionEngine on the same data to produce signals
3. Validates the integration with risk_filter
"""

import sys
import pandas as pd
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from training.train_model import train
from core.decision_engine import DecisionEngine
from core.risk_filter import risk_filter


def smoke_test():
    print("=" * 60)
    print("AI Signal Pipeline Smoke Test")
    print("=" * 60)
    
    # Step 1: Train the model
    print("\n[Step 1] Training model on data/candles.csv...")
    try:
        train("data/candles.csv")
        print("✓ Model trained successfully")
    except Exception as e:
        print(f"✗ Training failed: {e}")
        return False
    
    # Step 2: Load and predict
    print("\n[Step 2] Loading DecisionEngine and making predictions...")
    try:
        engine = DecisionEngine("models/signal_model.pkl")
        df = pd.read_csv("data/candles.csv")
        
        # Test on last window
        signal, prob = engine.predict(df)
        print(f"✓ DecisionEngine prediction: {signal} (confidence: {prob:.3f})")
    except Exception as e:
        print(f"✗ Prediction failed: {e}")
        return False
    
    # Step 3: Test risk filter
    print("\n[Step 3] Testing risk_filter integration...")
    try:
        volatility = df["close"].pct_change().std()
        filtered_signal = risk_filter(signal, prob, volatility)
        print(f"✓ Risk filter applied: {signal} -> {filtered_signal} (vol: {volatility:.4f})")
    except Exception as e:
        print(f"✗ Risk filter failed: {e}")
        return False
    
    # Step 4: Test backtest-style loop
    print("\n[Step 4] Testing backtest-style prediction loop...")
    try:
        signals_count = {"BUY": 0, "SELL": 0, "HOLD": 0}
        
        for i in range(250, min(260, len(df))):
            window = df.iloc[:i]
            s, p = engine.predict(window)
            signals_count[s] = signals_count.get(s, 0) + 1
        
        print(f"✓ Backtest loop completed: {signals_count}")
    except Exception as e:
        print(f"✗ Backtest loop failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✓ All smoke tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = smoke_test()
    sys.exit(0 if success else 1)
