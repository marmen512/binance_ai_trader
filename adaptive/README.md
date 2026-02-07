# Adaptive AI Trading System

**Status:** Shadow Learning Skeleton - Phase 1-6 Complete

## 🎯 Purpose

Isolated adaptive learning system that enables shadow model to learn from paper trades WITHOUT modifying the existing paper trading v1 pipeline.

## 🔒 Critical Constraints

This system:
- ✅ **DOES NOT** modify existing paper trading v1 pipeline
- ✅ **DOES NOT** change frozen model logic
- ✅ **DOES NOT** touch execution_safety gates
- ✅ **DOES NOT** enable online learning in production path
- ✅ **IS** completely isolated under `adaptive/` directory
- ✅ **IS** a READ-ONLY consumer of paper trading artifacts

## 🏗️ Architecture

### Dual Model System

```
┌─────────────┐                    ┌──────────────┐
│   FROZEN    │ ◄─────────────────┤  Production  │
│   (trades)  │   trades          │   Pipeline   │
└─────────────┘                    └──────────────┘
       │                                   │
       │ baseline                          │ paper logs
       │                                   ▼
       │                          ┌──────────────┐
       │                          │    Feature   │
       │                          │     Store    │
       │                          └──────────────┘
       │                                   │
       │                                   ▼
       ▼                          ┌──────────────┐
┌─────────────┐                  │    Shadow    │
│    Drift    │ ◄─────────────── │   Learner    │
│   Monitor   │   metrics        │ (learns only)│
└─────────────┘                  └──────────────┘
       │                                   │
       │ drift check                       │ metrics
       ▼                                   ▼
┌─────────────┐                  ┌──────────────┐
│  Promotion  │ ◄────────────────┤  Quality     │
│    Gate     │   evaluation     │    Tests     │
└─────────────┘                  └──────────────┘
       │
       │ ONLY if all tests pass
       ▼
   promote shadow → new frozen
```

### Learning Loop

```
Paper Trade Opens
       ↓
snapshot features_at_entry
       ↓
Trade Closes
       ↓
outcome label (win/loss/breakeven)
       ↓
send to Shadow Trainer
       ↓
learn_one() [incremental learning]
       ↓
log metrics (winrate, expectancy)
       ↓
check drift → auto pause if degraded
       ↓
evaluate promotion (NOT automatic)
```

## 📁 Directory Structure

```
adaptive/
├── __init__.py                    # Main exports
├── adaptive_controller.py         # Orchestrator
├── cli.py                         # CLI commands
├── dual_model/
│   ├── __init__.py
│   └── dual_model_manager.py     # Frozen + Shadow management
├── shadow_learner/
│   ├── __init__.py
│   └── shadow_learner.py         # Online learning loop
├── drift_monitor/
│   ├── __init__.py
│   └── drift_monitor.py          # Quality control
├── promotion_gate/
│   ├── __init__.py
│   └── promotion_gate.py         # Promotion decisions
└── feature_store/
    ├── __init__.py
    └── feature_store.py          # Feature logging

adaptive_logs/                     # Generated at runtime
├── features/
│   ├── features_log.jsonl        # All trade features
│   └── features_snapshot.parquet # Periodic snapshots
├── metrics/
│   ├── shadow_metrics.json       # Shadow model metrics
│   ├── frozen_metrics.json       # Frozen baseline
│   └── drift_alerts.jsonl        # Drift detection
└── decisions/
    └── promotion_decisions.jsonl # Promotion evaluations
```

## 🚀 Usage

### Initialize System

```bash
python -m adaptive.cli init \
  --frozen-model-id m_baseline \
  --frozen-artifact-path model_registry/models/frozen.pkl
```

### Check Status

```bash
python -m adaptive.cli status
```

### Evaluate Promotion

```bash
python -m adaptive.cli evaluate
```

### Promote Shadow (if approved)

```bash
python -m adaptive.cli promote
```

### Programmatic Usage

```python
from adaptive import AdaptiveController, AdaptiveConfig
from pathlib import Path

# Initialize
config = AdaptiveConfig.default(Path("ai_data/adaptive"))
controller = AdaptiveController(config)

# Set up frozen model
controller.initialize_from_frozen_model(
    frozen_model_id="m_baseline",
    frozen_artifact_path=Path("model_registry/models/frozen.pkl"),
)

# Process paper trade (called by paper trading logger)
controller.process_paper_trade(
    trade_id="trade_123",
    features_at_entry={"rsi": 45.2, "volume": 1000},
    prediction="LONG",
    confidence=0.75,
    outcome="win",
    pnl=10.5,
)

# Check status
status = controller.get_status()

# Evaluate promotion
should_promote, reason, decision = controller.evaluate_promotion()

if should_promote:
    success, msg = controller.promote_shadow_to_frozen()
```

## 🛡️ Safety Features

### Drift Monitor

- **Rolling window metrics**: winrate, expectancy
- **Auto-pause**: Pauses learning if shadow worse than frozen
- **Alerts**: Logs all drift detections

### Rate Limiting

- Max updates per hour (default: 10)
- Min trades before update (default: 10)
- Learning rate decay (default: 0.99)

### Promotion Gate

**NOT automatic**. Shadow promoted ONLY if passes:

1. ✅ Winrate improvement ≥ 2%
2. ✅ Expectancy improvement ≥ 5%
3. ✅ Max drawdown ≤ 20%
4. ✅ Last N trades test (default: 50)
5. ✅ Walk-forward test (optional)
6. ✅ Paper replay test (optional)

## 📊 Logs

### Required Logs

All logs stored under `adaptive_logs/`:

1. **trade_features.parquet**: All trade features
2. **trade_outcomes.parquet**: Trade outcomes with PnL
3. **shadow_metrics.json**: Shadow model performance
4. **model_versions.json**: Model version history

### Metrics Tracked

- **Winrate**: Rolling window winrate
- **Expectancy**: Expected value per trade
- **Average PnL**: Mean profit/loss
- **Max Drawdown**: Maximum equity drawdown
- **Sharpe Ratio**: Risk-adjusted returns

## 🔄 Integration with Paper Trading

### Read-Only Integration

The adaptive system reads from paper trading logs but never modifies them:

```python
# In paper trading code (example - NOT implemented yet)
from adaptive import AdaptiveController, AdaptiveConfig

# Initialize adaptive controller (one-time)
adaptive = AdaptiveController(AdaptiveConfig.default(Path("ai_data/adaptive")))

# After each paper trade completes
adaptive.process_paper_trade(
    trade_id=trade_id,
    features_at_entry=features_dict,
    prediction=prediction,
    confidence=confidence,
    outcome=outcome,  # "win", "loss", or "breakeven"
    pnl=pnl,
)
```

## 🎓 Learning Algorithm

Currently uses a simplified incremental learning approach. For production:

1. **river library**: For true online machine learning
2. **Incremental XGBoost**: For gradient boosting online
3. **Online Random Forest**: For ensemble methods

## 📈 Roadmap

### Phase 1-6: ✅ Complete
- [x] Dual model architecture
- [x] Feature store
- [x] Shadow learner (skeleton)
- [x] Drift monitor
- [x] Promotion gate
- [x] Model registry

### Phase 7-12: Future
- [ ] Continuous walk-forward testing
- [ ] Leaderboard signal integration (optional)
- [ ] Advanced regime detection
- [ ] Feature importance tracking
- [ ] Evaluation dashboard
- [ ] Automated backtesting integration

## ⚠️ Important Notes

1. **Not Production Ready**: This is a skeleton implementation
2. **No Actual Training**: `learn_one()` is currently a placeholder
3. **Simplified Metrics**: Real implementation needs more robust statistics
4. **No Model Persistence**: Shadow model updates not yet saved to disk
5. **Manual Integration**: Requires manual hookup to paper trading logs

## 🔍 Monitoring

Check these files regularly:

- `adaptive_logs/metrics/drift_alerts.jsonl` - Drift warnings
- `adaptive_logs/decisions/promotion_decisions.jsonl` - Promotion history
- `adaptive_logs/features/features_log.jsonl` - Trade features

## 🤝 Contributing

When extending this system:

1. ✅ Keep all code under `adaptive/`
2. ✅ Never import from execution/trading modules
3. ✅ Only read paper trading artifacts
4. ✅ Maintain dual model separation
5. ✅ Test promotion criteria thoroughly

## 📝 License

Same as parent project.
