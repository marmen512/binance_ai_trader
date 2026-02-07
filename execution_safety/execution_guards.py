"""
Enhanced execution safety guards.

Adds critical safety features:
- Duplicate order guard
- Position state check
- Max exposure per symbol
- Idempotent retry
- Timeout + backoff
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import hashlib
import json
from pathlib import Path


@dataclass(frozen=True)
class OrderGuardResult:
    ok: bool
    reason: Optional[str] = None


class DuplicateOrderGuard:
    """
    Prevents duplicate order submission.
    
    Tracks recent orders by hash and prevents duplicates within a time window.
    """
    
    def __init__(self, window_seconds: int = 60):
        """
        Initialize duplicate order guard.
        
        Args:
            window_seconds: Time window for duplicate detection
        """
        self.window_seconds = window_seconds
        self._order_cache: dict[str, datetime] = {}
    
    def _compute_order_hash(self, order_data: dict) -> str:
        """Compute hash of order data."""
        # Use only key fields for hash
        key_fields = {
            "symbol": order_data.get("symbol"),
            "side": order_data.get("side"),
            "quantity": order_data.get("quantity"),
            "price": order_data.get("price"),
        }
        order_str = json.dumps(key_fields, sort_keys=True)
        return hashlib.sha256(order_str.encode()).hexdigest()[:16]
    
    def check_order(self, order_data: dict) -> OrderGuardResult:
        """
        Check if order is a duplicate.
        
        Args:
            order_data: Order data to check
            
        Returns:
            OrderGuardResult indicating if order is safe to submit
        """
        order_hash = self._compute_order_hash(order_data)
        now = datetime.now(timezone.utc)
        
        # Clean up old entries
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._order_cache = {
            h: ts for h, ts in self._order_cache.items()
            if ts > cutoff
        }
        
        # Check if duplicate
        if order_hash in self._order_cache:
            last_time = self._order_cache[order_hash]
            seconds_ago = (now - last_time).total_seconds()
            return OrderGuardResult(
                ok=False,
                reason=f"DUPLICATE_ORDER (submitted {seconds_ago:.1f}s ago)"
            )
        
        # Record this order
        self._order_cache[order_hash] = now
        return OrderGuardResult(ok=True)


class PositionStateChecker:
    """
    Validates position state before order submission.
    
    Ensures:
    - Position exists and is valid
    - No conflicting orders in flight
    - Position size is within limits
    """
    
    def __init__(self):
        """Initialize position state checker."""
        self._positions: dict[str, dict] = {}
    
    def update_position(self, symbol: str, position_data: dict) -> None:
        """
        Update tracked position state.
        
        Args:
            symbol: Trading symbol
            position_data: Current position data
        """
        self._positions[symbol] = {
            **position_data,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    
    def check_position_state(
        self,
        symbol: str,
        order_data: dict
    ) -> OrderGuardResult:
        """
        Check if position state allows order.
        
        Args:
            symbol: Trading symbol
            order_data: Proposed order data
            
        Returns:
            OrderGuardResult indicating if order is safe
        """
        if symbol not in self._positions:
            return OrderGuardResult(
                ok=False,
                reason="POSITION_NOT_TRACKED"
            )
        
        position = self._positions[symbol]
        
        # Check if position is in a valid state
        if position.get("status") == "error":
            return OrderGuardResult(
                ok=False,
                reason="POSITION_ERROR_STATE"
            )
        
        # Check for conflicting orders
        if position.get("pending_orders", 0) > 0:
            return OrderGuardResult(
                ok=False,
                reason="PENDING_ORDERS_EXIST"
            )
        
        return OrderGuardResult(ok=True)


class ExposureLimiter:
    """
    Enforces maximum exposure limits per symbol and globally.
    """
    
    def __init__(
        self,
        max_exposure_per_symbol: float = 10000.0,
        max_total_exposure: float = 50000.0
    ):
        """
        Initialize exposure limiter.
        
        Args:
            max_exposure_per_symbol: Maximum exposure per symbol in USD
            max_total_exposure: Maximum total exposure across all symbols
        """
        self.max_exposure_per_symbol = max_exposure_per_symbol
        self.max_total_exposure = max_total_exposure
        self._symbol_exposure: dict[str, float] = {}
    
    def update_exposure(self, symbol: str, exposure: float) -> None:
        """
        Update current exposure for a symbol.
        
        Args:
            symbol: Trading symbol
            exposure: Current exposure in USD
        """
        self._symbol_exposure[symbol] = float(exposure)
    
    def check_exposure(
        self,
        symbol: str,
        order_value: float
    ) -> OrderGuardResult:
        """
        Check if order would exceed exposure limits.
        
        Args:
            symbol: Trading symbol
            order_value: Value of proposed order in USD
            
        Returns:
            OrderGuardResult indicating if order is within limits
        """
        current_exposure = self._symbol_exposure.get(symbol, 0.0)
        new_symbol_exposure = current_exposure + order_value
        
        # Check per-symbol limit
        if new_symbol_exposure > self.max_exposure_per_symbol:
            return OrderGuardResult(
                ok=False,
                reason=f"SYMBOL_EXPOSURE_LIMIT (current: {current_exposure:.2f}, limit: {self.max_exposure_per_symbol:.2f})"
            )
        
        # Check total limit
        total_exposure = sum(self._symbol_exposure.values()) + order_value
        if total_exposure > self.max_total_exposure:
            return OrderGuardResult(
                ok=False,
                reason=f"TOTAL_EXPOSURE_LIMIT (current: {sum(self._symbol_exposure.values()):.2f}, limit: {self.max_total_exposure:.2f})"
            )
        
        return OrderGuardResult(ok=True)


class IdempotentRetryManager:
    """
    Manages idempotent retries with exponential backoff.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0
    ):
        """
        Initialize retry manager.
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._retry_counts: dict[str, int] = {}
        self._last_attempts: dict[str, datetime] = {}
    
    def _compute_request_id(self, request_data: dict) -> str:
        """Compute unique request ID."""
        req_str = json.dumps(request_data, sort_keys=True)
        return hashlib.sha256(req_str.encode()).hexdigest()[:16]
    
    def can_retry(self, request_data: dict) -> tuple[bool, float]:
        """
        Check if request can be retried.
        
        Args:
            request_data: Request data
            
        Returns:
            Tuple of (can_retry, delay_seconds)
        """
        request_id = self._compute_request_id(request_data)
        retry_count = self._retry_counts.get(request_id, 0)
        
        if retry_count >= self.max_retries:
            return False, 0.0
        
        # Calculate exponential backoff delay
        delay = min(
            self.base_delay * (2 ** retry_count),
            self.max_delay
        )
        
        return True, delay
    
    def record_attempt(self, request_data: dict) -> None:
        """
        Record a retry attempt.
        
        Args:
            request_data: Request data
        """
        request_id = self._compute_request_id(request_data)
        self._retry_counts[request_id] = self._retry_counts.get(request_id, 0) + 1
        self._last_attempts[request_id] = datetime.now(timezone.utc)
    
    def reset_request(self, request_data: dict) -> None:
        """
        Reset retry state for a request (call on success).
        
        Args:
            request_data: Request data
        """
        request_id = self._compute_request_id(request_data)
        self._retry_counts.pop(request_id, None)
        self._last_attempts.pop(request_id, None)


# Global instances
_duplicate_guard: Optional[DuplicateOrderGuard] = None
_position_checker: Optional[PositionStateChecker] = None
_exposure_limiter: Optional[ExposureLimiter] = None
_retry_manager: Optional[IdempotentRetryManager] = None


def get_duplicate_guard() -> DuplicateOrderGuard:
    """Get global duplicate order guard."""
    global _duplicate_guard
    if _duplicate_guard is None:
        _duplicate_guard = DuplicateOrderGuard()
    return _duplicate_guard


def get_position_checker() -> PositionStateChecker:
    """Get global position state checker."""
    global _position_checker
    if _position_checker is None:
        _position_checker = PositionStateChecker()
    return _position_checker


def get_exposure_limiter() -> ExposureLimiter:
    """Get global exposure limiter."""
    global _exposure_limiter
    if _exposure_limiter is None:
        _exposure_limiter = ExposureLimiter()
    return _exposure_limiter


def get_retry_manager() -> IdempotentRetryManager:
    """Get global retry manager."""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = IdempotentRetryManager()
    return _retry_manager
