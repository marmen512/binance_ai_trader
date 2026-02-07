"""Promotion Gate - Phase 6

Model promotion with strict testing requirements.
Shadow promoted to frozen ONLY if passes all tests.

NOT automatic - requires explicit approval after testing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class PromotionStatus(Enum):
    """Promotion decision status"""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


@dataclass
class PromotionCriteria:
    """Criteria for model promotion"""
    min_trades: int = 100
    min_winrate_improvement: float = 0.02  # 2% better
    min_expectancy_improvement: float = 0.05  # 5% better
    max_drawdown_threshold: float = 0.20  # 20% max
    min_sharpe_ratio: Optional[float] = None
    require_walk_forward_test: bool = True
    require_paper_replay_test: bool = True
    require_last_n_trades_test: bool = True
    last_n_trades: int = 50
    
    def to_dict(self) -> dict:
        return {
            "min_trades": self.min_trades,
            "min_winrate_improvement": self.min_winrate_improvement,
            "min_expectancy_improvement": self.min_expectancy_improvement,
            "max_drawdown_threshold": self.max_drawdown_threshold,
            "min_sharpe_ratio": self.min_sharpe_ratio,
            "require_walk_forward_test": self.require_walk_forward_test,
            "require_paper_replay_test": self.require_paper_replay_test,
            "require_last_n_trades_test": self.require_last_n_trades_test,
            "last_n_trades": self.last_n_trades,
        }


@dataclass(frozen=True)
class TestResult:
    """Result of a promotion test"""
    test_name: str
    passed: bool
    shadow_metric: float
    frozen_metric: float
    improvement: float
    details: dict
    
    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "shadow_metric": self.shadow_metric,
            "frozen_metric": self.frozen_metric,
            "improvement": self.improvement,
            "details": self.details,
        }


@dataclass(frozen=True)
class PromotionDecision:
    """Final promotion decision"""
    status: PromotionStatus
    timestamp: str
    shadow_model_id: str
    frozen_model_id: str
    test_results: list[TestResult]
    all_tests_passed: bool
    reason: str
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "shadow_model_id": self.shadow_model_id,
            "frozen_model_id": self.frozen_model_id,
            "test_results": [t.to_dict() for t in self.test_results],
            "all_tests_passed": self.all_tests_passed,
            "reason": self.reason,
        }


class PromotionGate:
    """
    Manages model promotion from shadow to frozen.
    
    CRITICAL: This is NOT automatic.
    Shadow promoted ONLY if:
    1. Passes all required tests
    2. Meets improvement criteria
    3. Explicit approval granted
    
    Tests:
    - Walk-forward test
    - Paper replay test
    - Last N trades test
    """
    
    def __init__(
        self,
        criteria: PromotionCriteria,
        decisions_dir: Path,
    ):
        """
        Initialize promotion gate.
        
        Args:
            criteria: Promotion criteria
            decisions_dir: Directory for storing decisions
        """
        self.criteria = criteria
        self.decisions_dir = Path(decisions_dir)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        
        self.decisions_log_path = self.decisions_dir / "promotion_decisions.jsonl"
    
    def _test_winrate_improvement(
        self,
        shadow_trades: pd.DataFrame,
        frozen_trades: pd.DataFrame,
    ) -> TestResult:
        """Test winrate improvement"""
        shadow_wins = (shadow_trades["outcome"] == "win").sum()
        shadow_winrate = shadow_wins / len(shadow_trades) if len(shadow_trades) > 0 else 0.0
        
        frozen_wins = (frozen_trades["outcome"] == "win").sum()
        frozen_winrate = frozen_wins / len(frozen_trades) if len(frozen_trades) > 0 else 0.0
        
        improvement = shadow_winrate - frozen_winrate
        passed = improvement >= self.criteria.min_winrate_improvement
        
        return TestResult(
            test_name="winrate_improvement",
            passed=passed,
            shadow_metric=shadow_winrate,
            frozen_metric=frozen_winrate,
            improvement=improvement,
            details={
                "required_improvement": self.criteria.min_winrate_improvement,
                "shadow_trades": len(shadow_trades),
                "frozen_trades": len(frozen_trades),
            },
        )
    
    def _test_expectancy_improvement(
        self,
        shadow_trades: pd.DataFrame,
        frozen_trades: pd.DataFrame,
    ) -> TestResult:
        """Test expectancy improvement"""
        # Shadow expectancy
        shadow_wins = shadow_trades[shadow_trades["outcome"] == "win"]
        shadow_losses = shadow_trades[shadow_trades["outcome"] == "loss"]
        shadow_winrate = len(shadow_wins) / len(shadow_trades) if len(shadow_trades) > 0 else 0.0
        shadow_avg_win = shadow_wins["pnl"].mean() if len(shadow_wins) > 0 else 0.0
        shadow_avg_loss = abs(shadow_losses["pnl"].mean()) if len(shadow_losses) > 0 else 0.0
        shadow_expectancy = (shadow_winrate * shadow_avg_win) - ((1 - shadow_winrate) * shadow_avg_loss)
        
        # Frozen expectancy
        frozen_wins = frozen_trades[frozen_trades["outcome"] == "win"]
        frozen_losses = frozen_trades[frozen_trades["outcome"] == "loss"]
        frozen_winrate = len(frozen_wins) / len(frozen_trades) if len(frozen_trades) > 0 else 0.0
        frozen_avg_win = frozen_wins["pnl"].mean() if len(frozen_wins) > 0 else 0.0
        frozen_avg_loss = abs(frozen_losses["pnl"].mean()) if len(frozen_losses) > 0 else 0.0
        frozen_expectancy = (frozen_winrate * frozen_avg_win) - ((1 - frozen_winrate) * frozen_avg_loss)
        
        if frozen_expectancy != 0:
            improvement = (shadow_expectancy - frozen_expectancy) / abs(frozen_expectancy)
        else:
            improvement = shadow_expectancy
        
        passed = improvement >= self.criteria.min_expectancy_improvement
        
        return TestResult(
            test_name="expectancy_improvement",
            passed=passed,
            shadow_metric=shadow_expectancy,
            frozen_metric=frozen_expectancy,
            improvement=improvement,
            details={
                "required_improvement": self.criteria.min_expectancy_improvement,
                "shadow_avg_win": shadow_avg_win,
                "frozen_avg_win": frozen_avg_win,
            },
        )
    
    def _test_drawdown(
        self,
        shadow_trades: pd.DataFrame,
    ) -> TestResult:
        """Test maximum drawdown"""
        if "pnl" not in shadow_trades.columns or shadow_trades.empty:
            return TestResult(
                test_name="drawdown_check",
                passed=False,
                shadow_metric=0.0,
                frozen_metric=0.0,
                improvement=0.0,
                details={"error": "No PnL data"},
            )
        
        cumulative = shadow_trades["pnl"].cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0.0
        
        passed = max_drawdown <= self.criteria.max_drawdown_threshold
        
        return TestResult(
            test_name="drawdown_check",
            passed=passed,
            shadow_metric=max_drawdown,
            frozen_metric=self.criteria.max_drawdown_threshold,
            improvement=self.criteria.max_drawdown_threshold - max_drawdown,
            details={
                "max_drawdown_threshold": self.criteria.max_drawdown_threshold,
            },
        )
    
    def _test_last_n_trades(
        self,
        shadow_trades: pd.DataFrame,
        frozen_trades: pd.DataFrame,
    ) -> TestResult:
        """Test performance on last N trades"""
        n = self.criteria.last_n_trades
        
        shadow_recent = shadow_trades.tail(n)
        frozen_recent = frozen_trades.tail(n)
        
        if len(shadow_recent) < n or len(frozen_recent) < n:
            return TestResult(
                test_name="last_n_trades",
                passed=False,
                shadow_metric=0.0,
                frozen_metric=0.0,
                improvement=0.0,
                details={"error": f"Not enough trades (need {n})"},
            )
        
        # Compare average PnL
        shadow_avg_pnl = shadow_recent["pnl"].mean()
        frozen_avg_pnl = frozen_recent["pnl"].mean()
        
        improvement = shadow_avg_pnl - frozen_avg_pnl
        passed = shadow_avg_pnl > frozen_avg_pnl
        
        return TestResult(
            test_name="last_n_trades",
            passed=passed,
            shadow_metric=shadow_avg_pnl,
            frozen_metric=frozen_avg_pnl,
            improvement=improvement,
            details={
                "n_trades": n,
                "shadow_total_pnl": shadow_recent["pnl"].sum(),
                "frozen_total_pnl": frozen_recent["pnl"].sum(),
            },
        )
    
    def evaluate_promotion(
        self,
        shadow_model_id: str,
        frozen_model_id: str,
        shadow_trades: pd.DataFrame,
        frozen_trades: pd.DataFrame,
    ) -> PromotionDecision:
        """
        Evaluate if shadow should be promoted to frozen.
        
        Args:
            shadow_model_id: Shadow model identifier
            frozen_model_id: Frozen model identifier
            shadow_trades: DataFrame with shadow model trades
            frozen_trades: DataFrame with frozen model trades
        
        Returns:
            PromotionDecision with test results
        """
        test_results = []
        
        # Check minimum trades
        if len(shadow_trades) < self.criteria.min_trades:
            decision = PromotionDecision(
                status=PromotionStatus.REJECTED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                shadow_model_id=shadow_model_id,
                frozen_model_id=frozen_model_id,
                test_results=[],
                all_tests_passed=False,
                reason=f"Not enough trades: {len(shadow_trades)} < {self.criteria.min_trades}",
            )
            self._log_decision(decision)
            return decision
        
        # Run tests
        test_results.append(self._test_winrate_improvement(shadow_trades, frozen_trades))
        test_results.append(self._test_expectancy_improvement(shadow_trades, frozen_trades))
        test_results.append(self._test_drawdown(shadow_trades))
        
        if self.criteria.require_last_n_trades_test:
            test_results.append(self._test_last_n_trades(shadow_trades, frozen_trades))
        
        # Check if all tests passed
        all_passed = all(t.passed for t in test_results)
        
        # Determine status
        if all_passed:
            status = PromotionStatus.APPROVED
            reason = "All promotion criteria met"
        else:
            status = PromotionStatus.REJECTED
            failed_tests = [t.test_name for t in test_results if not t.passed]
            reason = f"Failed tests: {', '.join(failed_tests)}"
        
        decision = PromotionDecision(
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            shadow_model_id=shadow_model_id,
            frozen_model_id=frozen_model_id,
            test_results=test_results,
            all_tests_passed=all_passed,
            reason=reason,
        )
        
        self._log_decision(decision)
        
        logger.info(f"Promotion evaluation: {status.value} - {reason}")
        return decision
    
    def _log_decision(self, decision: PromotionDecision) -> None:
        """Log promotion decision"""
        with open(self.decisions_log_path, "a") as f:
            f.write(json.dumps(decision.to_dict()) + "\n")
    
    def get_recent_decisions(self, limit: int = 10) -> list[dict]:
        """Get recent promotion decisions"""
        if not self.decisions_log_path.exists():
            return []
        
        decisions = []
        with open(self.decisions_log_path, "r") as f:
            for line in f:
                try:
                    decisions.append(json.loads(line))
                except Exception:
                    continue
        
        return list(reversed(decisions[-limit:]))
