"""Shadow Model Loader - Phase 2

Load frozen model copy and maintain separate instance for learning.
Shadow model never auto-saves without registry approval.
"""

from copy import deepcopy
import joblib
import logging

logger = logging.getLogger(__name__)


class ShadowModel:
    """
    Shadow model that learns from paper trades.
    
    Critical: Shadow model NEVER trades directly.
    Only frozen model generates trading signals.
    """
    
    def __init__(self, frozen_path):
        """
        Initialize shadow model from frozen model.
        
        Args:
            frozen_path: Path to frozen model file
        """
        logger.info(f"Loading frozen model from {frozen_path}")
        self.frozen = joblib.load(frozen_path)
        self.shadow = deepcopy(self.frozen)
        logger.info("Shadow model created from frozen model")
    
    def predict(self, X):
        """
        Make prediction using shadow model.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predictions from shadow model
        """
        return self.shadow.predict(X)
    
    def learn_one(self, X, y):
        """
        Update shadow model with one sample.
        
        Supports models with partial_fit or learn_one methods.
        
        Args:
            X: Feature matrix (single sample or batch)
            y: Target values
        """
        if hasattr(self.shadow, "partial_fit"):
            self.shadow.partial_fit(X, y)
            logger.debug("Shadow model updated via partial_fit")
        elif hasattr(self.shadow, "learn_one"):
            self.shadow.learn_one(X, y)
            logger.debug("Shadow model updated via learn_one")
        else:
            logger.warning("Shadow model does not support online learning")
