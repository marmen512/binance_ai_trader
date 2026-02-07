"""
Online trainer for managing shadow model training pipeline.

Handles the safe training of shadow models without affecting production.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
import json

from adaptive.shadow_model import ShadowModel


class OnlineTrainer:
    """
    Manages online training pipeline for shadow models.
    
    Responsibilities:
    - Create shadow models from frozen models
    - Train shadow models on new data
    - Save training progress
    - Manage promotion gates
    - Handle rollback scenarios
    """
    
    def __init__(
        self,
        frozen_model_path: str | Path,
        shadow_model_path: str | Path,
        registry_path: Optional[str | Path] = None
    ):
        """
        Initialize online trainer.
        
        Args:
            frozen_model_path: Path to frozen production model
            shadow_model_path: Path where shadow model will be saved
            registry_path: Optional path to training registry
        """
        self.frozen_model_path = Path(frozen_model_path)
        self.shadow_model_path = Path(shadow_model_path)
        self.registry_path = Path(registry_path) if registry_path else None
        
        self.shadow_model: Optional[ShadowModel] = None
        self.training_started = False
    
    def initialize_shadow_model(self) -> None:
        """Initialize shadow model from frozen model."""
        if self.shadow_model_path.exists():
            # Load existing shadow model
            self.shadow_model = ShadowModel.load(self.shadow_model_path)
        else:
            # Create new shadow model from frozen model
            self.shadow_model = ShadowModel.from_frozen_model(self.frozen_model_path)
            self.shadow_model.save(self.shadow_model_path)
        
        self.training_started = True
        self._save_registry_entry("initialized")
    
    def train_one(self, x: dict, y: int) -> None:
        """
        Train shadow model on a single example.
        
        Args:
            x: Feature dictionary
            y: Target label
        """
        if not self.training_started:
            self.initialize_shadow_model()
        
        if self.shadow_model is None:
            raise RuntimeError("Shadow model not initialized")
        
        self.shadow_model.learn_one(x, y)
    
    def save_checkpoint(self) -> None:
        """Save current shadow model state."""
        if self.shadow_model is None:
            raise RuntimeError("Shadow model not initialized")
        
        self.shadow_model.save(self.shadow_model_path)
        self._save_registry_entry("checkpoint")
    
    def can_promote(self, metrics: dict[str, float], thresholds: dict[str, float]) -> bool:
        """
        Check if shadow model can be promoted to production.
        
        Args:
            metrics: Current shadow model metrics
            thresholds: Minimum required metrics for promotion
            
        Returns:
            True if shadow model meets promotion criteria
        """
        for metric_name, threshold in thresholds.items():
            if metric_name not in metrics:
                return False
            if metrics[metric_name] < threshold:
                return False
        
        return True
    
    def promote_to_production(self) -> None:
        """
        Promote shadow model to production.
        
        WARNING: This replaces the frozen model with the shadow model.
        Ensure can_promote() returns True before calling this.
        """
        if self.shadow_model is None:
            raise RuntimeError("Shadow model not initialized")
        
        # Backup current frozen model
        backup_path = self.frozen_model_path.parent / f"{self.frozen_model_path.stem}_backup_{int(datetime.now().timestamp())}.pkl"
        if self.frozen_model_path.exists():
            import shutil
            shutil.copy2(self.frozen_model_path, backup_path)
        
        # Copy shadow model to frozen model location
        self.shadow_model.save(self.frozen_model_path)
        
        self._save_registry_entry("promoted", {"backup_path": str(backup_path)})
    
    def rollback(self, backup_path: str | Path) -> None:
        """
        Rollback to a previous model version.
        
        Args:
            backup_path: Path to backup model to restore
        """
        import shutil
        backup_p = Path(backup_path)
        
        if not backup_p.exists():
            raise FileNotFoundError(f"Backup model not found: {backup_path}")
        
        shutil.copy2(backup_p, self.frozen_model_path)
        
        self._save_registry_entry("rollback", {"backup_path": str(backup_path)})
    
    def _save_registry_entry(self, action: str, metadata: Optional[dict] = None) -> None:
        """Save training event to registry."""
        if self.registry_path is None:
            return
        
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "frozen_model_path": str(self.frozen_model_path),
            "shadow_model_path": str(self.shadow_model_path),
            "metadata": metadata or {}
        }
        
        if self.shadow_model:
            entry["learn_count"] = self.shadow_model.learn_count
        
        # Append to registry
        with open(self.registry_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
