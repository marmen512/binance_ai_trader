"""
Promotion gate for shadow model validation.

Determines when a shadow model is ready to be promoted to production
based on performance metrics and drift detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
import json
from pathlib import Path

from adaptive.drift_monitor import DriftMonitorV2


@dataclass
class PromotionCriteria:
    """Criteria for model promotion."""
    min_winrate: float = 0.52
    min_expectancy: float = 0.0
    min_trades: int = 100
    max_loss_streak: int = 5
    max_drawdown_slope: float = -5.0
    min_improvement_vs_frozen: float = 0.02  # 2% improvement required


@dataclass
class PromotionDecision:
    """Result of promotion evaluation."""
    approved: bool
    reasons: list[str]
    metrics: dict
    timestamp: str


class PromotionGate:
    """
    Validates shadow model performance before promotion to production.
    
    Acts as a safety gate ensuring only improved models are promoted.
    """
    
    def __init__(
        self,
        criteria: Optional[PromotionCriteria] = None,
        log_path: Optional[str | Path] = None
    ):
        """
        Initialize promotion gate.
        
        Args:
            criteria: Promotion criteria (uses defaults if None)
            log_path: Path to log promotion decisions
        """
        self.criteria = criteria or PromotionCriteria()
        self.log_path = Path(log_path) if log_path else Path("ai_data/adaptive/promotion_log.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def evaluate(
        self,
        shadow_metrics: dict,
        frozen_metrics: Optional[dict] = None
    ) -> PromotionDecision:
        """
        Evaluate if shadow model should be promoted.
        
        Args:
            shadow_metrics: Shadow model performance metrics
            frozen_metrics: Current frozen model metrics (for comparison)
            
        Returns:
            PromotionDecision with approval and reasons
        """
        reasons = []
        approved = True
        
        # Extract metrics
        winrate = shadow_metrics.get('winrate', 0.0)
        expectancy = shadow_metrics.get('expectancy', 0.0)
        total_trades = shadow_metrics.get('total_trades', 0)
        loss_streak = shadow_metrics.get('loss_streak', 0)
        drawdown_slope = shadow_metrics.get('drawdown_slope', 0.0)
        
        # Check minimum trades
        if total_trades < self.criteria.min_trades:
            approved = False
            reasons.append(f"Insufficient trades: {total_trades} < {self.criteria.min_trades}")
        
        # Check winrate
        if winrate < self.criteria.min_winrate:
            approved = False
            reasons.append(f"Low winrate: {winrate:.3f} < {self.criteria.min_winrate}")
        
        # Check expectancy
        if expectancy < self.criteria.min_expectancy:
            approved = False
            reasons.append(f"Low expectancy: {expectancy:.3f} < {self.criteria.min_expectancy}")
        
        # Check loss streak
        if loss_streak > self.criteria.max_loss_streak:
            approved = False
            reasons.append(f"High loss streak: {loss_streak} > {self.criteria.max_loss_streak}")
        
        # Check drawdown slope
        if drawdown_slope < self.criteria.max_drawdown_slope:
            approved = False
            reasons.append(f"Steep drawdown: {drawdown_slope:.3f} < {self.criteria.max_drawdown_slope}")
        
        # Compare with frozen model if available
        if frozen_metrics is not None:
            frozen_winrate = frozen_metrics.get('winrate', 0.0)
            frozen_expectancy = frozen_metrics.get('expectancy', 0.0)
            
            # Require minimum improvement
            winrate_improvement = winrate - frozen_winrate
            expectancy_improvement = expectancy - frozen_expectancy
            
            if winrate_improvement < self.criteria.min_improvement_vs_frozen:
                if expectancy_improvement < self.criteria.min_improvement_vs_frozen:
                    approved = False
                    reasons.append(
                        f"Insufficient improvement: winrate +{winrate_improvement:.3f}, "
                        f"expectancy +{expectancy_improvement:.3f}"
                    )
                else:
                    reasons.append(f"Expectancy improved by {expectancy_improvement:.3f}")
            else:
                reasons.append(f"Winrate improved by {winrate_improvement:.3f}")
        
        if approved and not reasons:
            reasons.append("All criteria met")
        
        decision = PromotionDecision(
            approved=approved,
            reasons=reasons,
            metrics=shadow_metrics,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Log decision
        self._log_decision(decision)
        
        return decision
    
    def evaluate_with_drift_monitor(
        self,
        drift_monitor: DriftMonitorV2,
        frozen_metrics: Optional[dict] = None
    ) -> PromotionDecision:
        """
        Evaluate using a DriftMonitorV2 instance.
        
        Args:
            drift_monitor: DriftMonitorV2 with shadow model trade history
            frozen_metrics: Current frozen model metrics (for comparison)
            
        Returns:
            PromotionDecision
        """
        metrics_obj = drift_monitor.compute_metrics()
        
        if metrics_obj is None:
            return PromotionDecision(
                approved=False,
                reasons=["No metrics available"],
                metrics={},
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        shadow_metrics = {
            'winrate': metrics_obj.winrate,
            'expectancy': metrics_obj.expectancy,
            'avg_pnl': metrics_obj.avg_pnl,
            'loss_streak': metrics_obj.loss_streak,
            'max_loss_streak': metrics_obj.max_loss_streak,
            'drawdown_slope': metrics_obj.drawdown_slope,
            'total_trades': metrics_obj.total_trades,
            'winning_trades': metrics_obj.winning_trades,
            'losing_trades': metrics_obj.losing_trades
        }
        
        return self.evaluate(shadow_metrics, frozen_metrics)
    
    def _log_decision(self, decision: PromotionDecision) -> None:
        """Log promotion decision to file."""
        try:
            with open(self.log_path, 'a') as f:
                log_entry = {
                    'timestamp': decision.timestamp,
                    'approved': decision.approved,
                    'reasons': decision.reasons,
                    'metrics': decision.metrics
                }
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Failed to log promotion decision: {e}")
    
    def get_recent_decisions(self, limit: int = 10) -> list[dict]:
        """
        Get recent promotion decisions.
        
        Args:
            limit: Maximum number of decisions to return
            
        Returns:
            List of recent decisions
        """
        if not self.log_path.exists():
            return []
        
        decisions = []
        try:
            with open(self.log_path, 'r') as f:
                lines = f.readlines()
            
            for line in lines[-limit:]:
                try:
                    decisions.append(json.loads(line))
                except Exception:
                    continue
        except Exception:
            pass
        
        return decisions
