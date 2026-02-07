"""
Trade events system for event-driven architecture.

Provides a publish-subscribe pattern for trade events to decouple
execution from logging, analytics, and adaptive learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Any
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path


class TradeEventType(Enum):
    """Types of trade events."""
    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    TRADE_UPDATED = "trade_updated"
    POSITION_CHANGED = "position_changed"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"


@dataclass
class TradeEvent:
    """
    Trade event data.
    
    Attributes:
        event_type: Type of event
        timestamp: Event timestamp
        symbol: Trading symbol
        data: Event-specific data
        metadata: Optional metadata
    """
    event_type: TradeEventType
    timestamp: str
    symbol: str
    data: dict
    metadata: Optional[dict] = None


class TradeEventListener:
    """
    Base class for trade event listeners.
    
    Subclass this and override the on_* methods to handle specific events.
    """
    
    def on_trade_opened(self, event: TradeEvent) -> None:
        """Called when a trade is opened."""
        pass
    
    def on_trade_closed(self, event: TradeEvent) -> None:
        """Called when a trade is closed."""
        pass
    
    def on_trade_updated(self, event: TradeEvent) -> None:
        """Called when a trade is updated."""
        pass
    
    def on_position_changed(self, event: TradeEvent) -> None:
        """Called when position state changes."""
        pass
    
    def on_order_placed(self, event: TradeEvent) -> None:
        """Called when an order is placed."""
        pass
    
    def on_order_filled(self, event: TradeEvent) -> None:
        """Called when an order is filled."""
        pass
    
    def on_order_cancelled(self, event: TradeEvent) -> None:
        """Called when an order is cancelled."""
        pass
    
    def on_event(self, event: TradeEvent) -> None:
        """
        Generic event handler called for all events.
        
        Override this if you want to handle all events uniformly.
        """
        pass


class TradeEventBus:
    """
    Central event bus for trade events.
    
    Implements publish-subscribe pattern to decouple execution from
    logging, analytics, and adaptive learning.
    """
    
    def __init__(self, log_events: bool = True, log_path: Optional[str | Path] = None):
        """
        Initialize event bus.
        
        Args:
            log_events: Whether to log events to file
            log_path: Path to event log file
        """
        self._listeners: list[TradeEventListener] = []
        self.log_events = log_events
        self.log_path = Path(log_path) if log_path else Path("ai_data/events/trade_events.jsonl")
        
        if self.log_events:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def subscribe(self, listener: TradeEventListener) -> None:
        """
        Subscribe a listener to events.
        
        Args:
            listener: Event listener to subscribe
        """
        if listener not in self._listeners:
            self._listeners.append(listener)
    
    def unsubscribe(self, listener: TradeEventListener) -> None:
        """
        Unsubscribe a listener from events.
        
        Args:
            listener: Event listener to unsubscribe
        """
        if listener in self._listeners:
            self._listeners.remove(listener)
    
    def publish(self, event: TradeEvent) -> None:
        """
        Publish an event to all listeners.
        
        Args:
            event: Event to publish
        """
        # Log event to file if enabled
        if self.log_events:
            self._log_event(event)
        
        # Notify all listeners
        for listener in self._listeners:
            try:
                # Call generic handler
                listener.on_event(event)
                
                # Call specific handler based on event type
                if event.event_type == TradeEventType.TRADE_OPENED:
                    listener.on_trade_opened(event)
                elif event.event_type == TradeEventType.TRADE_CLOSED:
                    listener.on_trade_closed(event)
                elif event.event_type == TradeEventType.TRADE_UPDATED:
                    listener.on_trade_updated(event)
                elif event.event_type == TradeEventType.POSITION_CHANGED:
                    listener.on_position_changed(event)
                elif event.event_type == TradeEventType.ORDER_PLACED:
                    listener.on_order_placed(event)
                elif event.event_type == TradeEventType.ORDER_FILLED:
                    listener.on_order_filled(event)
                elif event.event_type == TradeEventType.ORDER_CANCELLED:
                    listener.on_order_cancelled(event)
                    
            except Exception as e:
                # Listener errors should not break the event bus
                print(f"Error in event listener {listener.__class__.__name__}: {e}")
    
    def emit_trade_opened(
        self,
        symbol: str,
        data: dict,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Emit a trade opened event.
        
        Args:
            symbol: Trading symbol
            data: Trade data
            metadata: Optional metadata
        """
        event = TradeEvent(
            event_type=TradeEventType.TRADE_OPENED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            data=data,
            metadata=metadata
        )
        self.publish(event)
    
    def emit_trade_closed(
        self,
        symbol: str,
        data: dict,
        metadata: Optional[dict] = None
    ) -> None:
        """
        Emit a trade closed event.
        
        Args:
            symbol: Trading symbol
            data: Trade data including outcome and PnL
            metadata: Optional metadata
        """
        event = TradeEvent(
            event_type=TradeEventType.TRADE_CLOSED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            data=data,
            metadata=metadata
        )
        self.publish(event)
    
    def emit_trade_updated(
        self,
        symbol: str,
        data: dict,
        metadata: Optional[dict] = None
    ) -> None:
        """Emit a trade updated event."""
        event = TradeEvent(
            event_type=TradeEventType.TRADE_UPDATED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            data=data,
            metadata=metadata
        )
        self.publish(event)
    
    def emit_position_changed(
        self,
        symbol: str,
        data: dict,
        metadata: Optional[dict] = None
    ) -> None:
        """Emit a position changed event."""
        event = TradeEvent(
            event_type=TradeEventType.POSITION_CHANGED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=symbol,
            data=data,
            metadata=metadata
        )
        self.publish(event)
    
    def _log_event(self, event: TradeEvent) -> None:
        """Log event to file."""
        try:
            log_entry = {
                'event_type': event.event_type.value,
                'timestamp': event.timestamp,
                'symbol': event.symbol,
                'data': event.data,
                'metadata': event.metadata
            }
            
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Failed to log event: {e}")


# Global event bus instance
_event_bus: Optional[TradeEventBus] = None


def get_event_bus() -> TradeEventBus:
    """
    Get or create the global event bus instance.
    
    Returns:
        Global TradeEventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = TradeEventBus()
    return _event_bus


def initialize_event_system(
    log_events: bool = True,
    log_path: Optional[str | Path] = None
) -> TradeEventBus:
    """
    Initialize the global event system.
    
    Args:
        log_events: Whether to log events to file
        log_path: Path to event log file
        
    Returns:
        Initialized TradeEventBus
    """
    global _event_bus
    _event_bus = TradeEventBus(log_events=log_events, log_path=log_path)
    return _event_bus
