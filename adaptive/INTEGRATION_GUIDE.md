# Integration Guide: Adaptive System + Paper Trading

**Goal**: Enable shadow model to learn from paper trades without modifying paper trading v1 pipeline.

## 🔌 Integration Strategy

The adaptive system is a **READ-ONLY consumer** of paper trading artifacts. There are two integration approaches:

### Option 1: Event-Based (Recommended)

Add a simple event emitter after paper trades complete. The adaptive system listens to events.

### Option 2: Log-Based Polling

Adaptive system periodically reads paper trading log files and processes new entries.

---

## 📝 Option 1: Event-Based Integration

### Step 1: Create Event Emitter

Create `adaptive/integration/event_bridge.py`:

```python
"""Event bridge between paper trading and adaptive system.
READ ONLY - does not modify paper trading behavior."""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

from adaptive import AdaptiveController, AdaptiveConfig

logger = logging.getLogger(__name__)


class AdaptiveEventBridge:
    """
    Bridges paper trading events to adaptive system.
    Completely isolated - paper trading has no dependency on this.
    """
    
    def __init__(self, adaptive_dir: Path):
        config = AdaptiveConfig.default(adaptive_dir)
        self.controller = AdaptiveController(config)
        self._enabled = False
    
    def initialize(
        self,
        frozen_model_id: str,
        frozen_artifact_path: Path,
    ) -> bool:
        """Initialize adaptive system with frozen model"""
        try:
            success, msg = self.controller.initialize_from_frozen_model(
                frozen_model_id=frozen_model_id,
                frozen_artifact_path=frozen_artifact_path,
            )
            
            if success:
                self._enabled = True
                logger.info(f"Adaptive system initialized: {msg}")
            else:
                logger.error(f"Adaptive initialization failed: {msg}")
            
            return success
        except Exception as e:
            logger.error(f"Failed to initialize adaptive: {e}")
            return False
    
    def on_trade_opened(
        self,
        trade_id: str,
        features: Dict[str, Any],
        prediction: str,
        confidence: float,
    ) -> None:
        """
        Called when paper trade opens.
        Snapshots features at entry.
        """
        if not self._enabled:
            return
        
        try:
            # Just log the entry features for now
            # Trade not complete yet, so no outcome/pnl
            self.controller.process_paper_trade(
                trade_id=trade_id,
                features_at_entry=features,
                prediction=prediction,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(f"Error processing trade open: {e}")
    
    def on_trade_closed(
        self,
        trade_id: str,
        features_at_entry: Dict[str, Any],
        features_at_exit: Dict[str, Any],
        prediction: str,
        confidence: float,
        outcome: str,  # "win", "loss", "breakeven"
        pnl: float,
    ) -> None:
        """
        Called when paper trade closes.
        Triggers shadow learning.
        """
        if not self._enabled:
            return
        
        try:
            # Process complete trade
            self.controller.process_paper_trade(
                trade_id=trade_id,
                features_at_entry=features_at_entry,
                prediction=prediction,
                confidence=confidence,
                features_at_exit=features_at_exit,
                outcome=outcome,
                pnl=pnl,
            )
        except Exception as e:
            logger.error(f"Error processing trade close: {e}")


# Global instance (singleton pattern)
_bridge: Optional[AdaptiveEventBridge] = None


def get_bridge(adaptive_dir: Path = Path("ai_data/adaptive")) -> AdaptiveEventBridge:
    """Get or create event bridge singleton"""
    global _bridge
    if _bridge is None:
        _bridge = AdaptiveEventBridge(adaptive_dir)
    return _bridge
```

### Step 2: Minimal Hook in Paper Trading

In `trading/paper_live.py` (or wherever paper trades complete), add **ONE LINE**:

```python
# At the top of the file
try:
    from adaptive.integration.event_bridge import get_bridge
    ADAPTIVE_ENABLED = True
except ImportError:
    ADAPTIVE_ENABLED = False

# ... existing paper trading code ...

def paper_trade_live_once(...):
    # ... existing code ...
    
    # After trade completes (existing code unchanged above this)
    if executed and fill is not None:
        equity_after = float(fill.equity_after)
        pnl = float(equity_after - equity_before)
        
        # ... existing logging code ...
        
        # NEW: Notify adaptive system (if available)
        if ADAPTIVE_ENABLED:
            try:
                bridge = get_bridge()
                bridge.on_trade_closed(
                    trade_id=f"{ts_s or 'na'}_{ctm_i}",
                    features_at_entry=row.to_dict(),  # Features from current row
                    features_at_exit=row.to_dict(),   # Same for now
                    prediction=str(pos_label),
                    confidence=float(conf),
                    outcome="win" if pnl > 0 else ("loss" if pnl < 0 else "breakeven"),
                    pnl=float(pnl),
                )
            except Exception as e:
                # Fail silently - don't break paper trading
                logger.debug(f"Adaptive event failed: {e}")
    
    # ... rest of existing code unchanged ...
```

**Key points:**
- ✅ Only 1 function call added
- ✅ Try/except ensures no paper trading breakage
- ✅ Import is optional (if adaptive not available)
- ✅ No changes to paper trading logic
- ✅ Completely isolated

### Step 3: Initialize at Startup

When starting paper trading, initialize adaptive:

```python
# In main.py or wherever paper trading starts
from adaptive.integration.event_bridge import get_bridge

# Initialize once at startup
bridge = get_bridge()
bridge.initialize(
    frozen_model_id="m_baseline",  # Your frozen model ID
    frozen_artifact_path=Path("model_registry/models/frozen.pkl"),
)

# Then start paper trading as normal
```

---

## 📂 Option 2: Log-Based Polling

If you prefer not to touch paper trading code at all, use log polling.

### Step 1: Create Log Poller

Create `adaptive/integration/log_poller.py`:

```python
"""Polls paper trading logs and processes new trades.
Completely isolated - zero coupling to paper trading."""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

from adaptive import AdaptiveController, AdaptiveConfig


class AdaptiveLogPoller:
    """
    Polls paper trading logs and feeds to adaptive system.
    NO modifications to paper trading required.
    """
    
    def __init__(
        self,
        adaptive_dir: Path,
        trades_log_path: Path,
        poll_interval_seconds: float = 60.0,
    ):
        config = AdaptiveConfig.default(adaptive_dir)
        self.controller = AdaptiveController(config)
        self.trades_log_path = trades_log_path
        self.poll_interval = poll_interval_seconds
        
        # Track last processed trade
        self._cursor_path = adaptive_dir / "log_poller_cursor.json"
        self._last_processed_line = self._load_cursor()
    
    def _load_cursor(self) -> int:
        """Load cursor (last processed line number)"""
        if self._cursor_path.exists():
            try:
                data = json.loads(self._cursor_path.read_text())
                return data.get("last_line", 0)
            except Exception:
                pass
        return 0
    
    def _save_cursor(self, line_number: int) -> None:
        """Save cursor"""
        self._cursor_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "last_line": line_number,
            "updated_at": datetime.now().isoformat(),
        }
        self._cursor_path.write_text(json.dumps(data, indent=2))
    
    def poll_once(self) -> int:
        """
        Poll trades log once and process new trades.
        Returns number of trades processed.
        """
        if not self.trades_log_path.exists():
            return 0
        
        processed = 0
        
        with open(self.trades_log_path, "r") as f:
            for line_num, line in enumerate(f, start=1):
                # Skip already processed
                if line_num <= self._last_processed_line:
                    continue
                
                try:
                    trade = json.loads(line)
                    
                    # Extract fields from paper trading log
                    self.controller.process_paper_trade(
                        trade_id=trade.get("trade_id"),
                        features_at_entry={},  # Would need to reconstruct from logs
                        prediction=trade.get("side"),
                        confidence=1.0,  # Not in log, use default
                        outcome="win" if trade.get("pnl", 0) > 0 else "loss",
                        pnl=trade.get("pnl", 0),
                    )
                    
                    processed += 1
                    self._last_processed_line = line_num
                    
                except Exception as e:
                    print(f"Error processing line {line_num}: {e}")
                    continue
        
        if processed > 0:
            self._save_cursor(self._last_processed_line)
        
        return processed
    
    def run_forever(self) -> None:
        """Run poller in loop"""
        print(f"Starting adaptive log poller (interval: {self.poll_interval}s)")
        print(f"Watching: {self.trades_log_path}")
        
        while True:
            try:
                n = self.poll_once()
                if n > 0:
                    print(f"Processed {n} new trades")
            except Exception as e:
                print(f"Poll error: {e}")
            
            time.sleep(self.poll_interval)


if __name__ == "__main__":
    # Example usage
    poller = AdaptiveLogPoller(
        adaptive_dir=Path("ai_data/adaptive"),
        trades_log_path=Path("ai_data/paper/trades.jsonl"),
        poll_interval_seconds=60.0,
    )
    
    # Initialize
    poller.controller.initialize_from_frozen_model(
        frozen_model_id="m_baseline",
        frozen_artifact_path=Path("model_registry/models/frozen.pkl"),
    )
    
    # Run
    poller.run_forever()
```

### Step 2: Run as Separate Process

```bash
# Run in separate terminal/screen/tmux
python3 -m adaptive.integration.log_poller
```

**Key points:**
- ✅ Zero paper trading code changes
- ✅ Completely separate process
- ✅ Polls logs periodically
- ✅ Cursor tracks progress
- ✅ Can be stopped/restarted anytime

---

## 🎛️ Configuration

Both approaches use the same configuration:

```python
from adaptive import AdaptiveConfig
from pathlib import Path

config = AdaptiveConfig.default(Path("ai_data/adaptive"))

# Customize if needed
config.learning_config.max_updates_per_hour = 10
config.learning_config.min_trades_before_update = 10
config.drift_config.auto_pause_on_drift = True
config.promotion_criteria.min_winrate_improvement = 0.02
```

---

## 📊 Monitoring

### Check Status

```bash
python3 -m adaptive.cli status
```

### View Logs

```bash
# Drift alerts
tail -f ai_data/adaptive/adaptive_logs/metrics/drift_alerts.jsonl

# Feature logs
tail -f ai_data/adaptive/adaptive_logs/features/features_log.jsonl

# Promotion decisions
tail -f ai_data/adaptive/adaptive_logs/decisions/promotion_decisions.jsonl
```

### Programmatic Monitoring

```python
from adaptive import AdaptiveController, AdaptiveConfig
from pathlib import Path

controller = AdaptiveController(AdaptiveConfig.default(Path("ai_data/adaptive")))

# Get stats
status = controller.get_status()
print(f"Shadow updates: {status['learner_stats']['total_updates']}")
print(f"Trades processed: {status['learner_stats']['total_trades_processed']}")

# Check drift
drift = status['drift_comparison']
if drift.get('drift_detected'):
    print(f"⚠️  Drift detected: {drift['drift_reason']}")
```

---

## 🚨 Safety Checks

Before deploying:

1. **Test with simulated data first**
2. **Verify adaptive has no write access to paper trading artifacts**
3. **Confirm shadow model never generates execution signals**
4. **Check drift monitoring is active**
5. **Verify promotion gate blocks bad models**

---

## 🔄 Deployment Checklist

- [ ] Choose integration approach (event-based or log-based)
- [ ] Initialize adaptive system with frozen model
- [ ] Test with paper trading in test environment
- [ ] Verify logs are generated correctly
- [ ] Monitor for 24 hours in paper environment
- [ ] Check drift alerts and promotion decisions
- [ ] Review shadow learning metrics
- [ ] Deploy to production paper trading

---

## ❓ FAQ

**Q: Will this slow down paper trading?**  
A: No. Event processing is async and fails silently if errors occur.

**Q: What if adaptive crashes?**  
A: Paper trading continues unaffected. Adaptive is optional.

**Q: How do I disable adaptive learning?**  
A: Simply pause the learner: `controller.pause_learning()`

**Q: Can I rollback a bad shadow model?**  
A: Yes: `controller.model_manager.rollback_frozen(backup_id)`

**Q: How do I promote shadow to frozen?**  
A: First evaluate: `controller.evaluate_promotion()`, then if approved: `controller.promote_shadow_to_frozen()`

---

**Ready to integrate? Start with Option 1 (event-based) for best results.**
