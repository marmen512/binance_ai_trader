"""
Idempotency module for production safety.

Provides wrapper functions and adapters for side effect protection
without modifying execution modules directly.
"""

from app.idempotency.side_effect_wrapper import (
    SideEffectWrapper,
    SideEffectType,
    generate_entity_id
)
from app.idempotency.execution_guard_adapter import (
    ExecutionGuardAdapter,
    wrap_order_placement,
    wrap_position_update,
    wrap_pnl_write,
    wrap_ledger_write,
    wrap_trade_state_write
)

__all__ = [
    "SideEffectWrapper",
    "SideEffectType",
    "generate_entity_id",
    "ExecutionGuardAdapter",
    "wrap_order_placement",
    "wrap_position_update",
    "wrap_pnl_write",
    "wrap_ledger_write",
    "wrap_trade_state_write",
]
