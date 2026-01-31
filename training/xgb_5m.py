from __future__ import annotations
from dataclasses import dataclass

@dataclass
class TrainResult:
    best_iteration: int
    val_mlogloss: float

def train_xgb_5m(*, config_path: str | None = None) -> TrainResult:
    """
    Minimal stub implementation. Replace with real training logic.
    Returns an object with attributes `best_iteration` and `val_mlogloss`.
    
    Args:
        config_path: Optional path to configuration file for future use in training logic.
    """
    # TODO: Implement the actual training logic here
    # The config_path parameter is reserved for future implementation
    return TrainResult(best_iteration=0, val_mlogloss=0.0)
