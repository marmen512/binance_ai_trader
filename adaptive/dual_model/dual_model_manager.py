"""Dual Model Manager - Phase 2

Manages frozen (production) and shadow (learning) models.
CRITICAL: Shadow model NEVER trades directly.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional, Any

import logging

logger = logging.getLogger(__name__)


class ModelRole(Enum):
    """Model role in dual architecture"""
    FROZEN = "frozen"  # Production model - trades
    SHADOW = "shadow"  # Learning model - never trades


@dataclass(frozen=True)
class ModelMetadata:
    """Metadata for a model version"""
    model_id: str
    role: ModelRole
    version: int
    created_at: str
    parent_model_id: Optional[str]
    trained_on_trades: int
    performance_metrics: dict[str, float]
    artifact_path: str
    model_card_path: Optional[str]
    
    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "role": self.role.value,
            "version": self.version,
            "created_at": self.created_at,
            "parent_model_id": self.parent_model_id,
            "trained_on_trades": self.trained_on_trades,
            "performance_metrics": self.performance_metrics,
            "artifact_path": self.artifact_path,
            "model_card_path": self.model_card_path,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> ModelMetadata:
        return cls(
            model_id=data["model_id"],
            role=ModelRole(data["role"]),
            version=data["version"],
            created_at=data["created_at"],
            parent_model_id=data.get("parent_model_id"),
            trained_on_trades=data["trained_on_trades"],
            performance_metrics=data["performance_metrics"],
            artifact_path=data["artifact_path"],
            model_card_path=data.get("model_card_path"),
        )


class DualModelManager:
    """
    Manages frozen and shadow models.
    
    Rules:
    - Frozen model is READ ONLY during paper trading
    - Shadow model learns but NEVER trades
    - Only promotion gate can swap shadow → frozen
    - Full version history maintained
    - Rollback capability required
    """
    
    def __init__(self, registry_dir: Path):
        """
        Initialize dual model manager.
        
        Args:
            registry_dir: Directory for model registry
        """
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        self.frozen_meta_path = self.registry_dir / "frozen_metadata.json"
        self.shadow_meta_path = self.registry_dir / "shadow_metadata.json"
        self.history_path = self.registry_dir / "version_history.jsonl"
        
        self._frozen_metadata: Optional[ModelMetadata] = None
        self._shadow_metadata: Optional[ModelMetadata] = None
        
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """Load frozen and shadow metadata from disk"""
        if self.frozen_meta_path.exists():
            try:
                data = json.loads(self.frozen_meta_path.read_text())
                self._frozen_metadata = ModelMetadata.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load frozen metadata: {e}")
        
        if self.shadow_meta_path.exists():
            try:
                data = json.loads(self.shadow_meta_path.read_text())
                self._shadow_metadata = ModelMetadata.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load shadow metadata: {e}")
    
    def _save_metadata(self, metadata: ModelMetadata) -> None:
        """Save metadata to disk and append to history"""
        if metadata.role == ModelRole.FROZEN:
            path = self.frozen_meta_path
            self._frozen_metadata = metadata
        else:
            path = self.shadow_meta_path
            self._shadow_metadata = metadata
        
        # Save current metadata
        path.write_text(json.dumps(metadata.to_dict(), indent=2))
        
        # Append to history
        history_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "update",
            "metadata": metadata.to_dict(),
        }
        with open(self.history_path, "a") as f:
            f.write(json.dumps(history_entry) + "\n")
        
        logger.info(f"Saved {metadata.role.value} model metadata: {metadata.model_id}")
    
    def initialize_frozen(
        self,
        model_id: str,
        artifact_path: Path,
        model_card_path: Optional[Path] = None,
        performance_metrics: Optional[dict] = None,
    ) -> ModelMetadata:
        """
        Initialize frozen (production) model.
        
        Args:
            model_id: Model identifier
            artifact_path: Path to model artifact
            model_card_path: Optional path to model card
            performance_metrics: Optional performance metrics
        
        Returns:
            ModelMetadata for frozen model
        """
        metadata = ModelMetadata(
            model_id=model_id,
            role=ModelRole.FROZEN,
            version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_model_id=None,
            trained_on_trades=0,
            performance_metrics=performance_metrics or {},
            artifact_path=str(artifact_path),
            model_card_path=str(model_card_path) if model_card_path else None,
        )
        
        self._save_metadata(metadata)
        logger.info(f"Initialized frozen model: {model_id}")
        return metadata
    
    def create_shadow_from_frozen(self) -> Optional[ModelMetadata]:
        """
        Create shadow model as a copy of frozen model.
        Shadow starts learning from this point.
        
        Returns:
            ModelMetadata for shadow model, or None if frozen not initialized
        """
        if not self._frozen_metadata:
            logger.error("Cannot create shadow: frozen model not initialized")
            return None
        
        shadow_id = f"{self._frozen_metadata.model_id}_shadow_v1"
        
        metadata = ModelMetadata(
            model_id=shadow_id,
            role=ModelRole.SHADOW,
            version=1,
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_model_id=self._frozen_metadata.model_id,
            trained_on_trades=0,
            performance_metrics={},
            artifact_path=self._frozen_metadata.artifact_path,  # Start from same artifact
            model_card_path=self._frozen_metadata.model_card_path,
        )
        
        self._save_metadata(metadata)
        logger.info(f"Created shadow model from frozen: {shadow_id}")
        return metadata
    
    def update_shadow(
        self,
        new_artifact_path: Path,
        trained_on_trades: int,
        performance_metrics: dict[str, float],
    ) -> ModelMetadata:
        """
        Update shadow model after learning.
        
        Args:
            new_artifact_path: Path to updated model artifact
            trained_on_trades: Number of trades used for training
            performance_metrics: Performance metrics
        
        Returns:
            Updated ModelMetadata for shadow
        """
        if not self._shadow_metadata:
            raise ValueError("Shadow model not initialized")
        
        new_version = self._shadow_metadata.version + 1
        shadow_id = f"{self._shadow_metadata.parent_model_id}_shadow_v{new_version}"
        
        metadata = ModelMetadata(
            model_id=shadow_id,
            role=ModelRole.SHADOW,
            version=new_version,
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_model_id=self._shadow_metadata.parent_model_id,
            trained_on_trades=trained_on_trades,
            performance_metrics=performance_metrics,
            artifact_path=str(new_artifact_path),
            model_card_path=self._shadow_metadata.model_card_path,
        )
        
        self._save_metadata(metadata)
        logger.info(f"Updated shadow model: {shadow_id} (trained on {trained_on_trades} trades)")
        return metadata
    
    def promote_shadow_to_frozen(self) -> tuple[bool, str]:
        """
        Promote shadow model to frozen (production).
        This is the ONLY way shadow can become production model.
        
        Returns:
            Tuple of (success, message)
        """
        if not self._shadow_metadata:
            return False, "Shadow model not initialized"
        
        if not self._frozen_metadata:
            return False, "Frozen model not initialized"
        
        # Create backup of current frozen
        backup_dir = self.registry_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        
        backup_path = backup_dir / f"frozen_{self._frozen_metadata.model_id}_{datetime.now(timezone.utc).isoformat()}.json"
        backup_path.write_text(json.dumps(self._frozen_metadata.to_dict(), indent=2))
        
        # Promote shadow to frozen
        new_frozen = ModelMetadata(
            model_id=self._shadow_metadata.model_id.replace("_shadow", "_frozen"),
            role=ModelRole.FROZEN,
            version=self._frozen_metadata.version + 1,
            created_at=datetime.now(timezone.utc).isoformat(),
            parent_model_id=self._frozen_metadata.model_id,
            trained_on_trades=self._shadow_metadata.trained_on_trades,
            performance_metrics=self._shadow_metadata.performance_metrics,
            artifact_path=self._shadow_metadata.artifact_path,
            model_card_path=self._shadow_metadata.model_card_path,
        )
        
        self._save_metadata(new_frozen)
        
        # Log promotion event
        promotion_event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "promotion",
            "old_frozen": self._frozen_metadata.to_dict(),
            "new_frozen": new_frozen.to_dict(),
            "promoted_from_shadow": self._shadow_metadata.to_dict(),
            "backup_path": str(backup_path),
        }
        with open(self.history_path, "a") as f:
            f.write(json.dumps(promotion_event) + "\n")
        
        msg = f"Promoted shadow {self._shadow_metadata.model_id} to frozen (version {new_frozen.version})"
        logger.info(msg)
        return True, msg
    
    def rollback_frozen(self, backup_id: str) -> tuple[bool, str]:
        """
        Rollback frozen model to a previous version.
        
        Args:
            backup_id: Backup identifier to restore
        
        Returns:
            Tuple of (success, message)
        """
        backup_dir = self.registry_dir / "backups"
        backup_files = list(backup_dir.glob(f"frozen_{backup_id}*.json"))
        
        if not backup_files:
            return False, f"Backup not found: {backup_id}"
        
        # Use most recent backup if multiple found
        backup_file = max(backup_files, key=lambda p: p.stat().st_mtime)
        
        try:
            data = json.loads(backup_file.read_text())
            metadata = ModelMetadata.from_dict(data)
            
            # Restore as frozen
            metadata = ModelMetadata(
                model_id=metadata.model_id,
                role=ModelRole.FROZEN,
                version=metadata.version,
                created_at=datetime.now(timezone.utc).isoformat(),
                parent_model_id=metadata.parent_model_id,
                trained_on_trades=metadata.trained_on_trades,
                performance_metrics=metadata.performance_metrics,
                artifact_path=metadata.artifact_path,
                model_card_path=metadata.model_card_path,
            )
            
            self._save_metadata(metadata)
            
            msg = f"Rolled back frozen model to {backup_id}"
            logger.info(msg)
            return True, msg
            
        except Exception as e:
            msg = f"Rollback failed: {e}"
            logger.error(msg)
            return False, msg
    
    def get_frozen_metadata(self) -> Optional[ModelMetadata]:
        """Get current frozen model metadata"""
        return self._frozen_metadata
    
    def get_shadow_metadata(self) -> Optional[ModelMetadata]:
        """Get current shadow model metadata"""
        return self._shadow_metadata
    
    def get_version_history(self, limit: int = 100) -> list[dict]:
        """
        Get version history.
        
        Args:
            limit: Maximum number of history entries to return
        
        Returns:
            List of history entries (most recent first)
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
