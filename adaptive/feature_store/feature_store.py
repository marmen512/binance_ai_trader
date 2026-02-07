"""Feature Store - Phase 3 & 10

Logs features from paper trades for shadow learning.
READ ONLY consumer of paper trading artifacts.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TradeFeatureSnapshot:
    """Feature snapshot for a single trade"""
    trade_id: str
    timestamp: str
    features_at_entry: dict
    features_at_exit: Optional[dict]
    prediction: str
    confidence: float
    outcome: Optional[str]  # "win", "loss", "breakeven"
    pnl: Optional[float]
    regime: Optional[str]
    volatility: Optional[float]
    leaderboard_flag: bool
    
    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "timestamp": self.timestamp,
            "features_at_entry": self.features_at_entry,
            "features_at_exit": self.features_at_exit,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "outcome": self.outcome,
            "pnl": self.pnl,
            "regime": self.regime,
            "volatility": self.volatility,
            "leaderboard_flag": self.leaderboard_flag,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> TradeFeatureSnapshot:
        return cls(
            trade_id=data["trade_id"],
            timestamp=data["timestamp"],
            features_at_entry=data["features_at_entry"],
            features_at_exit=data.get("features_at_exit"),
            prediction=data["prediction"],
            confidence=data["confidence"],
            outcome=data.get("outcome"),
            pnl=data.get("pnl"),
            regime=data.get("regime"),
            volatility=data.get("volatility"),
            leaderboard_flag=data.get("leaderboard_flag", False),
        )


class FeatureStore:
    """
    Stores and retrieves feature snapshots from paper trades.
    
    CRITICAL: This is a READ ONLY consumer of paper trading artifacts.
    It does NOT modify paper trading behavior.
    
    Storage:
    - features_log.jsonl: Append-only feature logs
    - features_snapshot.parquet: Periodic snapshots for fast access
    """
    
    def __init__(self, store_dir: Path):
        """
        Initialize feature store.
        
        Args:
            store_dir: Directory for feature storage
        """
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        self.features_log_path = self.store_dir / "features_log.jsonl"
        self.snapshot_path = self.store_dir / "features_snapshot.parquet"
        
        self._stats = {
            "total_logged": 0,
            "last_logged": None,
        }
    
    def log_trade_features(
        self,
        trade_id: str,
        features_at_entry: dict,
        prediction: str,
        confidence: float,
        features_at_exit: Optional[dict] = None,
        outcome: Optional[str] = None,
        pnl: Optional[float] = None,
        regime: Optional[str] = None,
        volatility: Optional[float] = None,
        leaderboard_flag: bool = False,
    ) -> bool:
        """
        Log features for a paper trade.
        
        Args:
            trade_id: Unique trade identifier
            features_at_entry: Feature dict at trade entry
            prediction: Model prediction
            confidence: Prediction confidence
            features_at_exit: Optional features at exit
            outcome: Trade outcome ("win", "loss", "breakeven")
            pnl: Profit/loss
            regime: Market regime
            volatility: Volatility metric
            leaderboard_flag: Whether this used leaderboard signal
        
        Returns:
            True if logged successfully
        """
        try:
            snapshot = TradeFeatureSnapshot(
                trade_id=trade_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                features_at_entry=features_at_entry,
                features_at_exit=features_at_exit,
                prediction=prediction,
                confidence=confidence,
                outcome=outcome,
                pnl=pnl,
                regime=regime,
                volatility=volatility,
                leaderboard_flag=leaderboard_flag,
            )
            
            # Append to log
            with open(self.features_log_path, "a") as f:
                f.write(json.dumps(snapshot.to_dict()) + "\n")
            
            self._stats["total_logged"] += 1
            self._stats["last_logged"] = datetime.now(timezone.utc).isoformat()
            
            logger.debug(f"Logged features for trade {trade_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log trade features: {e}")
            return False
    
    def create_snapshot(self) -> tuple[bool, str]:
        """
        Create parquet snapshot from JSONL log for fast access.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.features_log_path.exists():
                return False, "No features log found"
            
            # Read all logs
            features = []
            with open(self.features_log_path, "r") as f:
                for line in f:
                    try:
                        features.append(json.loads(line))
                    except Exception:
                        continue
            
            if not features:
                return False, "No valid features in log"
            
            # Convert to DataFrame
            df = pd.DataFrame(features)
            
            # Save as parquet
            df.to_parquet(self.snapshot_path, index=False)
            
            msg = f"Created snapshot with {len(df)} trade features"
            logger.info(msg)
            return True, msg
            
        except Exception as e:
            msg = f"Failed to create snapshot: {e}"
            logger.error(msg)
            return False, msg
    
    def get_features_since(
        self,
        since_timestamp: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[TradeFeatureSnapshot]:
        """
        Get trade features since a timestamp.
        
        Args:
            since_timestamp: ISO timestamp to filter from
            limit: Maximum number of features to return
        
        Returns:
            List of TradeFeatureSnapshot
        """
        features = []
        
        if not self.features_log_path.exists():
            return features
        
        try:
            with open(self.features_log_path, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        
                        # Filter by timestamp if provided
                        if since_timestamp and data["timestamp"] <= since_timestamp:
                            continue
                        
                        features.append(TradeFeatureSnapshot.from_dict(data))
                        
                        # Apply limit
                        if limit and len(features) >= limit:
                            break
                            
                    except Exception:
                        continue
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to read features: {e}")
            return []
    
    def get_features_for_learning(
        self,
        min_trades: int = 10,
        max_trades: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Get features suitable for shadow learning.
        
        Args:
            min_trades: Minimum number of trades required
            max_trades: Maximum number of trades to return
        
        Returns:
            DataFrame with features ready for learning
        """
        try:
            # Try to use snapshot if available
            if self.snapshot_path.exists():
                df = pd.read_parquet(self.snapshot_path)
            else:
                # Fall back to reading log
                features = self.get_features_since()
                if not features:
                    return pd.DataFrame()
                df = pd.DataFrame([f.to_dict() for f in features])
            
            # Filter for complete trades (with outcome)
            df = df[df["outcome"].notna()].copy()
            
            if len(df) < min_trades:
                logger.warning(f"Not enough trades for learning: {len(df)} < {min_trades}")
                return pd.DataFrame()
            
            # Apply max limit
            if max_trades and len(df) > max_trades:
                df = df.tail(max_trades).copy()
            
            logger.info(f"Retrieved {len(df)} trades for learning")
            return df
            
        except Exception as e:
            logger.error(f"Failed to get features for learning: {e}")
            return pd.DataFrame()
    
    def get_stats(self) -> dict:
        """Get feature store statistics"""
        log_size = 0
        snapshot_size = 0
        
        if self.features_log_path.exists():
            log_size = self.features_log_path.stat().st_size
        
        if self.snapshot_path.exists():
            snapshot_size = self.snapshot_path.stat().st_size
        
        return {
            "total_logged": self._stats["total_logged"],
            "last_logged": self._stats["last_logged"],
            "log_size_bytes": log_size,
            "snapshot_size_bytes": snapshot_size,
            "log_exists": self.features_log_path.exists(),
            "snapshot_exists": self.snapshot_path.exists(),
        }
