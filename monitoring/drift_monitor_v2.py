"""
Enhanced drift monitor v2.

Extends beyond winrate to include:
- Expectancy
- Average PnL
- Loss streak
- Drawdown slope
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import json
from pathlib import Path


@dataclass
class DriftMetrics:
    """
    Comprehensive drift metrics.
    
    Attributes:
        timestamp: When metrics were computed
        winrate: Win rate (existing)
        expectancy: Expected value per trade
        avg_pnl: Average profit/loss per trade
        loss_streak: Current consecutive losses
        max_loss_streak: Maximum consecutive losses
        drawdown_slope: Rate of drawdown change
        total_trades: Total number of trades
        winning_trades: Number of winning trades
        losing_trades: Number of losing trades
    """
    timestamp: str
    winrate: float
    expectancy: float
    avg_pnl: float
    loss_streak: int
    max_loss_streak: int
    drawdown_slope: float
    total_trades: int
    winning_trades: int
    losing_trades: int


class DriftMonitorV2:
    """
    Enhanced drift monitor with comprehensive metrics.
    
    Monitors model performance degradation across multiple dimensions:
    - Win rate (traditional)
    - Expectancy (expected value)
    - Average PnL (profitability)
    - Loss streaks (risk management)
    - Drawdown slope (capital preservation)
    """
    
    def __init__(self, window_size: int = 100):
        """
        Initialize drift monitor.
        
        Args:
            window_size: Number of recent trades to consider
        """
        self.window_size = window_size
        self._trade_history: list[dict] = []
    
    def add_trade(
        self,
        pnl: float,
        is_win: bool,
        timestamp: Optional[str] = None
    ) -> None:
        """
        Add trade result to history.
        
        Args:
            pnl: Trade profit/loss
            is_win: Whether trade was a win
            timestamp: Trade timestamp (uses now if not provided)
        """
        trade = {
            "pnl": float(pnl),
            "is_win": bool(is_win),
            "timestamp": timestamp or datetime.now(timezone.utc).isoformat()
        }
        
        self._trade_history.append(trade)
        
        # Keep only recent window
        if len(self._trade_history) > self.window_size:
            self._trade_history = self._trade_history[-self.window_size:]
    
    def compute_metrics(self) -> Optional[DriftMetrics]:
        """
        Compute comprehensive drift metrics.
        
        Returns:
            DriftMetrics if enough data, None otherwise
        """
        if len(self._trade_history) == 0:
            return None
        
        # Basic counts
        total_trades = len(self._trade_history)
        winning_trades = sum(1 for t in self._trade_history if t["is_win"])
        losing_trades = total_trades - winning_trades
        
        # Win rate
        winrate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Average PnL
        pnls = [t["pnl"] for t in self._trade_history]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        
        # Expectancy (average win * win_rate - average loss * loss_rate)
        wins = [t["pnl"] for t in self._trade_history if t["is_win"]]
        losses = [abs(t["pnl"]) for t in self._trade_history if not t["is_win"]]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        loss_rate = 1.0 - winrate
        
        expectancy = (avg_win * winrate) - (avg_loss * loss_rate)
        
        # Loss streaks
        current_loss_streak = 0
        max_loss_streak = 0
        temp_streak = 0
        
        for trade in reversed(self._trade_history):
            if not trade["is_win"]:
                temp_streak += 1
                if current_loss_streak == 0:
                    current_loss_streak = temp_streak
                max_loss_streak = max(max_loss_streak, temp_streak)
            else:
                temp_streak = 0
        
        # Drawdown slope (rate of capital decline)
        drawdown_slope = self._compute_drawdown_slope()
        
        return DriftMetrics(
            timestamp=datetime.now(timezone.utc).isoformat(),
            winrate=winrate,
            expectancy=expectancy,
            avg_pnl=avg_pnl,
            loss_streak=current_loss_streak,
            max_loss_streak=max_loss_streak,
            drawdown_slope=drawdown_slope,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    
    def _compute_drawdown_slope(self) -> float:
        """
        Compute drawdown slope (rate of capital decline).
        
        Returns:
            Slope of drawdown curve (negative = declining)
        """
        if len(self._trade_history) < 2:
            return 0.0
        
        # Compute cumulative PnL
        cumulative_pnl = []
        running_sum = 0.0
        
        for trade in self._trade_history:
            running_sum += trade["pnl"]
            cumulative_pnl.append(running_sum)
        
        # Compute peak and current drawdown
        peak = max(cumulative_pnl)
        current = cumulative_pnl[-1]
        drawdown = current - peak
        
        # Compute slope over recent window (last 20% of trades)
        lookback = max(2, len(cumulative_pnl) // 5)
        recent_pnl = cumulative_pnl[-lookback:]
        
        if len(recent_pnl) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(recent_pnl)
        x = list(range(n))
        y = recent_pnl
        
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0.0
        
        return float(slope)
    
    def is_drifting(
        self,
        min_winrate: float = 0.45,
        min_expectancy: float = 0.0,
        max_loss_streak: int = 5,
        max_drawdown_slope: float = -10.0
    ) -> tuple[bool, list[str]]:
        """
        Check if model is experiencing drift.
        
        Args:
            min_winrate: Minimum acceptable win rate
            min_expectancy: Minimum acceptable expectancy
            max_loss_streak: Maximum acceptable loss streak
            max_drawdown_slope: Maximum acceptable drawdown slope (negative)
            
        Returns:
            Tuple of (is_drifting, reasons)
        """
        metrics = self.compute_metrics()
        
        if metrics is None:
            return False, ["INSUFFICIENT_DATA"]
        
        reasons = []
        
        if metrics.winrate < min_winrate:
            reasons.append(f"LOW_WINRATE ({metrics.winrate:.3f} < {min_winrate})")
        
        if metrics.expectancy < min_expectancy:
            reasons.append(f"LOW_EXPECTANCY ({metrics.expectancy:.3f} < {min_expectancy})")
        
        if metrics.loss_streak > max_loss_streak:
            reasons.append(f"HIGH_LOSS_STREAK ({metrics.loss_streak} > {max_loss_streak})")
        
        if metrics.drawdown_slope < max_drawdown_slope:
            reasons.append(f"STEEP_DRAWDOWN ({metrics.drawdown_slope:.3f} < {max_drawdown_slope})")
        
        is_drifting = len(reasons) > 0
        
        return is_drifting, reasons
    
    def save_metrics(self, path: str | Path) -> None:
        """
        Save current metrics to disk.
        
        Args:
            path: Path to save metrics
        """
        metrics = self.compute_metrics()
        
        if metrics is None:
            return
        
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        metrics_dict = {
            "timestamp": metrics.timestamp,
            "winrate": metrics.winrate,
            "expectancy": metrics.expectancy,
            "avg_pnl": metrics.avg_pnl,
            "loss_streak": metrics.loss_streak,
            "max_loss_streak": metrics.max_loss_streak,
            "drawdown_slope": metrics.drawdown_slope,
            "total_trades": metrics.total_trades,
            "winning_trades": metrics.winning_trades,
            "losing_trades": metrics.losing_trades
        }
        
        # Append to metrics log
        with open(p, "a") as f:
            f.write(json.dumps(metrics_dict) + "\n")
    
    @classmethod
    def load_history(cls, path: str | Path, window_size: int = 100) -> "DriftMonitorV2":
        """
        Load drift monitor from saved metrics.
        
        Args:
            path: Path to metrics log
            window_size: Size of monitoring window
            
        Returns:
            DriftMonitorV2 instance with loaded history
        """
        monitor = cls(window_size=window_size)
        
        p = Path(path)
        if not p.exists():
            return monitor
        
        try:
            with open(p, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Reconstruct trades from metrics
                        # This is approximate - ideally store full trade history
                        monitor._trade_history.append({
                            "pnl": data.get("avg_pnl", 0.0),
                            "is_win": data.get("winrate", 0.5) > 0.5,
                            "timestamp": data.get("timestamp")
                        })
                    except Exception:
                        continue
        except Exception:
            pass
        
        return monitor
