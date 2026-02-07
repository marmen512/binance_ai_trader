# Adaptive System - Quick Start

Get the adaptive learning system running in 5 minutes.

## 1. Test Installation

```bash
cd binance_ai_trader

# Test imports
python3 -c "from adaptive import AdaptiveController; print('✅ Installed')"

# Run examples
PYTHONPATH=. python3 adaptive/examples.py
```

## 2. Initialize

```python
from adaptive import AdaptiveController, AdaptiveConfig
from pathlib import Path

# Create controller
config = AdaptiveConfig.default(Path("ai_data/adaptive"))
controller = AdaptiveController(config)

# Initialize with your frozen model
controller.initialize_from_frozen_model(
    frozen_model_id="m_baseline",
    frozen_artifact_path=Path("model_registry/models/frozen.pkl"),
)

print("✅ Adaptive system initialized")
```

## 3. Process Paper Trades

```python
# After a paper trade completes
controller.process_paper_trade(
    trade_id="trade_001",
    features_at_entry={
        "rsi": 45.2,
        "volume": 1000,
        "price": 50000,
    },
    prediction="LONG",
    confidence=0.75,
    outcome="win",     # "win", "loss", or "breakeven"
    pnl=10.5,
)
```

## 4. Monitor

```bash
# Check status
python3 -m adaptive.cli status

# Watch drift alerts
tail -f ai_data/adaptive/adaptive_logs/metrics/drift_alerts.jsonl

# Watch features
tail -f ai_data/adaptive/adaptive_logs/features/features_log.jsonl
```

## 5. Evaluate Promotion

```python
# Check if shadow should be promoted
should_promote, reason, decision = controller.evaluate_promotion()

if should_promote:
    print(f"✅ Promotion approved: {reason}")
    success, msg = controller.promote_shadow_to_frozen()
    print(msg)
else:
    print(f"❌ Promotion rejected: {reason}")
```

## Next Steps

- Read `README.md` for full documentation
- Read `INTEGRATION_GUIDE.md` for integration options
- Read `IMPLEMENTATION_SUMMARY.md` for technical details

## Key Commands

```bash
# Status
python3 -m adaptive.cli status

# Initialize
python3 -m adaptive.cli init

# Evaluate promotion
python3 -m adaptive.cli evaluate

# Promote (if approved)
python3 -m adaptive.cli promote
```

## Safety Notes

- ✅ Shadow model NEVER trades directly
- ✅ Frozen model is read-only during paper trading
- ✅ Auto-pauses if shadow performance degrades
- ✅ Promotion requires passing all tests (NOT automatic)
- ✅ Full rollback capability

## Need Help?

1. Check `README.md` for comprehensive guide
2. Review `examples.py` for usage patterns
3. Read `INTEGRATION_GUIDE.md` for integration strategies

**Status:** Ready for integration testing!
