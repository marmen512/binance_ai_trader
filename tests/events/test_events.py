"""
Tests for event system.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from events.trade_events import (
    TradeEventBus,
    TradeEventListener,
    TradeEventType,
    TradeEvent,
    get_event_bus
)


class TestListener(TradeEventListener):
    """Test listener that tracks events."""
    
    def __init__(self):
        self.events_received = []
    
    def on_event(self, event: TradeEvent):
        self.events_received.append(event)
    
    def on_trade_closed(self, event: TradeEvent):
        self.events_received.append(('closed', event))


class TestTradeEventBus:
    """Test trade event bus."""
    
    def test_event_bus_creation(self):
        """Test event bus can be created."""
        bus = TradeEventBus(log_events=False)
        assert bus is not None
    
    def test_event_bus_subscribe(self):
        """Test listener can subscribe to events."""
        bus = TradeEventBus(log_events=False)
        listener = TestListener()
        
        bus.subscribe(listener)
        
        assert listener in bus._listeners
    
    def test_event_bus_unsubscribe(self):
        """Test listener can unsubscribe from events."""
        bus = TradeEventBus(log_events=False)
        listener = TestListener()
        
        bus.subscribe(listener)
        bus.unsubscribe(listener)
        
        assert listener not in bus._listeners
    
    def test_event_bus_publish_trade_closed(self):
        """Test publishing trade closed event."""
        bus = TradeEventBus(log_events=False)
        listener = TestListener()
        bus.subscribe(listener)
        
        bus.emit_trade_closed(
            symbol="BTCUSDT",
            data={"pnl": 100.0, "outcome": "win"}
        )
        
        assert len(listener.events_received) > 0
        # Check that generic handler was called
        assert any(isinstance(e, TradeEvent) for e in listener.events_received)
        # Check that specific handler was called
        assert any(isinstance(e, tuple) and e[0] == 'closed' for e in listener.events_received)
    
    def test_event_bus_publish_trade_opened(self):
        """Test publishing trade opened event."""
        bus = TradeEventBus(log_events=False)
        listener = TestListener()
        bus.subscribe(listener)
        
        bus.emit_trade_opened(
            symbol="BTCUSDT",
            data={"side": "long", "price": 50000.0}
        )
        
        assert len(listener.events_received) > 0
    
    def test_event_bus_listener_error_isolation(self):
        """Test that listener errors don't break event bus."""
        
        class ErrorListener(TradeEventListener):
            def on_event(self, event: TradeEvent):
                raise ValueError("Test error")
        
        bus = TradeEventBus(log_events=False)
        error_listener = ErrorListener()
        good_listener = TestListener()
        
        bus.subscribe(error_listener)
        bus.subscribe(good_listener)
        
        # This should not raise despite error_listener raising
        bus.emit_trade_closed(
            symbol="BTCUSDT",
            data={"pnl": 100.0}
        )
        
        # Good listener should still receive the event
        assert len(good_listener.events_received) > 0
    
    def test_get_event_bus_singleton(self):
        """Test get_event_bus returns singleton."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        assert bus1 is bus2
