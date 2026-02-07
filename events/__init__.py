"""
Trade events module for decoupled event-driven architecture.

This module provides the event system that allows execution to emit
events without directly calling adaptive or analytics code.
"""

from events.trade_events import (
    TradeEvent,
    TradeEventType,
    TradeEventBus,
    TradeEventListener,
    get_event_bus,
    initialize_event_system
)

__all__ = [
    'TradeEvent',
    'TradeEventType',
    'TradeEventBus',
    'TradeEventListener',
    'get_event_bus',
    'initialize_event_system',
]
