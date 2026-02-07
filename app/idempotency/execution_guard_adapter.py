"""
Execution Guard Adapter

Non-invasive adapter that wraps execution module calls without modifying
execution/* files directly. Provides wrapper functions that use SideEffectWrapper.

DO NOT modify execution/* files - use these adapters instead.
"""

import logging
from typing import Any, Callable, Optional, Dict
import redis

from app.idempotency.side_effect_wrapper import (
    SideEffectWrapper,
    SideEffectType,
    order_entity_id,
    position_entity_id,
    pnl_entity_id,
    ledger_entity_id,
    trade_state_entity_id
)

logger = logging.getLogger(__name__)


class ExecutionGuardAdapter:
    """
    Adapter that provides idempotent wrappers for execution operations.
    
    Use this instead of directly calling execution/* modules to ensure
    exactly-once semantics without modifying existing code.
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize execution guard adapter.
        
        Args:
            redis_client: Redis client instance
        """
        self.wrapper = SideEffectWrapper(redis_client)
    
    def wrap_order_placement(
        self,
        operation: Callable[[], Any],
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
        ttl: Optional[int] = None
    ) -> tuple[bool, Optional[Any]]:
        """
        Wrap an order placement operation to ensure exactly-once execution.
        
        Args:
            operation: Function that places the order
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            price: Order price (optional for market orders)
            ttl: TTL in seconds (optional)
            
        Returns:
            Tuple of (was_executed, result)
        """
        entity_id = order_entity_id(symbol, side, quantity, price)
        logger.info(f"Wrapping order placement: {symbol} {side} {quantity} @ {price}")
        
        return self.wrapper.execute_once(
            SideEffectType.ORDER_PLACEMENT,
            entity_id,
            operation,
            ttl=ttl
        )
    
    def wrap_position_update(
        self,
        operation: Callable[[], Any],
        symbol: str,
        position_id: str,
        ttl: Optional[int] = None
    ) -> tuple[bool, Optional[Any]]:
        """
        Wrap a position update operation to ensure exactly-once execution.
        
        Args:
            operation: Function that updates the position
            symbol: Trading symbol
            position_id: Position identifier
            ttl: TTL in seconds (optional)
            
        Returns:
            Tuple of (was_executed, result)
        """
        entity_id = position_entity_id(symbol, position_id)
        logger.info(f"Wrapping position update: {symbol} position {position_id}")
        
        return self.wrapper.execute_once(
            SideEffectType.POSITION_UPDATE,
            entity_id,
            operation,
            ttl=ttl
        )
    
    def wrap_pnl_write(
        self,
        operation: Callable[[], Any],
        trade_id: str,
        ttl: Optional[int] = None
    ) -> tuple[bool, Optional[Any]]:
        """
        Wrap a PnL write operation to ensure exactly-once execution.
        
        Args:
            operation: Function that writes PnL
            trade_id: Trade identifier
            ttl: TTL in seconds (optional)
            
        Returns:
            Tuple of (was_executed, result)
        """
        entity_id = pnl_entity_id(trade_id)
        logger.info(f"Wrapping PnL write: trade {trade_id}")
        
        return self.wrapper.execute_once(
            SideEffectType.PNL_WRITE,
            entity_id,
            operation,
            ttl=ttl
        )
    
    def wrap_ledger_write(
        self,
        operation: Callable[[], Any],
        transaction_id: str,
        ttl: Optional[int] = None
    ) -> tuple[bool, Optional[Any]]:
        """
        Wrap a ledger write operation to ensure exactly-once execution.
        
        Args:
            operation: Function that writes to ledger
            transaction_id: Transaction identifier
            ttl: TTL in seconds (optional)
            
        Returns:
            Tuple of (was_executed, result)
        """
        entity_id = ledger_entity_id(transaction_id)
        logger.info(f"Wrapping ledger write: transaction {transaction_id}")
        
        return self.wrapper.execute_once(
            SideEffectType.LEDGER_WRITE,
            entity_id,
            operation,
            ttl=ttl
        )
    
    def wrap_trade_state_write(
        self,
        operation: Callable[[], Any],
        trade_id: str,
        state: str,
        ttl: Optional[int] = None
    ) -> tuple[bool, Optional[Any]]:
        """
        Wrap a trade state write operation to ensure exactly-once execution.
        
        Args:
            operation: Function that writes trade state
            trade_id: Trade identifier
            state: New state value
            ttl: TTL in seconds (optional)
            
        Returns:
            Tuple of (was_executed, result)
        """
        entity_id = trade_state_entity_id(trade_id, state)
        logger.info(f"Wrapping trade state write: trade {trade_id} -> {state}")
        
        return self.wrapper.execute_once(
            SideEffectType.TRADE_STATE_WRITE,
            entity_id,
            operation,
            ttl=ttl
        )


# Convenience functions for standalone usage

def wrap_order_placement(
    redis_client: redis.Redis,
    operation: Callable[[], Any],
    symbol: str,
    side: str,
    quantity: float,
    price: Optional[float] = None,
    ttl: Optional[int] = None
) -> tuple[bool, Optional[Any]]:
    """Standalone wrapper for order placement"""
    adapter = ExecutionGuardAdapter(redis_client)
    return adapter.wrap_order_placement(operation, symbol, side, quantity, price, ttl)


def wrap_position_update(
    redis_client: redis.Redis,
    operation: Callable[[], Any],
    symbol: str,
    position_id: str,
    ttl: Optional[int] = None
) -> tuple[bool, Optional[Any]]:
    """Standalone wrapper for position update"""
    adapter = ExecutionGuardAdapter(redis_client)
    return adapter.wrap_position_update(operation, symbol, position_id, ttl)


def wrap_pnl_write(
    redis_client: redis.Redis,
    operation: Callable[[], Any],
    trade_id: str,
    ttl: Optional[int] = None
) -> tuple[bool, Optional[Any]]:
    """Standalone wrapper for PnL write"""
    adapter = ExecutionGuardAdapter(redis_client)
    return adapter.wrap_pnl_write(operation, trade_id, ttl)


def wrap_ledger_write(
    redis_client: redis.Redis,
    operation: Callable[[], Any],
    transaction_id: str,
    ttl: Optional[int] = None
) -> tuple[bool, Optional[Any]]:
    """Standalone wrapper for ledger write"""
    adapter = ExecutionGuardAdapter(redis_client)
    return adapter.wrap_ledger_write(operation, transaction_id, ttl)


def wrap_trade_state_write(
    redis_client: redis.Redis,
    operation: Callable[[], Any],
    trade_id: str,
    state: str,
    ttl: Optional[int] = None
) -> tuple[bool, Optional[Any]]:
    """Standalone wrapper for trade state write"""
    adapter = ExecutionGuardAdapter(redis_client)
    return adapter.wrap_trade_state_write(operation, trade_id, state, ttl)
