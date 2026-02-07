"""
Feature logger for tracking feature snapshots with versioning.

Logs features used in predictions with schema versioning to prevent
data corruption in online learning scenarios.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict


@dataclass
class FeatureSnapshot:
    """
    Feature snapshot with schema versioning.
    
    Attributes:
        feature_set_id: Unique ID for this feature snapshot
        feature_schema_version: Version of the feature schema
        feature_hash: Hash of feature keys for validation
        features: The actual feature dictionary
        timestamp: When the snapshot was created
        metadata: Optional metadata (e.g., model_id, prediction_id)
    """
    feature_set_id: str
    feature_schema_version: str
    feature_hash: str
    features: dict
    timestamp: str
    metadata: Optional[dict] = None


class FeatureLogger:
    """
    Logs feature snapshots with schema versioning.
    
    Prevents data corruption in online learning by ensuring:
    - Feature schema consistency across time
    - Ability to detect schema changes
    - Tracking of feature evolution
    """
    
    def __init__(
        self,
        log_path: str | Path,
        schema_version: str = "v1"
    ):
        """
        Initialize feature logger.
        
        Args:
            log_path: Path to feature log file (JSONL format)
            schema_version: Current feature schema version
        """
        self.log_path = Path(log_path)
        self.schema_version = schema_version
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _compute_feature_hash(self, features: dict) -> str:
        """
        Compute hash of feature keys (not values).
        
        This allows detecting schema changes while ignoring value changes.
        """
        sorted_keys = sorted(features.keys())
        keys_str = ",".join(sorted_keys)
        return hashlib.sha256(keys_str.encode()).hexdigest()[:16]
    
    def _generate_feature_set_id(self) -> str:
        """Generate unique feature set ID."""
        timestamp = datetime.now(timezone.utc).isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def log_features(
        self,
        features: dict,
        metadata: Optional[dict] = None
    ) -> FeatureSnapshot:
        """
        Log feature snapshot with versioning.
        
        Args:
            features: Feature dictionary
            metadata: Optional metadata to attach
            
        Returns:
            FeatureSnapshot that was logged
        """
        snapshot = FeatureSnapshot(
            feature_set_id=self._generate_feature_set_id(),
            feature_schema_version=self.schema_version,
            feature_hash=self._compute_feature_hash(features),
            features=features,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {}
        )
        
        # Append to log file
        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(snapshot)) + "\n")
        
        return snapshot
    
    def validate_schema(self, features: dict, expected_hash: Optional[str] = None) -> bool:
        """
        Validate feature schema against expected hash.
        
        Args:
            features: Feature dictionary to validate
            expected_hash: Expected feature hash (if None, uses first log entry)
            
        Returns:
            True if schema matches, False otherwise
        """
        current_hash = self._compute_feature_hash(features)
        
        if expected_hash is not None:
            return current_hash == expected_hash
        
        # Get expected hash from first log entry
        if not self.log_path.exists():
            return True  # No reference yet
        
        try:
            with open(self.log_path, "r") as f:
                first_line = f.readline()
                if not first_line:
                    return True
                
                first_snapshot = json.loads(first_line)
                expected_hash = first_snapshot.get("feature_hash")
                
                if expected_hash is None:
                    return True
                
                return current_hash == expected_hash
        except Exception:
            return True  # Can't validate, assume OK
    
    def read_recent_snapshots(self, limit: int = 100) -> list[FeatureSnapshot]:
        """
        Read recent feature snapshots from log.
        
        Args:
            limit: Maximum number of snapshots to return
            
        Returns:
            List of FeatureSnapshot objects (most recent last)
        """
        if not self.log_path.exists():
            return []
        
        snapshots = []
        
        try:
            with open(self.log_path, "r") as f:
                lines = f.readlines()
                
            for line in lines[-limit:]:
                try:
                    data = json.loads(line)
                    snapshot = FeatureSnapshot(**data)
                    snapshots.append(snapshot)
                except Exception:
                    continue
        except Exception:
            pass
        
        return snapshots
    
    def get_schema_changes(self) -> list[dict]:
        """
        Detect schema changes over time.
        
        Returns:
            List of schema change events with timestamps
        """
        if not self.log_path.exists():
            return []
        
        changes = []
        prev_hash = None
        
        try:
            with open(self.log_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        current_hash = data.get("feature_hash")
                        
                        if prev_hash is not None and current_hash != prev_hash:
                            changes.append({
                                "timestamp": data.get("timestamp"),
                                "old_hash": prev_hash,
                                "new_hash": current_hash,
                                "schema_version": data.get("feature_schema_version")
                            })
                        
                        prev_hash = current_hash
                    except Exception:
                        continue
        except Exception:
            pass
        
        return changes
