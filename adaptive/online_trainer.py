"""Online Trainer - Phase 4

Train shadow model from logged paper trades.
Rate-limited updates to prevent overfitting.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


class OnlineTrainer:
    """
    Train shadow model from logged paper trades.
    
    Updates are rate-limited via max_updates parameter.
    """
    
    def __init__(self, shadow_model, max_updates=50):
        """
        Initialize online trainer.
        
        Args:
            shadow_model: ShadowModel instance to train
            max_updates: Maximum number of updates per training run
        """
        self.shadow_model = shadow_model
        self.max_updates = max_updates
        logger.info(f"OnlineTrainer initialized with max_updates={max_updates}")
    
    def train_from_log(self, path):
        """
        Train shadow model from parquet log file.
        
        Args:
            path: Path to trades.parquet file
        """
        try:
            df = pd.read_parquet(path)
            logger.info(f"Loaded {len(df)} trades from log")
            
            # Separate features and outcomes
            X = df.drop(columns=["outcome"])
            y = df["outcome"]
            
            # Train with max_updates limit
            num_updates = min(len(df), self.max_updates)
            logger.info(f"Training shadow model with {num_updates} updates")
            
            for i in range(num_updates):
                self.shadow_model.learn_one(
                    X.iloc[i:i+1],
                    y.iloc[i:i+1]
                )
            
            logger.info(f"Shadow model training complete ({num_updates} updates)")
            
        except Exception as e:
            logger.error(f"Error training from log: {e}")
            raise
