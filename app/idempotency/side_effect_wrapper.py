"""
Side Effect Wrapper for Idempotent Execution

Provides execute_once() pattern for critical side effects.
Uses Redis SETNX for atomic operations with result caching.

Supported side effect types:
- ORDER_PLACEMENT
- POSITION_UPDATE
- PNL_WRITE
- LEDGER_WRITE
- TRADE_STATE_WRITE
"""

import logging
import hashlib
import json
from typing import Optional, Dict, Any, Callable, TypeVar
from datetime import timedelta
import redis

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SideEffectType:
    """Types of side effects that need idempotency protection"""
    ORDER_PLACEMENT = "order_placement"
    POSITION_UPDATE = "position_update"
    PNL_WRITE = "pnl_write"
    LEDGER_WRITE = "ledger_write"
    TRADE_STATE_WRITE = "trade_state_write"


class SideEffectWrapper:
    """
    Wraps side effect operations to ensure exactly-once execution.
    
    Key pattern: effect:{type}:{entity_id}
    
    Features:
    - Atomic SETNX for lock acquisition
    - TTL-based automatic cleanup (72 hours default)
    - Result caching for duplicate calls
    - Automatic retry on operation failure
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        namespace: str = "effect",
        default_ttl: int = 259200  # 72 hours
    ):
        """
        Initialize side effect wrapper.
        
        Args:
            redis_client: Redis client instance
            namespace: Namespace prefix for keys (default: "effect")
            default_ttl: Default TTL in seconds (default: 72 hours)
        """
        self.redis = redis_client
        self.namespace = namespace
        self.default_ttl = default_ttl
    
    def _make_key(self, effect_type: str, entity_id: str) -> str:
        """
        Generate idempotency key for a side effect.
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            
        Returns:
            Redis key string
        """
        return f"{self.namespace}:{effect_type}:{entity_id}"
    
    def is_executed(self, effect_type: str, entity_id: str) -> bool:
        """
        Check if a side effect has already been executed.
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            
        Returns:
            True if already executed, False otherwise
        """
        key = self._make_key(effect_type, entity_id)
        try:
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check side effect execution: {e}")
            # Fail safe: assume not executed to allow operation
            return False
    
    def mark_executed(
        self,
        effect_type: str,
        entity_id: str,
        result_data: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Mark a side effect as executed using atomic SETNX.
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            result_data: Optional result data to cache
            ttl: TTL in seconds (uses default if None)
            
        Returns:
            True if marked successfully (first execution), False if already marked
        """
        key = self._make_key(effect_type, entity_id)
        ttl = ttl or self.default_ttl
        value = result_data if result_data is not None else ""
        
        try:
            # Use SETNX (SET if Not eXists) for atomic operation
            success = self.redis.set(key, value, ex=ttl, nx=True)
            return bool(success)
        except Exception as e:
            logger.error(f"Failed to mark side effect as executed: {e}")
            # Fail safe: return False to prevent duplicate execution
            return False
    
    def get_cached_result(self, effect_type: str, entity_id: str) -> Optional[str]:
        """
        Get cached result from a previous execution.
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            
        Returns:
            Cached result data or None if not found
        """
        key = self._make_key(effect_type, entity_id)
        try:
            result = self.redis.get(key)
            return result.decode('utf-8') if result else None
        except Exception as e:
            logger.error(f"Failed to get cached result: {e}")
            return None
    
    def execute_once(
        self,
        effect_type: str,
        entity_id: str,
        operation: Callable[[], T],
        ttl: Optional[int] = None,
        cache_result: bool = True
    ) -> tuple[bool, Optional[T]]:
        """
        Execute a side effect operation exactly once using atomic check-and-execute.
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            operation: Callable that performs the side effect
            ttl: TTL in seconds (uses default if None)
            cache_result: Whether to cache the result
            
        Returns:
            Tuple of (was_executed, result)
            - was_executed: True if operation was executed, False if skipped (duplicate)
            - result: Operation result or cached result from previous execution
        """
        key = self._make_key(effect_type, entity_id)
        ttl = ttl or self.default_ttl
        
        # First check if already executed (fast path)
        if self.is_executed(effect_type, entity_id):
            logger.info(f"Side effect already executed: {effect_type}:{entity_id}")
            cached = self.get_cached_result(effect_type, entity_id)
            
            # Try to deserialize cached result
            if cached and cache_result:
                try:
                    result = json.loads(cached)
                    return False, result
                except (json.JSONDecodeError, TypeError):
                    return False, cached
            return False, cached
        
        # Try to mark as executed atomically
        if self.mark_executed(effect_type, entity_id, "", ttl):
            # We got the lock, execute the operation
            try:
                logger.info(f"Executing side effect: {effect_type}:{entity_id}")
                result = operation()
                
                # Cache the result if requested (best effort)
                if cache_result:
                    try:
                        result_str = json.dumps(result) if result is not None else ""
                        self.redis.set(key, result_str, ex=ttl)
                    except (TypeError, json.JSONEncodeError) as e:
                        logger.warning(f"Failed to serialize result for caching: {e}")
                        # Try string representation as fallback
                        try:
                            self.redis.set(key, str(result), ex=ttl)
                        except Exception as e2:
                            logger.warning(f"Failed to cache result: {e2}")
                
                return True, result
            except Exception as e:
                # Operation failed, remove the mark to allow retry
                logger.error(f"Side effect operation failed: {e}")
                try:
                    self.redis.delete(key)
                except Exception as del_e:
                    logger.error(f"Failed to remove failed side effect mark: {del_e}")
                raise
        else:
            # Someone else executed it first (race condition)
            logger.info(f"Side effect already executed by another process: {effect_type}:{entity_id}")
            cached = self.get_cached_result(effect_type, entity_id)
            
            # Try to deserialize cached result
            if cached and cache_result:
                try:
                    result = json.loads(cached)
                    return False, result
                except (json.JSONDecodeError, TypeError):
                    return False, cached
            return False, cached
    
    def clear(self, effect_type: str, entity_id: str) -> bool:
        """
        Clear a side effect mark (use with caution).
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            
        Returns:
            True if cleared, False otherwise
        """
        key = self._make_key(effect_type, entity_id)
        try:
            return self.redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Failed to clear side effect mark: {e}")
            return False
    
    def get_ttl(self, effect_type: str, entity_id: str) -> Optional[int]:
        """
        Get remaining TTL for a side effect mark.
        
        Args:
            effect_type: Type of side effect
            entity_id: Unique identifier for the entity
            
        Returns:
            TTL in seconds, or None if key doesn't exist or error
        """
        key = self._make_key(effect_type, entity_id)
        try:
            ttl = self.redis.ttl(key)
            return ttl if ttl > 0 else None
        except Exception as e:
            logger.error(f"Failed to get TTL: {e}")
            return None


def generate_entity_id(effect_type: str, **kwargs) -> str:
    """
    Generate a deterministic entity ID from parameters.
    
    Args:
        effect_type: Type of side effect
        **kwargs: Parameters that uniquely identify the entity
        
    Returns:
        Deterministic hash-based entity ID
    """
    # Sort kwargs to ensure deterministic ordering
    sorted_params = sorted(kwargs.items())
    param_str = "|".join(f"{k}={v}" for k, v in sorted_params)
    combined = f"{effect_type}|{param_str}"
    
    # Use SHA256 for consistent hashing
    hash_obj = hashlib.sha256(combined.encode('utf-8'))
    return hash_obj.hexdigest()[:32]  # Use first 32 chars for readability


def order_entity_id(symbol: str, side: str, quantity: float, price: Optional[float] = None) -> str:
    """Generate entity ID for order placement"""
    params = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
    }
    if price is not None:
        params["price"] = price
    return generate_entity_id(SideEffectType.ORDER_PLACEMENT, **params)


def position_entity_id(symbol: str, position_id: str) -> str:
    """Generate entity ID for position update"""
    return generate_entity_id(
        SideEffectType.POSITION_UPDATE,
        symbol=symbol,
        position_id=position_id
    )


def pnl_entity_id(trade_id: str) -> str:
    """Generate entity ID for PnL write"""
    return generate_entity_id(
        SideEffectType.PNL_WRITE,
        trade_id=trade_id
    )


def ledger_entity_id(transaction_id: str) -> str:
    """Generate entity ID for ledger write"""
    return generate_entity_id(
        SideEffectType.LEDGER_WRITE,
        transaction_id=transaction_id
    )


def trade_state_entity_id(trade_id: str, state: str) -> str:
    """Generate entity ID for trade state write"""
    return generate_entity_id(
        SideEffectType.TRADE_STATE_WRITE,
        trade_id=trade_id,
        state=state
    )
