"""
Shadow model implementation for safe online learning.

A shadow model is a copy of the frozen production model that learns from
new data without affecting live trading decisions. It can be promoted to
production after validation.
"""

import pickle
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from river import linear_model, optim, preprocessing, compose


class ShadowModel:
    """
    Shadow model that learns from new data without affecting production.
    
    The shadow model:
    - Starts as a copy of the frozen production model
    - Learns from new data via learn_one()
    - Is saved separately from production model
    - Can be promoted to production via promotion gate
    - Can be rolled back if performance degrades
    """
    
    def __init__(self, frozen_model=None):
        """
        Initialize shadow model.
        
        Args:
            frozen_model: Optional frozen model to copy from. If None, creates new model.
        """
        if frozen_model is not None:
            # Deep copy the frozen model
            self.model = pickle.loads(pickle.dumps(frozen_model))
        else:
            # Create new model if no frozen model provided
            self.model = compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.LogisticRegression(optimizer=optim.SGD(0.01))
            )
        
        self.learn_count = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_updated = self.created_at
    
    def predict_proba(self, x: dict) -> float:
        """Make prediction without learning."""
        out = self.model.predict_proba_one(x)
        if isinstance(out, dict):
            return float(out.get(1, 0.0))
        try:
            return float(out)
        except Exception:
            return 0.0
    
    def learn_one(self, x: dict, y: int) -> None:
        """Learn from a single example."""
        self.model.learn_one(x, y)
        self.learn_count += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()
    
    def save(self, path: str | Path) -> None:
        """Save shadow model to disk."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "model": self.model,
            "learn_count": self.learn_count,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
        
        with open(p, "wb") as f:
            pickle.dump(state, f)
    
    @classmethod
    def load(cls, path: str | Path) -> "ShadowModel":
        """Load shadow model from disk."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Shadow model not found: {path}")
        
        with open(p, "rb") as f:
            state = pickle.load(f)
        
        instance = cls()
        instance.model = state["model"]
        instance.learn_count = state.get("learn_count", 0)
        instance.created_at = state.get("created_at", datetime.now(timezone.utc).isoformat())
        instance.last_updated = state.get("last_updated", instance.created_at)
        
        return instance
    
    @classmethod
    def from_frozen_model(cls, frozen_model_path: str | Path) -> "ShadowModel":
        """
        Create shadow model by copying frozen production model.
        
        Args:
            frozen_model_path: Path to frozen production model
            
        Returns:
            ShadowModel instance initialized from frozen model
        """
        p = Path(frozen_model_path)
        if not p.exists():
            raise FileNotFoundError(f"Frozen model not found: {frozen_model_path}")
        
        with open(p, "rb") as f:
            frozen_model = pickle.load(f)
        
        return cls(frozen_model=frozen_model)
