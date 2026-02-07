"""
Shadow model pipeline integration example.

Demonstrates the complete shadow model workflow:
1. frozen_model → copy → shadow_model
2. shadow_model.learn_one()
3. registry save
4. promotion gate
5. rollback

This module is NOT connected to execution - it's for offline training only.
"""

from pathlib import Path
from typing import Optional
from adaptive.shadow_model import ShadowModel
from adaptive.online_trainer import OnlineTrainer


class ShadowModelPipeline:
    """
    Complete shadow model pipeline orchestration.
    
    This pipeline ensures:
    - Shadow models never affect live trading
    - All learning happens in isolation
    - Promotion only happens after validation
    - Rollback is always available
    """
    
    def __init__(
        self,
        frozen_model_path: str | Path = "ai_data/models/frozen_model.pkl",
        shadow_model_path: str | Path = "ai_data/models/shadow_model.pkl",
        registry_path: str | Path = "ai_data/adaptive/training_registry.jsonl"
    ):
        """
        Initialize shadow model pipeline.
        
        Args:
            frozen_model_path: Path to frozen production model
            shadow_model_path: Path where shadow model will be saved
            registry_path: Path to training registry
        """
        self.trainer = OnlineTrainer(
            frozen_model_path=frozen_model_path,
            shadow_model_path=shadow_model_path,
            registry_path=registry_path
        )
    
    def start_training(self) -> None:
        """
        Start shadow model training pipeline.
        
        Step 1: frozen_model → copy → shadow_model
        """
        self.trainer.initialize_shadow_model()
        print("✓ Shadow model initialized from frozen model")
    
    def train_on_new_data(self, features: dict, label: int) -> None:
        """
        Train shadow model on new data.
        
        Step 2: shadow_model.learn_one()
        
        Args:
            features: Feature dictionary
            label: Target label (0 or 1)
        """
        self.trainer.train_one(features, label)
    
    def save_progress(self) -> None:
        """
        Save shadow model progress to disk.
        
        Step 3: registry save
        """
        self.trainer.save_checkpoint()
        print("✓ Shadow model checkpoint saved")
    
    def evaluate_for_promotion(
        self,
        metrics: dict[str, float],
        min_winrate: float = 0.55,
        min_expectancy: float = 0.5
    ) -> bool:
        """
        Evaluate if shadow model is ready for promotion.
        
        Step 4: promotion gate
        
        Args:
            metrics: Current shadow model performance metrics
            min_winrate: Minimum required win rate
            min_expectancy: Minimum required expectancy
            
        Returns:
            True if shadow model meets promotion criteria
        """
        thresholds = {
            "winrate": min_winrate,
            "expectancy": min_expectancy
        }
        
        can_promote = self.trainer.can_promote(metrics, thresholds)
        
        if can_promote:
            print(f"✓ Shadow model meets promotion criteria: {metrics}")
        else:
            print(f"✗ Shadow model does not meet criteria: {metrics}")
        
        return can_promote
    
    def promote_shadow_to_production(self) -> None:
        """
        Promote shadow model to production.
        
        WARNING: Only call after evaluate_for_promotion() returns True.
        This replaces the frozen model with the shadow model.
        """
        self.trainer.promote_to_production()
        print("✓ Shadow model promoted to production")
        print("  (backup created automatically)")
    
    def rollback_to_backup(self, backup_path: str | Path) -> None:
        """
        Rollback to previous model version.
        
        Step 5: rollback
        
        Args:
            backup_path: Path to backup model
        """
        self.trainer.rollback(backup_path)
        print(f"✓ Rolled back to: {backup_path}")


def example_usage():
    """
    Example of complete shadow model pipeline workflow.
    
    This demonstrates the safe online learning workflow without
    affecting live trading.
    """
    # Initialize pipeline
    pipeline = ShadowModelPipeline()
    
    # Step 1: Start training (frozen → shadow)
    pipeline.start_training()
    
    # Step 2: Train on new data
    for i in range(100):
        features = {
            "feature_1": 0.5,
            "feature_2": 0.7,
            "feature_3": 1.2
        }
        label = 1 if i % 2 == 0 else 0
        pipeline.train_on_new_data(features, label)
    
    # Step 3: Save progress
    pipeline.save_progress()
    
    # Step 4: Evaluate for promotion
    metrics = {
        "winrate": 0.58,
        "expectancy": 0.65,
        "sharpe": 1.2
    }
    
    if pipeline.evaluate_for_promotion(metrics):
        # Promote to production
        pipeline.promote_shadow_to_production()
    
    # Step 5: If needed, rollback
    # pipeline.rollback_to_backup("ai_data/models/frozen_model_backup_123456.pkl")


if __name__ == "__main__":
    example_usage()
