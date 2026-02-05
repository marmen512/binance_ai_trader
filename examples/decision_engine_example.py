#!/usr/bin/env python
"""
Example script demonstrating the decision engine pipeline.

This script shows how to:
1. Train a signal model from OHLCV data
2. Load the decision engine
3. Make trading decisions from live data
"""
import sys
from pathlib import Path

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.features import compute_ohlcv_features, last_row_features
from app.core.decision_engine import get_engine


def example_train_model():
    """Example: Train a multi-class signal model."""
    print("=" * 70)
    print("Example 1: Training a Signal Model")
    print("=" * 70)
    
    print("\nCommand to train a multi-class model:")
    print("  python training/train_signal_model.py \\")
    print("    --candles data/bnb_1m.csv \\")
    print("    --out models/signal_model.pkl \\")
    print("    --horizon 1 \\")
    print("    --threshold 0.004 \\")
    print("    --multiclass")
    
    print("\nCommand to train a binary model:")
    print("  python training/train_signal_model.py \\")
    print("    --candles data/bnb_1m.csv \\")
    print("    --out models/signal_model_binary.pkl \\")
    print("    --horizon 1 \\")
    print("    --threshold 0.004 \\")
    print("    --binary")


def example_feature_computation():
    """Example: Compute features from OHLCV data."""
    print("\n" + "=" * 70)
    print("Example 2: Feature Computation")
    print("=" * 70)
    
    # Create sample data
    df = pd.DataFrame({
        'open': [100.0, 101.0, 102.0, 103.0, 104.0],
        'high': [101.0, 102.0, 103.0, 104.0, 105.0],
        'low': [99.0, 100.0, 101.0, 102.0, 103.0],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'volume': [1000.0, 1100.0, 1200.0, 1300.0, 1400.0]
    })
    
    print("\nOriginal DataFrame:")
    print(df)
    
    # Compute features
    df_features = compute_ohlcv_features(df)
    
    print(f"\nComputed {df_features.shape[1]} total columns including:")
    print("  - return, log_return")
    print("  - high_low_spread, open_close_spread, candle_body")
    print("  - atr_14, atr_14_norm")
    print("  - ema_9, ema_21, ema_50")
    print("  - ema_9_21_cross, ema_9_50_cross")
    print("  - rsi_14")
    print("  - macd, macd_signal, macd_hist, macd_norm")
    print("  - volatility_10, volatility_30")
    print("  - volume_spike, volume_change")
    
    # Extract features from last row
    features = last_row_features(df_features)
    
    print(f"\nExtracted {len(features)} features from last row:")
    for key, value in list(features.items())[:5]:
        print(f"  {key}: {value:.6f}")
    print("  ...")


def example_decision_engine():
    """Example: Use decision engine to make trading decisions."""
    print("\n" + "=" * 70)
    print("Example 3: Decision Engine")
    print("=" * 70)
    
    # Load historical data
    df = pd.read_csv('data/bnb_1m.csv')
    print(f"\nLoaded {len(df)} candles from data/bnb_1m.csv")
    
    # Compute features
    df = compute_ohlcv_features(df)
    features = last_row_features(df)
    print(f"Extracted features from last candle")
    
    # Load decision engine
    try:
        engine = get_engine('models/signal_model.pkl')
        print("Loaded decision engine from models/signal_model.pkl")
    except FileNotFoundError:
        print("\n⚠ Model not found. Please train a model first:")
        print("  python training/train_signal_model.py --candles data/bnb_1m.csv --out models/signal_model.pkl")
        return
    
    # Get model score
    score = engine.predict_score(features)
    print(f"\nModel score: {score:.4f}")
    
    # Apply risk filters - Conservative
    print("\n[Conservative Strategy]")
    decision_conservative = engine.apply_risk_filters(
        features,
        min_confidence=0.7,
        volatility_max=0.02,
        max_spread_pct=0.005
    )
    print(f"  Action: {decision_conservative.action}")
    print(f"  Confidence: {decision_conservative.confidence:.4f}")
    print(f"  Reasons: {', '.join(decision_conservative.reasons)}")
    
    # Apply risk filters - Moderate
    print("\n[Moderate Strategy]")
    decision_moderate = engine.apply_risk_filters(
        features,
        min_confidence=0.5,
        volatility_max=0.05,
        max_spread_pct=0.01
    )
    print(f"  Action: {decision_moderate.action}")
    print(f"  Confidence: {decision_moderate.confidence:.4f}")
    print(f"  Reasons: {', '.join(decision_moderate.reasons)}")
    
    # Apply risk filters - Aggressive
    print("\n[Aggressive Strategy]")
    decision_aggressive = engine.apply_risk_filters(
        features,
        min_confidence=0.3,
        volatility_max=0.1,
        max_spread_pct=0.02
    )
    print(f"  Action: {decision_aggressive.action}")
    print(f"  Confidence: {decision_aggressive.confidence:.4f}")
    print(f"  Reasons: {', '.join(decision_aggressive.reasons)}")


def example_streaming_decisions():
    """Example: Generate decisions for streaming data."""
    print("\n" + "=" * 70)
    print("Example 4: Streaming Decisions")
    print("=" * 70)
    
    # Load data
    df = pd.read_csv('data/bnb_1m.csv')
    df = compute_ohlcv_features(df)
    
    try:
        engine = get_engine('models/signal_model.pkl')
    except FileNotFoundError:
        print("\n⚠ Model not found. Skipping streaming example.")
        return
    
    print("\nGenerating decisions for last 5 candles:")
    print(f"{'Candle':<8} {'Close':<10} {'Action':<8} {'Confidence':<12} {'Reasons'}")
    print("-" * 70)
    
    # Process last 5 candles
    for i in range(len(df) - 5, len(df)):
        df_slice = df.iloc[:i+1]
        features = last_row_features(df_slice)
        decision = engine.apply_risk_filters(features, min_confidence=0.5)
        
        close_price = df.iloc[i]['close']
        reasons_str = '; '.join(decision.reasons)[:30] + "..."
        
        print(f"{i:<8} {close_price:<10.2f} {decision.action:<8} {decision.confidence:<12.4f} {reasons_str}")


def main():
    """Run all examples."""
    example_train_model()
    example_feature_computation()
    example_decision_engine()
    example_streaming_decisions()
    
    print("\n" + "=" * 70)
    print("Examples Complete!")
    print("=" * 70)
    print("\nFor more information, see:")
    print("  - app/core/features.py - Feature engineering")
    print("  - app/core/decision_engine.py - Decision engine")
    print("  - training/train_signal_model.py - Model training")


if __name__ == '__main__':
    main()
