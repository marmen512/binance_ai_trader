"""Paper Trade Feature Logger - Phase 3

Log entry features and outcomes to parquet storage.
Append-only mode for data integrity.
"""

import pandas as pd
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Create log directory
LOG_PATH = Path("adaptive_logs")
LOG_PATH.mkdir(exist_ok=True)


def log_trade(features: dict, outcome: int):
    """
    Log a paper trade with features and outcome.
    
    Args:
        features: Dictionary of features at trade entry
        outcome: Trade outcome (1 for win, 0 for loss)
    """
    # Combine features and outcome
    row = {**features, "outcome": outcome}
    df = pd.DataFrame([row])
    
    # Append to parquet file
    file = LOG_PATH / "trades.parquet"
    
    if file.exists():
        try:
            old = pd.read_parquet(file)
            df = pd.concat([old, df], ignore_index=True)
            logger.debug(f"Appended trade to existing log (total: {len(df)} trades)")
        except Exception as e:
            logger.warning(f"Error reading existing log: {e}. Creating new log.")
    else:
        logger.info("Creating new trade log file")
    
    df.to_parquet(file, index=False)
    logger.debug(f"Trade logged: outcome={outcome}, features={len(features)}")
