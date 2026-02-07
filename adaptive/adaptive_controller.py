"""Adaptive Controller - Orchestrates the learning loop

Paper trade → learning loop:
1. Paper trade opens → snapshot features_at_entry
2. Trade closes → outcome label
3. Send to shadow trainer → learn_one()
4. Log metrics
5. Check drift
6. Evaluate promotion (if criteria met)

READ ONLY consumer of paper trading artifacts.
Does NOT modify paper trading behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from adaptive.dual_model import DualModelManager, ModelMetadata
from adaptive.feature_store import FeatureStore
from adaptive.shadow_learner import ShadowLearner, LearningConfig
from adaptive.drift_monitor import DriftMonitor, DriftConfig
from adaptive.promotion_gate import PromotionGate, PromotionCriteria

logger = logging.getLogger(__name__)


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive system"""
    adaptive_logs_dir: Path
    model_registry_dir: Path
    learning_config: LearningConfig
    drift_config: DriftConfig
    promotion_criteria: PromotionCriteria
    
    @classmethod
    def default(cls, base_dir: Path) -> AdaptiveConfig:
        """Create default configuration"""
        adaptive_logs_dir = base_dir / "adaptive_logs"
        model_registry_dir = base_dir / "adaptive_models"
        
        return cls(
            adaptive_logs_dir=adaptive_logs_dir,
            model_registry_dir=model_registry_dir,
            learning_config=LearningConfig(),
            drift_config=DriftConfig(),
            promotion_criteria=PromotionCriteria(),
        )


class AdaptiveController:
    """
    Main controller for adaptive learning system.
    
    Orchestrates:
    - Feature logging from paper trades
    - Shadow model online learning
    - Drift monitoring
    - Model promotion evaluation
    
    CRITICAL: This is READ ONLY consumer of paper artifacts.
    """
    
    def __init__(self, config: AdaptiveConfig):
        """
        Initialize adaptive controller.
        
        Args:
            config: Adaptive system configuration
        """
        self.config = config
        
        # Create directories
        config.adaptive_logs_dir.mkdir(parents=True, exist_ok=True)
        config.model_registry_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.model_manager = DualModelManager(config.model_registry_dir)
        
        self.feature_store = FeatureStore(
            store_dir=config.adaptive_logs_dir / "features"
        )
        
        self.shadow_learner = ShadowLearner(
            config=config.learning_config,
            model_dir=config.model_registry_dir / "shadow",
        )
        
        self.drift_monitor = DriftMonitor(
            config=config.drift_config,
            metrics_dir=config.adaptive_logs_dir / "metrics",
        )
        
        self.promotion_gate = PromotionGate(
            criteria=config.promotion_criteria,
            decisions_dir=config.adaptive_logs_dir / "decisions",
        )
        
        logger.info("Adaptive controller initialized")
    
    def initialize_from_frozen_model(
        self,
        frozen_model_id: str,
        frozen_artifact_path: Path,
        frozen_model_card_path: Optional[Path] = None,
    ) -> tuple[bool, str]:
        """
        Initialize adaptive system with frozen (production) model.
        
        Args:
            frozen_model_id: Frozen model identifier
            frozen_artifact_path: Path to frozen model artifact
            frozen_model_card_path: Optional path to model card
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Initialize frozen model
            frozen_meta = self.model_manager.initialize_frozen(
                model_id=frozen_model_id,
                artifact_path=frozen_artifact_path,
                model_card_path=frozen_model_card_path,
            )
            
            # Create shadow from frozen
            shadow_meta = self.model_manager.create_shadow_from_frozen()
            
            if not shadow_meta:
                return False, "Failed to create shadow model"
            
            msg = f"Initialized adaptive system: frozen={frozen_model_id}, shadow={shadow_meta.model_id}"
            logger.info(msg)
            return True, msg
            
        except Exception as e:
            msg = f"Failed to initialize: {e}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def set_frozen_baseline_from_trades(
        self,
        trades_df: pd.DataFrame,
    ) -> tuple[bool, str]:
        """
        Set frozen model baseline from historical trades.
        
        Args:
            trades_df: DataFrame with frozen model trades
        
        Returns:
            Tuple of (success, message)
        """
        try:
            metrics = self.drift_monitor.set_frozen_baseline(trades_df)
            msg = f"Set frozen baseline: winrate={metrics.winrate:.3f}, expectancy={metrics.expectancy:.3f}"
            logger.info(msg)
            return True, msg
        except Exception as e:
            msg = f"Failed to set baseline: {e}"
            logger.error(msg)
            return False, msg
    
    def process_paper_trade(
        self,
        trade_id: str,
        features_at_entry: dict,
        prediction: str,
        confidence: float,
        features_at_exit: Optional[dict] = None,
        outcome: Optional[str] = None,
        pnl: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        Process a completed paper trade for shadow learning.
        
        This is the core learning loop:
        1. Log features
        2. If trade complete, add to learning queue
        3. Trigger shadow learning if criteria met
        4. Check drift
        5. Log metrics
        
        Args:
            trade_id: Unique trade identifier
            features_at_entry: Features when trade opened
            prediction: Model prediction
            confidence: Prediction confidence
            features_at_exit: Features when trade closed
            outcome: Trade outcome ("win", "loss", "breakeven")
            pnl: Profit/loss
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Log features
            logged = self.feature_store.log_trade_features(
                trade_id=trade_id,
                features_at_entry=features_at_entry,
                prediction=prediction,
                confidence=confidence,
                features_at_exit=features_at_exit,
                outcome=outcome,
                pnl=pnl,
            )
            
            if not logged:
                return False, "Failed to log trade features"
            
            # If trade is complete, trigger learning
            if outcome and pnl is not None:
                return self._trigger_shadow_learning()
            
            return True, "Trade features logged"
            
        except Exception as e:
            msg = f"Failed to process paper trade: {e}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def _trigger_shadow_learning(self) -> tuple[bool, str]:
        """
        Trigger shadow model learning from accumulated trades.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Get features for learning
            trades_df = self.feature_store.get_features_for_learning(
                min_trades=self.config.learning_config.min_trades_before_update,
            )
            
            if trades_df.empty:
                return True, "Not enough trades for learning yet"
            
            # Check if learner can update (rate limiting)
            can_update, reason = self.shadow_learner.can_update(len(trades_df))
            if not can_update:
                return True, f"Learning skipped: {reason}"
            
            # Perform learning
            success, update = self.shadow_learner.learn_from_trades(trades_df)
            
            if not success:
                return False, "Shadow learning failed"
            
            # Update shadow metrics
            shadow_metrics = self.drift_monitor.update_shadow_metrics(trades_df)
            
            # Check drift
            has_drifted, drift_reason, _ = self.drift_monitor.check_drift(shadow_metrics)
            
            if has_drifted and self.config.drift_config.auto_pause_on_drift:
                self.shadow_learner.pause()
                msg = f"Shadow learning paused due to drift: {drift_reason}"
                logger.warning(msg)
                return True, msg
            
            msg = f"Shadow learning complete: {update.trades_processed} trades processed"
            logger.info(msg)
            return True, msg
            
        except Exception as e:
            msg = f"Shadow learning trigger failed: {e}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def evaluate_promotion(self) -> tuple[bool, str, Optional[dict]]:
        """
        Evaluate if shadow should be promoted to frozen.
        
        Returns:
            Tuple of (should_promote, reason, decision_dict)
        """
        try:
            frozen_meta = self.model_manager.get_frozen_metadata()
            shadow_meta = self.model_manager.get_shadow_metadata()
            
            if not frozen_meta or not shadow_meta:
                return False, "Models not initialized", None
            
            # Get trade data for both models
            # In real implementation, this would load actual trade logs
            # For now, we simulate with feature store data
            trades_df = self.feature_store.get_features_for_learning()
            
            if trades_df.empty:
                return False, "No trade data for evaluation", None
            
            # For this skeleton, use same data for both (in real system, separate logs)
            decision = self.promotion_gate.evaluate_promotion(
                shadow_model_id=shadow_meta.model_id,
                frozen_model_id=frozen_meta.model_id,
                shadow_trades=trades_df,
                frozen_trades=trades_df,
            )
            
            should_promote = decision.all_tests_passed
            return should_promote, decision.reason, decision.to_dict()
            
        except Exception as e:
            msg = f"Promotion evaluation failed: {e}"
            logger.error(msg, exc_info=True)
            return False, msg, None
    
    def promote_shadow_to_frozen(self) -> tuple[bool, str]:
        """
        Promote shadow model to frozen (production).
        Should only be called after evaluate_promotion() returns True.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            success, msg = self.model_manager.promote_shadow_to_frozen()
            
            if success:
                # Create new shadow from new frozen
                self.model_manager.create_shadow_from_frozen()
            
            return success, msg
            
        except Exception as e:
            msg = f"Promotion failed: {e}"
            logger.error(msg, exc_info=True)
            return False, msg
    
    def get_status(self) -> dict:
        """Get comprehensive status of adaptive system"""
        frozen_meta = self.model_manager.get_frozen_metadata()
        shadow_meta = self.model_manager.get_shadow_metadata()
        
        return {
            "frozen_model": frozen_meta.to_dict() if frozen_meta else None,
            "shadow_model": shadow_meta.to_dict() if shadow_meta else None,
            "learner_stats": self.shadow_learner.get_stats(),
            "feature_store_stats": self.feature_store.get_stats(),
            "drift_comparison": self.drift_monitor.get_comparison(),
            "recent_decisions": self.promotion_gate.get_recent_decisions(limit=5),
        }
    
    def pause_learning(self) -> None:
        """Pause shadow learning"""
        self.shadow_learner.pause()
        logger.info("Shadow learning paused")
    
    def resume_learning(self) -> None:
        """Resume shadow learning"""
        self.shadow_learner.resume()
        logger.info("Shadow learning resumed")
