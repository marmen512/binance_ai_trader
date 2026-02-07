# Adaptive AI Learning + Copy-Trader Validation + Hybrid Decision Layer

## Overview

This implementation adds a **fully isolated** adaptive learning system with copy-trader validation and hybrid decision-making capabilities to the Binance AI Trader, while maintaining complete backward compatibility and respecting all architectural constraints.

## 🔒 Hard Constraints Respected

The implementation **DOES NOT MODIFY**:
- ❌ `execution/*` - Execution logic unchanged
- ❌ `execution_safety/*` - Safety checks preserved
- ❌ `paper_gate/*` - Paper trading pipeline intact
- ❌ Existing paper v1 pipeline
- ❌ Frozen model inference path
- ❌ Risk gates and kill switches
- ❌ Current strategy logic

**Key Safety Features:**
- ✅ All new systems behind config flags (disabled by default)
- ✅ Event-driven architecture prevents direct coupling
- ✅ Shadow learning never affects production models
- ✅ No automatic retraining of production models
- ✅ Complete isolation from live execution

## 📦 Architecture

### Module Structure

```
binance_ai_trader/
├── adaptive/              # Adaptive learning (isolated)
│   ├── shadow_model.py      # Shadow model for safe learning
│   ├── online_trainer.py    # Training orchestration
│   ├── feature_logger.py    # Feature versioning
│   ├── drift_monitor.py     # Drift detection (wrapper)
│   ├── model_registry.py    # Model management (wrapper)
│   ├── promotion_gate.py    # Model promotion validation
│   ├── pipeline.py          # Complete workflow
│   └── event_hooks.py       # Legacy event system
│
├── events/                # Event system (NEW)
│   └── trade_events.py      # Publish-subscribe event bus
│
├── leaderboard/           # Copy-trader analysis (NEW)
│   ├── fetcher.py           # Fetch top traders
│   ├── positions.py         # Read trader positions
│   ├── analyzer.py          # Entry quality analysis
│   └── validator.py         # Confidence validation
│
├── decision/              # Hybrid decision layer (NEW)
│   └── hybrid_engine.py     # Signal fusion engine
│
└── tests/                 # Comprehensive tests
    ├── adaptive/
    ├── events/
    ├── leaderboard/
    ├── hybrid/
    └── safety/
```

## 🚀 Features

### 1. Adaptive Shadow Learning

**Purpose:** Learn from paper trades without affecting production models.

**Key Components:**
- **Shadow Model:** Clones frozen model for safe learning
- **Online Trainer:** Orchestrates training with promotion gates
- **Feature Logger:** Tracks features with schema versioning
- **Drift Monitor:** Detects performance degradation
- **Promotion Gate:** Validates before promoting to production

**Workflow:**
```
Paper Trade Closes
    ↓
Feature Snapshot (with versioning)
    ↓
Outcome Label
    ↓
Shadow Model Learn
    ↓
Drift Monitor Check
    ↓
Promotion Gate Validation
    ↓
(Optional) Promote to Production
```

**Usage:**
```python
from adaptive.pipeline import ShadowModelPipeline

# Initialize
pipeline = ShadowModelPipeline()
pipeline.start_training()

# Train on new data
pipeline.train_on_new_data(features, label)
pipeline.save_progress()

# Evaluate for promotion
metrics = {"winrate": 0.58, "expectancy": 0.65}
if pipeline.evaluate_for_promotion(metrics):
    pipeline.promote_shadow_to_production()
```

### 2. Event System

**Purpose:** Decouple execution from logging/analytics via events.

**Key Components:**
- **TradeEventBus:** Central event dispatcher
- **TradeEventListener:** Base class for listeners
- **Event Types:** trade_opened, trade_closed, position_changed, etc.

**Benefits:**
- ✅ Execution never calls adaptive code directly
- ✅ Listener errors don't break execution
- ✅ Easy to add new listeners

**Usage:**
```python
from events import get_event_bus, TradeEventListener

# Create custom listener
class MyListener(TradeEventListener):
    def on_trade_closed(self, event):
        print(f"Trade closed: {event.data}")

# Subscribe
bus = get_event_bus()
bus.subscribe(MyListener())

# Emit events (from execution)
bus.emit_trade_closed(
    symbol="BTCUSDT",
    data={"pnl": 100.0, "outcome": "win"}
)
```

### 3. Copy-Trader Validation

**Purpose:** Validate copy-trader signals before acting (NO direct copying).

**Key Components:**
- **LeaderboardFetcher:** Fetch top traders
- **PositionReader:** Read trader positions
- **EntryAnalyzer:** Analyze entry quality
- **ConfidenceValidator:** Validate replication confidence

**Workflow:**
```
Fetch Top Traders
    ↓
Read Open Positions
    ↓
Rebuild Features at Entry
    ↓
Run Model Validation
    ↓
Compute Confidence Score
    ↓
Emit Validated Signal (NOT execution)
```

**Usage:**
```python
from leaderboard import LeaderboardFetcher, ConfidenceValidator

# Fetch traders
fetcher = LeaderboardFetcher()
traders = fetcher.fetch_top_traders(min_winrate=0.55)

# Validate signal
validator = ConfidenceValidator()
result = validator.validate(
    trader_metrics={"winrate": 0.6, "roi": 0.15},
    entry_analysis={"entry_quality_score": 0.75}
)

if result.recommendation == "REPLICATE":
    # Emit signal (do NOT execute trade here)
    pass
```

### 4. Hybrid Decision Layer

**Purpose:** Fuse signals from multiple sources using confidence weighting.

**Key Components:**
- **HybridDecisionEngine:** Signal fusion engine
- **Signal Sources:** own_model, copy_validated, regime_model
- **Confidence Weighting:** Configurable weights
- **Conflict Resolution:** Voting and threshold gating

**Workflow:**
```
Own Model Signal
Copy-Validated Signal    →  Weighted Fusion  →  Final Decision
Regime Model Signal
```

**Usage:**
```python
from decision import HybridDecisionEngine, Signal, SignalSource

# Initialize engine
engine = HybridDecisionEngine(
    own_model_weight=0.4,
    copy_weight=0.3,
    regime_weight=0.3
)

# Create signals
own_signal = Signal(
    source=SignalSource.OWN_MODEL,
    direction="long",
    confidence=0.7,
    strength=0.8
)

copy_signal = Signal(
    source=SignalSource.COPY_VALIDATED,
    direction="long",
    confidence=0.6,
    strength=0.7
)

# Make decision
decision = engine.decide(
    own_model_signal=own_signal,
    copy_signal=copy_signal
)

print(f"Decision: {decision.direction} (conf={decision.confidence:.2f})")
print(f"Reasoning: {decision.reasoning}")
```

## ⚙️ Configuration

All new features are controlled via `config/config.yaml`:

```yaml
# Adaptive learning configuration
adaptive:
  enabled: false              # Master switch (DISABLED by default)
  shadow_learning: true       # Enable shadow learning
  drift_guard: true           # Enable drift detection
  promotion_gate:
    min_winrate: 0.52
    min_expectancy: 0.0
    min_trades: 100
    max_loss_streak: 5

# Leaderboard/copy-trader configuration
leaderboard:
  enabled: false              # Master switch (DISABLED by default)
  validation_required: true   # Require validation before signals
  min_trader_winrate: 0.55
  min_trader_roi: 0.10

# Hybrid decision layer configuration
hybrid:
  enabled: false              # Master switch (DISABLED by default)
  own_model_weight: 0.4
  copy_weight: 0.3
  regime_weight: 0.3
  min_confidence_threshold: 0.6

# Event system configuration
events:
  enabled: true               # Enable event bus
  log_events: true
```

## 🧪 Testing

### Running Tests

```bash
# Run all new tests
pytest tests/adaptive/ tests/events/ tests/leaderboard/ tests/hybrid/ -v

# Run adaptive tests only
pytest tests/adaptive/test_adaptive.py -v

# Run event system tests
pytest tests/events/test_events.py -v

# Run hybrid engine tests
pytest tests/hybrid/test_hybrid.py -v

# Run safety verification tests
pytest tests/safety/test_final_verification.py -v

# Run execution hardening verification
pytest tests/safety/test_execution_hardening.py -v
```

### Test Coverage

- ✅ **adaptive:** Shadow model, promotion gate, drift monitor (10+ tests)
- ✅ **events:** Event bus, listeners, error isolation (8+ tests)
- ✅ **hybrid:** Signal fusion, weighting, conflict resolution (8+ tests)
- ✅ **leaderboard:** Fetcher, validator, confidence scoring (6+ tests)
- ✅ **safety:** Execution hardening verification (10+ tests)
- ✅ **safety:** Final constraints verification (15+ tests)

## 📊 Data Flow

### Shadow Learning Flow

```
Paper Trade (from paper_gate)
    ↓
Event: trade_closed
    ↓
Feature Logger (with versioning)
    ↓
Shadow Model (learn_one)
    ↓
Drift Monitor (track performance)
    ↓
Promotion Gate (validate)
    ↓
(Optional) Promote → Frozen Model
```

### Hybrid Decision Flow

```
Market Data
    ↓
┌─────────────┬──────────────┬──────────────┐
│             │              │              │
Own Model     Copy Validator Regime Model
│             │              │              │
└─────────────┴──────────────┴──────────────┘
                ↓
        Hybrid Engine
    (confidence weighting)
                ↓
        Final Decision
                ↓
        Signal Output
    (NOT execution)
```

## 🔐 Safety Guarantees

### 1. Isolation
- ✅ Adaptive never directly calls execution
- ✅ Event system provides decoupling
- ✅ Shadow models separate from frozen models

### 2. Backward Compatibility
- ✅ All existing APIs unchanged
- ✅ Paper pipeline 100% intact
- ✅ Frozen model path preserved
- ✅ Execution logic untouched

### 3. Config Gates
- ✅ All features disabled by default
- ✅ Must be explicitly enabled
- ✅ Can be disabled instantly

### 4. Error Isolation
- ✅ Listener errors don't break execution
- ✅ Shadow learning errors don't affect production
- ✅ Drift detection failures safe

### 5. Rollback Support
- ✅ Automatic backup before promotion
- ✅ Rollback to any previous version
- ✅ Model registry tracks all versions

## 📝 Implementation Checklist

- [x] **PHASE 1:** Adaptive shadow learning layer
- [x] **PHASE 2:** Event hook system
- [x] **PHASE 3:** Model registry v2
- [x] **PHASE 4:** Drift monitor v2
- [x] **PHASE 5:** Copy-trader analyzer
- [x] **PHASE 6:** Hybrid decision layer
- [x] **PHASE 7:** Adaptive backtester (already existed)
- [x] **PHASE 8:** Execution hardening verification
- [x] **PHASE 9:** Config flags
- [x] **PHASE 10:** Comprehensive tests
- [x] **PHASE 11:** Safety verification

## 🚦 Deployment Guide

### Step 1: Review & Test

```bash
# Run all tests
pytest tests/ -v

# Verify hard constraints
pytest tests/safety/test_final_verification.py -v

# Check execution hardening
pytest tests/safety/test_execution_hardening.py -v
```

### Step 2: Enable Features Gradually

1. **Enable Events First:**
   ```yaml
   events:
     enabled: true
   ```

2. **Enable Shadow Learning:**
   ```yaml
   adaptive:
     enabled: true
     shadow_learning: true
   ```

3. **Enable Leaderboard (Optional):**
   ```yaml
   leaderboard:
     enabled: true
   ```

4. **Enable Hybrid (Optional):**
   ```yaml
   hybrid:
     enabled: true
   ```

### Step 3: Monitor

- Monitor event logs: `ai_data/events/trade_events.jsonl`
- Monitor adaptive logs: `ai_data/adaptive/features/`
- Monitor promotion decisions: `ai_data/adaptive/promotion_log.jsonl`
- Check drift metrics regularly

### Step 4: Promote Shadow Models

```python
from adaptive.pipeline import ShadowModelPipeline

pipeline = ShadowModelPipeline()
metrics = {"winrate": 0.58, "expectancy": 0.65, "total_trades": 150}

if pipeline.evaluate_for_promotion(metrics):
    pipeline.promote_shadow_to_production()
    print("✓ Shadow model promoted")
```

## 🔧 Troubleshooting

### Issue: Events not firing

**Solution:** Check `events.enabled` in config.yaml

### Issue: Shadow model not learning

**Solution:** Check `adaptive.enabled` and `adaptive.shadow_learning` flags

### Issue: Promotion gate always rejects

**Solution:** Review promotion criteria in config.yaml and adjust thresholds

### Issue: Hybrid engine returning flat

**Solution:** Check `min_confidence_threshold` and signal confidence scores

## 📚 Additional Resources

- **Feature Logging:** See `adaptive/feature_logger.py` for schema versioning
- **Drift Detection:** See `monitoring/drift_monitor_v2.py` for metrics
- **Event System:** See `events/trade_events.py` for event types
- **Hybrid Engine:** See `decision/hybrid_engine.py` for fusion logic

## 🎯 Next Steps

1. ✅ Review this implementation
2. ✅ Run comprehensive tests
3. ⏭️ Deploy to staging environment
4. ⏭️ Enable features gradually
5. ⏭️ Monitor performance
6. ⏭️ Adjust weights and thresholds
7. ⏭️ Promote shadow models when ready

## 📄 License & Credits

Part of the Binance AI Trader project. Implemented with strict adherence to architectural constraints and backward compatibility requirements.
