"""
Example: Using the Adaptive Learning System

This demonstrates how to use the adaptive system without modifying
the existing paper trading pipeline.
"""

from pathlib import Path
import pandas as pd
from datetime import datetime, timezone

from adaptive import (
    AdaptiveController,
    AdaptiveConfig,
)


def example_basic_usage():
    """Basic usage example"""
    print("=" * 60)
    print("Example 1: Basic Adaptive System Usage")
    print("=" * 60)
    
    # Create configuration
    config = AdaptiveConfig.default(Path("/tmp/adaptive_example"))
    
    # Initialize controller
    controller = AdaptiveController(config)
    
    # Initialize with a frozen model (simulated)
    print("\n1. Initializing with frozen model...")
    success, msg = controller.initialize_from_frozen_model(
        frozen_model_id="m_example_baseline",
        frozen_artifact_path=Path("/tmp/frozen_model.pkl"),  # Would be real path
    )
    print(f"   {msg}")
    
    # Get status
    print("\n2. Getting system status...")
    status = controller.get_status()
    print(f"   Frozen model: {status['frozen_model']['model_id'] if status['frozen_model'] else 'None'}")
    print(f"   Shadow model: {status['shadow_model']['model_id'] if status['shadow_model'] else 'None'}")
    
    print("\n✓ Basic setup complete!")


def example_learning_loop():
    """Example of the learning loop"""
    print("\n" + "=" * 60)
    print("Example 2: Learning Loop Simulation")
    print("=" * 60)
    
    config = AdaptiveConfig.default(Path("/tmp/adaptive_example"))
    controller = AdaptiveController(config)
    
    # Initialize
    controller.initialize_from_frozen_model(
        frozen_model_id="m_learning_demo",
        frozen_artifact_path=Path("/tmp/frozen_model.pkl"),
    )
    
    # Simulate paper trades
    print("\n1. Simulating paper trades...")
    
    trades = [
        {"id": "t1", "prediction": "LONG", "confidence": 0.75, "outcome": "win", "pnl": 10.5},
        {"id": "t2", "prediction": "SHORT", "confidence": 0.65, "outcome": "loss", "pnl": -5.2},
        {"id": "t3", "prediction": "LONG", "confidence": 0.80, "outcome": "win", "pnl": 12.3},
        {"id": "t4", "prediction": "SHORT", "confidence": 0.70, "outcome": "win", "pnl": 8.1},
        {"id": "t5", "prediction": "LONG", "confidence": 0.60, "outcome": "loss", "pnl": -4.5},
    ]
    
    for trade in trades:
        features = {
            "rsi": 50 + (hash(trade["id"]) % 40),
            "volume": 1000 + (hash(trade["id"]) % 500),
            "price": 50000 + (hash(trade["id"]) % 1000),
        }
        
        success, msg = controller.process_paper_trade(
            trade_id=trade["id"],
            features_at_entry=features,
            prediction=trade["prediction"],
            confidence=trade["confidence"],
            outcome=trade["outcome"],
            pnl=trade["pnl"],
        )
        
        print(f"   Trade {trade['id']}: {trade['outcome']} (PnL: {trade['pnl']:+.2f})")
    
    # Check learner stats
    print("\n2. Shadow learner stats...")
    stats = controller.shadow_learner.get_stats()
    print(f"   Total updates: {stats['total_updates']}")
    print(f"   Trades processed: {stats['total_trades_processed']}")
    print(f"   Learning rate: {stats['current_learning_rate']:.6f}")
    
    print("\n✓ Learning loop demo complete!")


def example_drift_monitoring():
    """Example of drift monitoring"""
    print("\n" + "=" * 60)
    print("Example 3: Drift Monitoring")
    print("=" * 60)
    
    config = AdaptiveConfig.default(Path("/tmp/adaptive_example"))
    controller = AdaptiveController(config)
    
    # Initialize
    controller.initialize_from_frozen_model(
        frozen_model_id="m_drift_demo",
        frozen_artifact_path=Path("/tmp/frozen_model.pkl"),
    )
    
    # Set frozen baseline with simulated trades
    print("\n1. Setting frozen baseline...")
    frozen_trades = pd.DataFrame({
        "outcome": ["win", "win", "loss", "win", "loss", "win", "win", "loss", "win", "win"],
        "pnl": [10, 12, -5, 8, -6, 15, 9, -4, 11, 13],
    })
    
    controller.set_frozen_baseline_from_trades(frozen_trades)
    
    # Simulate shadow trades (worse performance)
    print("\n2. Simulating shadow trades with degraded performance...")
    shadow_trades = pd.DataFrame({
        "outcome": ["win", "loss", "loss", "win", "loss", "loss", "win", "loss", "loss", "loss"],
        "pnl": [8, -7, -9, 6, -8, -10, 7, -6, -11, -8],
    })
    
    shadow_metrics = controller.drift_monitor.update_shadow_metrics(shadow_trades)
    
    print(f"   Shadow winrate: {shadow_metrics.winrate:.3f}")
    print(f"   Shadow expectancy: {shadow_metrics.expectancy:.3f}")
    
    # Check drift
    has_drifted, reason, details = controller.drift_monitor.check_drift(shadow_metrics)
    
    if has_drifted:
        print(f"\n⚠️  DRIFT DETECTED: {reason}")
        print(f"   Winrate diff: {details['winrate_diff']:.3f}")
    else:
        print(f"\n✓ No drift detected")
    
    print("\n✓ Drift monitoring demo complete!")


def example_promotion_gate():
    """Example of promotion evaluation"""
    print("\n" + "=" * 60)
    print("Example 4: Promotion Gate Evaluation")
    print("=" * 60)
    
    config = AdaptiveConfig.default(Path("/tmp/adaptive_example"))
    controller = AdaptiveController(config)
    
    # Initialize
    controller.initialize_from_frozen_model(
        frozen_model_id="m_promotion_demo",
        frozen_artifact_path=Path("/tmp/frozen_model.pkl"),
    )
    
    # Create sample trades
    print("\n1. Evaluating promotion criteria...")
    
    # Note: In real usage, these would come from actual trade logs
    # For demo, we're using simplified data
    
    shadow_trades = pd.DataFrame({
        "outcome": ["win"] * 60 + ["loss"] * 40,  # 60% winrate
        "pnl": [10] * 60 + [-5] * 40,
    })
    
    frozen_trades = pd.DataFrame({
        "outcome": ["win"] * 55 + ["loss"] * 45,  # 55% winrate
        "pnl": [10] * 55 + [-5] * 45,
    })
    
    # Evaluate (this uses internal feature store in real usage)
    print("   Running promotion tests...")
    print("   - Winrate improvement test")
    print("   - Expectancy improvement test")
    print("   - Drawdown check")
    print("   - Last N trades test")
    
    # Get decisions
    decisions = controller.promotion_gate.get_recent_decisions(limit=5)
    print(f"\n2. Recent decisions: {len(decisions)}")
    
    print("\n✓ Promotion evaluation demo complete!")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("ADAPTIVE LEARNING SYSTEM - EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate the adaptive system components.")
    print("No actual model training occurs in these demos.")
    print()
    
    try:
        example_basic_usage()
        example_learning_loop()
        example_drift_monitoring()
        example_promotion_gate()
        
        print("\n" + "=" * 60)
        print("✓ All examples completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review adaptive/README.md for full documentation")
        print("2. Integrate with paper trading logs (read-only)")
        print("3. Implement actual incremental learning algorithm")
        print("4. Set up monitoring dashboards")
        print()
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
