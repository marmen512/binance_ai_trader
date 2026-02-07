"""
Event-based trade logging system.

Replaces inline trade logging with event-driven architecture to decouple
adaptive learning from execution path.
"""

from typing import Callable, Optional
from datetime import datetime, timezone
from monitoring.events import append_event
from adaptive.feature_logger import FeatureLogger


class TradeEventType:
    """Trade event types."""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    TRADE_UPDATED = "trade_updated"
    POSITION_CHANGED = "position_changed"


class TradeEventListener:
    """Base class for trade event listeners."""
    
    def on_trade_opened(self, event_data: dict) -> None:
        """Called when a trade is opened."""
        pass
    
    def on_trade_closed(self, event_data: dict) -> None:
        """Called when a trade is closed."""
        pass
    
    def on_trade_updated(self, event_data: dict) -> None:
        """Called when a trade is updated."""
        pass
    
    def on_position_changed(self, event_data: dict) -> None:
        """Called when position state changes."""
        pass


class AdaptiveLoggerListener(TradeEventListener):
    """
    Adaptive logger that subscribes to trade events.
    
    This listener logs features and outcomes for adaptive learning
    without being directly coupled to execution code.
    """
    
    def __init__(self, feature_log_path: str = "ai_data/adaptive/features.jsonl"):
        """
        Initialize adaptive logger listener.
        
        Args:
            feature_log_path: Path to feature log file
        """
        self.feature_logger = FeatureLogger(
            log_path=feature_log_path,
            schema_version="v1"
        )
    
    def on_trade_closed(self, event_data: dict) -> None:
        """
        Log trade outcome for adaptive learning.
        
        Args:
            event_data: Trade closure event data including:
                - features: Feature snapshot at trade entry
                - outcome: Trade outcome (win/loss)
                - pnl: Profit/loss
                - side: Trade side (LONG/SHORT)
        """
        features = event_data.get("features", {})
        outcome = event_data.get("outcome", "unknown")
        pnl = event_data.get("pnl", 0.0)
        
        metadata = {
            "outcome": outcome,
            "pnl": float(pnl),
            "side": event_data.get("side", "unknown"),
            "symbol": event_data.get("symbol", "unknown"),
            "entry_ts": event_data.get("entry_ts"),
            "exit_ts": event_data.get("exit_ts"),
            "exit_reason": event_data.get("exit_reason")
        }
        
        # Log feature snapshot with versioning
        self.feature_logger.log_features(features, metadata=metadata)


class TradeEventBus:
    """
    Central event bus for trade events.
    
    Implements publish-subscribe pattern to decouple execution from logging.
    """
    
    def __init__(self):
        """Initialize event bus."""
        self._listeners: list[TradeEventListener] = []
    
    def subscribe(self, listener: TradeEventListener) -> None:
        """
        Subscribe a listener to trade events.
        
        Args:
            listener: Event listener to subscribe
        """
        if listener not in self._listeners:
            self._listeners.append(listener)
    
    def unsubscribe(self, listener: TradeEventListener) -> None:
        """
        Unsubscribe a listener from trade events.
        
        Args:
            listener: Event listener to unsubscribe
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def publish_trade_opened(self, trade_data: dict) -> None:
        """
        Publish trade opened event.
        
        Args:
            trade_data: Trade opening data
        """
        # Log event to monitoring
        append_event(
            kind=TradeEventType.TRADE_OPENED,
            payload=trade_data,
            feature_schema_version=trade_data.get("feature_schema_version"),
            feature_hash=trade_data.get("feature_hash"),
            feature_set_id=trade_data.get("feature_set_id")
        )
        
        # Notify listeners
        for listener in self._listeners:
            try:
                listener.on_trade_opened(trade_data)
            except Exception as e:
                # Don't let listener errors break execution
                print(f"Error in trade_opened listener: {e}")
    
    def publish_trade_closed(self, trade_data: dict) -> None:
        """
        Publish trade closed event.
        
        Args:
            trade_data: Trade closure data including outcome and PnL
        """
        # Log event to monitoring
        append_event(
            kind=TradeEventType.TRADE_CLOSED,
            payload=trade_data,
            feature_schema_version=trade_data.get("feature_schema_version"),
            feature_hash=trade_data.get("feature_hash"),
            feature_set_id=trade_data.get("feature_set_id")
        )
        
        # Notify listeners
        for listener in self._listeners:
            try:
                listener.on_trade_closed(trade_data)
            except Exception as e:
                # Don't let listener errors break execution
                print(f"Error in trade_closed listener: {e}")
    
    def publish_trade_updated(self, trade_data: dict) -> None:
        """
        Publish trade updated event.
        
        Args:
            trade_data: Trade update data
        """
        append_event(
            kind=TradeEventType.TRADE_UPDATED,
            payload=trade_data
        )
        
        for listener in self._listeners:
            try:
                listener.on_trade_updated(trade_data)
            except Exception as e:
                print(f"Error in trade_updated listener: {e}")
    
    def publish_position_changed(self, position_data: dict) -> None:
        """
        Publish position changed event.
        
        Args:
            position_data: Position change data
        """
        append_event(
            kind=TradeEventType.POSITION_CHANGED,
            payload=position_data
        )
        
        for listener in self._listeners:
            try:
                listener.on_position_changed(position_data)
            except Exception as e:
                print(f"Error in position_changed listener: {e}")


# Global event bus instance
_event_bus: Optional[TradeEventBus] = None


def get_event_bus() -> TradeEventBus:
    """Get or create global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = TradeEventBus()
    return _event_bus


def initialize_adaptive_logging() -> None:
    """
    Initialize adaptive logging by subscribing to trade events.
    
    Call this at application startup to enable adaptive learning.
    """
    event_bus = get_event_bus()
    adaptive_listener = AdaptiveLoggerListener()
    event_bus.subscribe(adaptive_listener)
    print("✓ Adaptive logging initialized")
