"""Shadow Learner - Phase 4

Online learning loop for shadow model only.
Uses simple incremental learning (river library).
Shadow NEVER trades directly.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class LearningConfig:
    """Configuration for shadow learning"""
    max_updates_per_hour: int = 10
    min_trades_before_update: int = 10
    learning_rate: float = 0.01
    learning_rate_decay: float = 0.99
    window_size: int = 100
    enable_drift_guard: bool = True
    
    def to_dict(self) -> dict:
        return {
            "max_updates_per_hour": self.max_updates_per_hour,
            "min_trades_before_update": self.min_trades_before_update,
            "learning_rate": self.learning_rate,
            "learning_rate_decay": self.learning_rate_decay,
            "window_size": self.window_size,
            "enable_drift_guard": self.enable_drift_guard,
        }


@dataclass(frozen=True)
class LearningUpdate:
    """Record of a single learning update"""
    update_id: int
    timestamp: str
    trades_processed: int
    learning_rate: float
    loss: Optional[float]
    metrics: dict[str, float]


class ShadowLearner:
    """
    Online learner for shadow model.
    
    CRITICAL RULES:
    - Shadow model NEVER trades directly
    - Only learns from completed paper trades
    - Respects rate limits (max updates/hour)
    - Maintains learning history
    - Can be paused/resumed
    """
    
    def __init__(
        self,
        config: LearningConfig,
        model_dir: Path,
        history_path: Optional[Path] = None,
    ):
        """
        Initialize shadow learner.
        
        Args:
            config: Learning configuration
            model_dir: Directory for shadow model artifacts
            history_path: Optional path for learning history log
        """
        self.config = config
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_path = history_path or (self.model_dir / "learning_history.jsonl")
        self.state_path = self.model_dir / "learner_state.json"
        
        self._update_count = 0
        self._total_trades_processed = 0
        self._current_learning_rate = config.learning_rate
        self._paused = False
        self._last_update_time: Optional[datetime] = None
        
        self._load_state()
    
    def _load_state(self) -> None:
        """Load learner state from disk"""
        if self.state_path.exists():
            try:
                state = json.loads(self.state_path.read_text())
                self._update_count = state.get("update_count", 0)
                self._total_trades_processed = state.get("total_trades_processed", 0)
                self._current_learning_rate = state.get("current_learning_rate", self.config.learning_rate)
                self._paused = state.get("paused", False)
                
                last_update = state.get("last_update_time")
                if last_update:
                    self._last_update_time = datetime.fromisoformat(last_update)
                    
                logger.info(f"Loaded learner state: {self._update_count} updates, {self._total_trades_processed} trades")
            except Exception as e:
                logger.error(f"Failed to load learner state: {e}")
    
    def _save_state(self) -> None:
        """Save learner state to disk"""
        state = {
            "update_count": self._update_count,
            "total_trades_processed": self._total_trades_processed,
            "current_learning_rate": self._current_learning_rate,
            "paused": self._paused,
            "last_update_time": self._last_update_time.isoformat() if self._last_update_time else None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self.state_path.write_text(json.dumps(state, indent=2))
    
    def _log_update(self, update: LearningUpdate) -> None:
        """Log learning update to history"""
        with open(self.history_path, "a") as f:
            f.write(json.dumps({
                "update_id": update.update_id,
                "timestamp": update.timestamp,
                "trades_processed": update.trades_processed,
                "learning_rate": update.learning_rate,
                "loss": update.loss,
                "metrics": update.metrics,
            }) + "\n")
    
    def _check_rate_limit(self) -> tuple[bool, str]:
        """
        Check if we can perform an update (rate limiting).
        
        Returns:
            Tuple of (allowed, reason)
        """
        if self._paused:
            return False, "Learner is paused"
        
        if not self._last_update_time:
            return True, "First update"
        
        # Check updates per hour
        now = datetime.now(timezone.utc)
        time_since_last = (now - self._last_update_time).total_seconds()
        
        # If less than 1 hour since last update, check count
        if time_since_last < 3600:
            # Count recent updates
            recent_updates = self._count_recent_updates(hours=1)
            if recent_updates >= self.config.max_updates_per_hour:
                return False, f"Rate limit: {recent_updates}/{self.config.max_updates_per_hour} updates in last hour"
        
        return True, "Rate limit OK"
    
    def _count_recent_updates(self, hours: int = 1) -> int:
        """Count updates in the last N hours"""
        if not self.history_path.exists():
            return 0
        
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        count = 0
        
        try:
            with open(self.history_path, "r") as f:
                for line in f:
                    try:
                        update = json.loads(line)
                        ts = datetime.fromisoformat(update["timestamp"]).timestamp()
                        if ts >= cutoff:
                            count += 1
                    except Exception:
                        continue
        except Exception:
            pass
        
        return count
    
    def can_update(self, num_trades: int) -> tuple[bool, str]:
        """
        Check if shadow can be updated with given number of trades.
        
        Args:
            num_trades: Number of new trades available
        
        Returns:
            Tuple of (can_update, reason)
        """
        # Check minimum trades
        if num_trades < self.config.min_trades_before_update:
            return False, f"Not enough trades: {num_trades} < {self.config.min_trades_before_update}"
        
        # Check rate limit
        rate_ok, rate_msg = self._check_rate_limit()
        if not rate_ok:
            return False, rate_msg
        
        return True, "Can update"
    
    def learn_from_trades(
        self,
        trade_features: pd.DataFrame,
    ) -> tuple[bool, Optional[LearningUpdate]]:
        """
        Update shadow model with new trade data (incremental learning).
        
        This is a SIMPLIFIED implementation that logs the learning intent.
        Actual model training would happen here with river or similar incremental learner.
        
        Args:
            trade_features: DataFrame with trade features and outcomes
        
        Returns:
            Tuple of (success, LearningUpdate or None)
        """
        try:
            num_trades = len(trade_features)
            
            # Check if we can update
            can_update, reason = self.can_update(num_trades)
            if not can_update:
                logger.info(f"Skipping shadow update: {reason}")
                return False, None
            
            # Apply learning rate decay
            self._current_learning_rate *= self.config.learning_rate_decay
            
            # Simulate learning (in real implementation, this would train the model)
            # For now, we just log that learning would happen
            logger.info(
                f"Shadow learning: {num_trades} trades, "
                f"lr={self._current_learning_rate:.6f}"
            )
            
            # Create update record
            self._update_count += 1
            self._total_trades_processed += num_trades
            self._last_update_time = datetime.now(timezone.utc)
            
            # Calculate simple metrics (placeholder)
            metrics = {
                "trades_processed": num_trades,
                "total_trades": self._total_trades_processed,
                "learning_rate": self._current_learning_rate,
            }
            
            update = LearningUpdate(
                update_id=self._update_count,
                timestamp=datetime.now(timezone.utc).isoformat(),
                trades_processed=num_trades,
                learning_rate=self._current_learning_rate,
                loss=None,  # Would be computed during actual training
                metrics=metrics,
            )
            
            self._log_update(update)
            self._save_state()
            
            logger.info(f"Shadow update #{self._update_count} complete: {num_trades} trades")
            return True, update
            
        except Exception as e:
            logger.error(f"Shadow learning failed: {e}", exc_info=True)
            return False, None
    
    def pause(self) -> None:
        """Pause learning"""
        self._paused = True
        self._save_state()
        logger.info("Shadow learner paused")
    
    def resume(self) -> None:
        """Resume learning"""
        self._paused = False
        self._save_state()
        logger.info("Shadow learner resumed")
    
    def is_paused(self) -> bool:
        """Check if learner is paused"""
        return self._paused
    
    def get_stats(self) -> dict:
        """Get learner statistics"""
        recent_updates = self._count_recent_updates(hours=1)
        
        return {
            "total_updates": self._update_count,
            "total_trades_processed": self._total_trades_processed,
            "current_learning_rate": self._current_learning_rate,
            "paused": self._paused,
            "last_update": self._last_update_time.isoformat() if self._last_update_time else None,
            "recent_updates_1h": recent_updates,
            "rate_limit_status": f"{recent_updates}/{self.config.max_updates_per_hour}",
        }
    
    def get_learning_history(self, limit: int = 100) -> list[dict]:
        """
        Get learning history.
        
        Args:
            limit: Maximum number of history entries
        
        Returns:
            List of learning updates (most recent first)
        """
        if not self.history_path.exists():
            return []
        
        history = []
        with open(self.history_path, "r") as f:
            for line in f:
                try:
                    history.append(json.loads(line))
                except Exception:
                    continue
        
        return list(reversed(history[-limit:]))
