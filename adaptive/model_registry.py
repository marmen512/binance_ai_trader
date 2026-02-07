"""Model Registry - Phase 6

Versioned model saves with rollback support.
"""

import joblib
from pathlib import Path
import time
import logging

logger = logging.getLogger(__name__)

# Create registry directory
REG_PATH = Path("adaptive_models")
REG_PATH.mkdir(exist_ok=True)


def save_shadow(model):
    """
    Save shadow model with timestamp version.
    
    Args:
        model: Model to save (shadow_model.shadow attribute)
        
    Returns:
        Path to saved model file
    """
    name = f"shadow_{int(time.time())}.pkl"
    path = REG_PATH / name
    
    joblib.dump(model, path)
    logger.info(f"Shadow model saved to {path}")
    
    return path


def list_versions():
    """
    List all saved shadow model versions.
    
    Returns:
        List of tuples (timestamp, path) sorted by timestamp
    """
    versions = []
    
    for path in REG_PATH.glob("shadow_*.pkl"):
        try:
            # Extract timestamp from filename
            timestamp = int(path.stem.split("_")[1])
            versions.append((timestamp, path))
        except Exception as e:
            logger.warning(f"Invalid shadow model filename: {path.name}")
    
    versions.sort(key=lambda x: x[0], reverse=True)
    return versions


def load_version(timestamp):
    """
    Load a specific shadow model version.
    
    Args:
        timestamp: Timestamp of version to load
        
    Returns:
        Loaded model
    """
    name = f"shadow_{timestamp}.pkl"
    path = REG_PATH / name
    
    if not path.exists():
        raise FileNotFoundError(f"Shadow model version not found: {name}")
    
    model = joblib.load(path)
    logger.info(f"Loaded shadow model version: {name}")
    
    return model


def get_latest_version():
    """
    Get the most recent shadow model version.
    
    Returns:
        Tuple of (timestamp, path) or None if no versions exist
    """
    versions = list_versions()
    return versions[0] if versions else None
