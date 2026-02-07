"""
Adaptive backtester for shadow model evaluation.

Tests shadow models separately from main backtest to ensure isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import pandas as pd

from adaptive.shadow_model import ShadowModel


@dataclass
class AdaptiveBacktestResult:
    """Result of adaptive backtest."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    winrate: float
    avg_pnl: float
    expectancy: float
    max_drawdown: float
    sharpe_ratio: float
    final_balance: float
    model_updates: int


class AdaptiveBacktester:
    """
    Backtester for adaptive/shadow models.
    
    Key differences from main backtest:
    - Supports online learning during backtest
    - Tracks model evolution
    - Isolated from production backtest
    - Tests shadow model promotion criteria
    """
    
    def __init__(
        self,
        shadow_model_path: str | Path,
        initial_balance: float = 10000.0
    ):
        """
        Initialize adaptive backtester.
        
        Args:
            shadow_model_path: Path to shadow model
            initial_balance: Starting capital
        """
        self.shadow_model_path = Path(shadow_model_path)
        self.initial_balance = initial_balance
        self.shadow_model: Optional[ShadowModel] = None
    
    def load_shadow_model(self) -> None:
        """Load shadow model for testing."""
        if self.shadow_model_path.exists():
            self.shadow_model = ShadowModel.load(self.shadow_model_path)
        else:
            # Create new shadow model for testing
            self.shadow_model = ShadowModel()
    
    def run_backtest(
        self,
        features_df: pd.DataFrame,
        labels_df: pd.DataFrame,
        enable_learning: bool = True
    ) -> AdaptiveBacktestResult:
        """
        Run adaptive backtest with optional learning.
        
        Args:
            features_df: DataFrame with features (one row per trade opportunity)
            labels_df: DataFrame with labels (actual outcomes)
            enable_learning: Whether to update model during backtest
            
        Returns:
            AdaptiveBacktestResult with performance metrics
        """
        if self.shadow_model is None:
            self.load_shadow_model()
        
        balance = self.initial_balance
        trades = []
        model_updates = 0
        
        peak_balance = balance
        max_drawdown = 0.0
        
        for idx in range(len(features_df)):
            # Get features and label for this trade
            features = features_df.iloc[idx].to_dict()
            label = int(labels_df.iloc[idx])
            
            # Predict
            score = self.shadow_model.predict_proba(features)
            
            # Simple threshold-based trading
            threshold = 0.6
            if score >= threshold:
                # Take trade
                pnl = 100.0 if label == 1 else -50.0  # Simplified PnL
                balance += pnl
                
                is_win = pnl > 0
                trades.append({
                    "pnl": pnl,
                    "is_win": is_win,
                    "score": score
                })
                
                # Update model if learning enabled
                if enable_learning:
                    self.shadow_model.learn_one(features, label)
                    model_updates += 1
                
                # Track drawdown
                peak_balance = max(peak_balance, balance)
                drawdown = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        # Compute metrics
        if not trades:
            return AdaptiveBacktestResult(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                winrate=0.0,
                avg_pnl=0.0,
                expectancy=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                final_balance=balance,
                model_updates=model_updates
            )
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t["is_win"])
        losing_trades = total_trades - winning_trades
        
        winrate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        pnls = [t["pnl"] for t in trades]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0
        
        wins = [t["pnl"] for t in trades if t["is_win"]]
        losses = [abs(t["pnl"]) for t in trades if not t["is_win"]]
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        loss_rate = 1.0 - winrate
        
        expectancy = (avg_win * winrate) - (avg_loss * loss_rate)
        
        # Sharpe ratio (simplified)
        if len(pnls) > 1:
            std_pnl = pd.Series(pnls).std()
            sharpe_ratio = (avg_pnl / std_pnl) if std_pnl > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return AdaptiveBacktestResult(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            winrate=winrate,
            avg_pnl=avg_pnl,
            expectancy=expectancy,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            final_balance=balance,
            model_updates=model_updates
        )
    
    def compare_frozen_vs_adaptive(
        self,
        features_df: pd.DataFrame,
        labels_df: pd.DataFrame,
        frozen_model_path: str | Path
    ) -> dict:
        """
        Compare frozen model vs adaptive model performance.
        
        Args:
            features_df: Feature data
            labels_df: Label data
            frozen_model_path: Path to frozen model
            
        Returns:
            Dictionary with comparison results
        """
        # Test frozen model (no learning)
        self.shadow_model_path = Path(frozen_model_path)
        frozen_result = self.run_backtest(
            features_df=features_df,
            labels_df=labels_df,
            enable_learning=False
        )
        
        # Test adaptive model (with learning)
        self.load_shadow_model()
        adaptive_result = self.run_backtest(
            features_df=features_df,
            labels_df=labels_df,
            enable_learning=True
        )
        
        return {
            "frozen": {
                "winrate": frozen_result.winrate,
                "expectancy": frozen_result.expectancy,
                "final_balance": frozen_result.final_balance,
                "sharpe_ratio": frozen_result.sharpe_ratio
            },
            "adaptive": {
                "winrate": adaptive_result.winrate,
                "expectancy": adaptive_result.expectancy,
                "final_balance": adaptive_result.final_balance,
                "sharpe_ratio": adaptive_result.sharpe_ratio,
                "model_updates": adaptive_result.model_updates
            },
            "improvement": {
                "winrate_delta": adaptive_result.winrate - frozen_result.winrate,
                "expectancy_delta": adaptive_result.expectancy - frozen_result.expectancy,
                "balance_delta": adaptive_result.final_balance - frozen_result.final_balance
            }
        }
