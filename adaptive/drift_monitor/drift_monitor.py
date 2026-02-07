"""Drift Monitor - Phase 5

Monitors shadow model quality with rolling metrics.
Auto-pauses learning if shadow degrades below frozen.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DriftMetrics:
    """Drift metrics for a model"""
    timestamp: str
    model_id: str
    window_size: int
    trades_in_window: int
    winrate: float
    expectancy: float
    avg_pnl: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "model_id": self.model_id,
            "window_size": self.window_size,
            "trades_in_window": self.trades_in_window,
            "winrate": self.winrate,
            "expectancy": self.expectancy,
            "avg_pnl": self.avg_pnl,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }


@dataclass
class DriftConfig:
    """Configuration for drift monitoring"""
    rolling_window: int = 50
    min_trades_for_drift_check: int = 20
    winrate_tolerance: float = 0.05  # 5% worse allowed
    expectancy_tolerance: float = 0.10  # 10% worse allowed
    auto_pause_on_drift: bool = True
    
    def to_dict(self) -> dict:
        return {
            "rolling_window": self.rolling_window,
            "min_trades_for_drift_check": self.min_trades_for_drift_check,
            "winrate_tolerance": self.winrate_tolerance,
            "expectancy_tolerance": self.expectancy_tolerance,
            "auto_pause_on_drift": self.auto_pause_on_drift,
        }


class DriftMonitor:
    """
    Monitors shadow model performance vs frozen model.
    
    Key features:
    - Rolling window metrics (winrate, expectancy)
    - Comparison with frozen model baseline
    - Auto-pause if shadow degrades
    - Drift alert system
    """
    
    def __init__(
        self,
        config: DriftConfig,
        metrics_dir: Path,
    ):
        """
        Initialize drift monitor.
        
        Args:
            config: Drift monitoring configuration
            metrics_dir: Directory for metrics storage
        """
        self.config = config
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.shadow_metrics_path = self.metrics_dir / "shadow_metrics.json"
        self.frozen_metrics_path = self.metrics_dir / "frozen_metrics.json"
        self.drift_alerts_path = self.metrics_dir / "drift_alerts.jsonl"
        
        # Rolling windows for shadow and frozen
        self._shadow_window: deque = deque(maxlen=config.rolling_window)
        self._frozen_window: deque = deque(maxlen=config.rolling_window)
        
        self._frozen_baseline: Optional[DriftMetrics] = None
    
    def set_frozen_baseline(self, trades_df: pd.DataFrame) -> DriftMetrics:
        """
        Set frozen model baseline from historical trades.
        
        Args:
            trades_df: DataFrame with frozen model trades (columns: pnl, outcome)
        
        Returns:
            DriftMetrics for frozen baseline
        """
        metrics = self._compute_metrics(
            trades_df=trades_df,
            model_id="frozen_baseline",
        )
        
        self._frozen_baseline = metrics
        
        # Save to disk
        self.frozen_metrics_path.write_text(json.dumps(metrics.to_dict(), indent=2))
        
        logger.info(
            f"Set frozen baseline: winrate={metrics.winrate:.3f}, "
            f"expectancy={metrics.expectancy:.3f}"
        )
        
        return metrics
    
    def _compute_metrics(
        self,
        trades_df: pd.DataFrame,
        model_id: str,
    ) -> DriftMetrics:
        """
        Compute metrics from trades DataFrame.
        
        Args:
            trades_df: DataFrame with columns: pnl, outcome
            model_id: Model identifier
        
        Returns:
            DriftMetrics
        """
        if trades_df.empty:
            return DriftMetrics(
                timestamp=datetime.now(timezone.utc).isoformat(),
                model_id=model_id,
                window_size=self.config.rolling_window,
                trades_in_window=0,
                winrate=0.0,
                expectancy=0.0,
                avg_pnl=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
            )
        
        # Winrate
        wins = (trades_df["outcome"] == "win").sum()
        winrate = wins / len(trades_df) if len(trades_df) > 0 else 0.0
        
        # Expectancy
        avg_pnl = trades_df["pnl"].mean() if "pnl" in trades_df.columns else 0.0
        
        # Separate wins and losses for expectancy
        wins_df = trades_df[trades_df["outcome"] == "win"]
        losses_df = trades_df[trades_df["outcome"] == "loss"]
        
        avg_win = wins_df["pnl"].mean() if len(wins_df) > 0 and "pnl" in wins_df.columns else 0.0
        avg_loss = abs(losses_df["pnl"].mean()) if len(losses_df) > 0 and "pnl" in losses_df.columns else 0.0
        
        # Expectancy = (WinRate * AvgWin) - (LossRate * AvgLoss)
        loss_rate = 1.0 - winrate
        expectancy = (winrate * avg_win) - (loss_rate * avg_loss)
        
        # Max drawdown
        if "pnl" in trades_df.columns:
            cumulative = trades_df["pnl"].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            max_drawdown = drawdown.min() if len(drawdown) > 0 else 0.0
        else:
            max_drawdown = 0.0
        
        # Sharpe ratio (simplified)
        sharpe = None
        if "pnl" in trades_df.columns and len(trades_df) > 1:
            std = trades_df["pnl"].std()
            if std > 0:
                sharpe = (avg_pnl / std) * (252 ** 0.5)  # Annualized
        
        return DriftMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            model_id=model_id,
            window_size=self.config.rolling_window,
            trades_in_window=len(trades_df),
            winrate=float(winrate),
            expectancy=float(expectancy),
            avg_pnl=float(avg_pnl),
            max_drawdown=float(max_drawdown),
            sharpe_ratio=float(sharpe) if sharpe is not None else None,
        )
    
    def update_shadow_metrics(self, trades_df: pd.DataFrame) -> DriftMetrics:
        """
        Update shadow model metrics from recent trades.
        
        Args:
            trades_df: DataFrame with shadow model trades
        
        Returns:
            DriftMetrics for shadow
        """
        # Take last N trades for rolling window
        if len(trades_df) > self.config.rolling_window:
            trades_df = trades_df.tail(self.config.rolling_window)
        
        metrics = self._compute_metrics(
            trades_df=trades_df,
            model_id="shadow",
        )
        
        # Save to disk
        self.shadow_metrics_path.write_text(json.dumps(metrics.to_dict(), indent=2))
        
        logger.info(
            f"Shadow metrics: winrate={metrics.winrate:.3f}, "
            f"expectancy={metrics.expectancy:.3f}"
        )
        
        return metrics
    
    def check_drift(
        self,
        shadow_metrics: DriftMetrics,
    ) -> tuple[bool, str, dict]:
        """
        Check if shadow has drifted below acceptable threshold.
        
        Args:
            shadow_metrics: Current shadow metrics
        
        Returns:
            Tuple of (has_drifted, reason, details)
        """
        if not self._frozen_baseline:
            return False, "No frozen baseline set", {}
        
        # Need minimum trades
        if shadow_metrics.trades_in_window < self.config.min_trades_for_drift_check:
            return False, "Not enough trades for drift check", {}
        
        # Check winrate drift
        winrate_diff = shadow_metrics.winrate - self._frozen_baseline.winrate
        winrate_drifted = winrate_diff < -self.config.winrate_tolerance
        
        # Check expectancy drift
        if self._frozen_baseline.expectancy != 0:
            expectancy_ratio = shadow_metrics.expectancy / self._frozen_baseline.expectancy
            expectancy_drifted = expectancy_ratio < (1.0 - self.config.expectancy_tolerance)
        else:
            expectancy_drifted = shadow_metrics.expectancy < -self.config.expectancy_tolerance
        
        details = {
            "shadow_winrate": shadow_metrics.winrate,
            "frozen_winrate": self._frozen_baseline.winrate,
            "winrate_diff": winrate_diff,
            "winrate_drifted": winrate_drifted,
            "shadow_expectancy": shadow_metrics.expectancy,
            "frozen_expectancy": self._frozen_baseline.expectancy,
            "expectancy_drifted": expectancy_drifted,
        }
        
        if winrate_drifted or expectancy_drifted:
            reasons = []
            if winrate_drifted:
                reasons.append(
                    f"Winrate degraded: {shadow_metrics.winrate:.3f} vs "
                    f"{self._frozen_baseline.winrate:.3f} (diff: {winrate_diff:.3f})"
                )
            if expectancy_drifted:
                reasons.append(
                    f"Expectancy degraded: {shadow_metrics.expectancy:.3f} vs "
                    f"{self._frozen_baseline.expectancy:.3f}"
                )
            
            reason = "; ".join(reasons)
            
            # Log drift alert
            self._log_drift_alert(reason, details)
            
            return True, reason, details
        
        return False, "No drift detected", details
    
    def _log_drift_alert(self, reason: str, details: dict) -> None:
        """Log drift alert"""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "alert_type": "drift_detected",
            "reason": reason,
            "details": details,
        }
        
        with open(self.drift_alerts_path, "a") as f:
            f.write(json.dumps(alert) + "\n")
        
        logger.warning(f"DRIFT ALERT: {reason}")
    
    def get_comparison(self) -> dict:
        """
        Get comparison between shadow and frozen.
        
        Returns:
            Dictionary with comparison metrics
        """
        if not self._frozen_baseline:
            return {"error": "No frozen baseline"}
        
        shadow_metrics = None
        if self.shadow_metrics_path.exists():
            try:
                shadow_metrics = DriftMetrics(**json.loads(self.shadow_metrics_path.read_text()))
            except Exception:
                pass
        
        if not shadow_metrics:
            return {"error": "No shadow metrics"}
        
        has_drifted, reason, details = self.check_drift(shadow_metrics)
        
        return {
            "frozen": self._frozen_baseline.to_dict(),
            "shadow": shadow_metrics.to_dict(),
            "drift_detected": has_drifted,
            "drift_reason": reason,
            "comparison": details,
        }
    
    def get_recent_alerts(self, limit: int = 10) -> list[dict]:
        """Get recent drift alerts"""
        if not self.drift_alerts_path.exists():
            return []
        
        alerts = []
        with open(self.drift_alerts_path, "r") as f:
            for line in f:
                try:
                    alerts.append(json.loads(line))
                except Exception:
                    continue
        
        return list(reversed(alerts[-limit:]))
