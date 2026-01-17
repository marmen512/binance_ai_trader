# PAPER TRADING SYSTEM v1 - ARCHITECTURAL BOUNDARIES

⚠ CRITICAL SYSTEM CONTRACT

This repository implements a PAPER TRADING SYSTEM with strict architectural boundaries.
These boundaries exist to prevent accidental online learning, feedback loops,
and invalidation of paper trading results.

## FUNDAMENTAL INVARIANTS

### NO ONLINE LEARNING
There is NO online learning in this system.
The model is frozen during paper trading.
All learning happens offline, manually, after human review.

### NO REINFORCEMENT LOOPS
There are NO feedback loops from paper trading to model updates.
Replay logs are read-only during paper trading.
No automatic model improvements based on paper results.

### NO SELF-IMPROVING BEHAVIOR
The system does NOT improve itself automatically.
It does NOT adapt to market conditions.
It does NOT learn from paper trading performance.

### CAPITAL PRESERVATION FIRST
The system is intentionally conservative.
HOLD is the default safe action.
Stability > performance during paper mode.

## ARCHITECTURAL SEPARATION

### PAPER TRADING MODE
- Model is frozen (read-only)
- No weight updates allowed
- No training during trading
- Replay logs are historical only
- HOLD as default action

### OFFLINE TRAINING MODE
- Manual execution only
- Historical data only
- Human review required
- Single-shot updates
- Post-soak only

### MONITORING MODE
- Read-only inspection
- Behavioral validation
- CI gate enforcement
- No side effects

## FORBIDDEN PATTERNS

Any attempt to implement the following would violate the paper trading contract:

### DANGEROUS IMPORTS
```python
# FORBIDDEN - creates online learning
import training.offline_finetuning from inference or monitoring

# FORBIDDEN - creates feedback loop
from training.replay_to_instruction import convert_trade_to_instruction during live trading
```

### DANGEROUS EXECUTION
```python
# FORBIDDEN - automatic training
if paper_trading_active:
    run_training()  # This would invalidate all results

# FORBIDDEN - live model updates
if performance_degrades:
    update_model()  # This creates a feedback loop
```

### DANGEROUS DATA FLOWS
```
# FORBIDDEN - live data to training
live_trades → training_pipeline  # Creates online learning

# FORBIDDEN - automatic triggers
paper_results → auto_training  # Violates manual review
```

## SAFE PATTERNS

### CORRECT SEPARATION
```
paper_trading → replay_log.json (historical only)
                ↓
         (manual review, offline)
                ↓
    replay_to_instruction → dataset → manual_training
```

### CORRECT MONITORING
```python
# SAFE - read-only inspection
metrics = monitor(replay_log)  # No side effects
if metrics violate invariants:
    block_deployment()  # CI gate, not training
```

## CONSEQUENCES OF VIOLATION

Any violation of these boundaries would:
1. Invalidate all paper trading results
2. Break the scientific validity of the system
3. Create uncontrolled learning behavior
4. Compromise capital preservation guarantees

## ENGINEER RESPONSIBILITY

Future contributors MUST:
1. Read these boundaries before any changes
2. Verify no online learning is introduced
3. Ensure monitoring remains read-only
4. Keep training manual and offline
5. Preserve the frozen model during paper trading

The system is intentionally conservative and limited by design.
This is a feature, not a bug.

## FINAL WARNING

This system is locked for paper trading stability.
Any "helpful" improvements that introduce online learning,
automatic updates, or feedback loops will be rejected as critical bugs.

Stability and capital preservation are non-negotiable requirements.
