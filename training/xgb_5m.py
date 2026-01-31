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
    """
    # TODO: Implement the actual training logic here
    return TrainResult(best_iteration=0, val_mlogloss=0.0)
