"""
Adaptive learning module - isolated from execution path.

This module contains online learning components that are kept separate from
the trading execution path to prevent any interference with live trading.
"""

from adaptive.ml_online import OnlineModel
from adaptive.shadow_model import ShadowModel
from adaptive.online_trainer import OnlineTrainer
from adaptive.feature_logger import FeatureLogger

__all__ = [
    "OnlineModel",
    "ShadowModel",
    "OnlineTrainer",
    "FeatureLogger",
]
