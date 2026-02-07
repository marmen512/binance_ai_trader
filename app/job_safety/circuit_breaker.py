"""
Retry Circuit Breaker

Prevents retry storms by pausing retries when failure rate exceeds threshold.

Features:
- Failure threshold tracking (N failures in M minutes)
- Automatic pause on threshold breach
- Alert event emission
- Manual override requirement to resume
- Per-job-type circuit breakers
"""

import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from collections import deque
import redis

logger = logging.getLogger(__name__)


class CircuitState:
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit broken, retries blocked
    HALF_OPEN = "half_open"  # Testing if system recovered


class CircuitBreaker:
    """
    Circuit breaker for retry operations.
    
    Tracks failure rate and opens circuit when threshold is exceeded.
    Requires manual intervention to resume after circuit opens.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        job_type: str = "default",
        failure_threshold: int = 10,
        time_window_minutes: int = 5,
        namespace: str = "circuit_breaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            redis_client: Redis client instance
            job_type: Type of job (for per-type circuit breakers)
            failure_threshold: Number of failures to trigger circuit break
            time_window_minutes: Time window for counting failures
            namespace: Redis namespace prefix
        """
        self.redis = redis_client
        self.job_type = job_type
        self.failure_threshold = failure_threshold
        self.time_window_minutes = time_window_minutes
        self.namespace = namespace
        
        # Redis keys
        self.state_key = f"{namespace}:{job_type}:state"
        self.failures_key = f"{namespace}:{job_type}:failures"
        self.manual_override_key = f"{namespace}:{job_type}:manual_override"
        self.last_alert_key = f"{namespace}:{job_type}:last_alert"
        
        # Alert cooldown (prevent alert spam)
        self.alert_cooldown_seconds = 300  # 5 minutes
    
    def get_state(self) -> str:
        """Get current circuit breaker state"""
        try:
            state = self.redis.get(self.state_key)
            return state.decode('utf-8') if state else CircuitState.CLOSED
        except Exception as e:
            logger.error(f"Failed to get circuit state: {e}")
            return CircuitState.CLOSED
    
    def set_state(self, state: str) -> bool:
        """Set circuit breaker state"""
        try:
            self.redis.set(self.state_key, state)
            return True
        except Exception as e:
            logger.error(f"Failed to set circuit state: {e}")
            return False
    
    def record_failure(self) -> None:
        """
        Record a failure and check if threshold is exceeded.
        
        If threshold is exceeded, opens the circuit.
        """
        try:
            current_time = time.time()
            
            # Add failure to sorted set with timestamp as score
            self.redis.zadd(self.failures_key, {str(current_time): current_time})
            
            # Remove old failures outside time window
            cutoff_time = current_time - (self.time_window_minutes * 60)
            self.redis.zremrangebyscore(self.failures_key, 0, cutoff_time)
            
            # Check if threshold exceeded
            failure_count = self.redis.zcard(self.failures_key)
            
            if failure_count >= self.failure_threshold:
                current_state = self.get_state()
                if current_state == CircuitState.CLOSED:
                    logger.error(
                        f"Circuit breaker threshold exceeded for {self.job_type}: "
                        f"{failure_count} failures in {self.time_window_minutes} minutes"
                    )
                    self.open_circuit()
        except Exception as e:
            logger.error(f"Failed to record failure: {e}")
    
    def record_success(self) -> None:
        """Record a successful execution"""
        try:
            # If in half-open state and success, close the circuit
            if self.get_state() == CircuitState.HALF_OPEN:
                logger.info(f"Circuit breaker closing for {self.job_type} after successful retry")
                self.set_state(CircuitState.CLOSED)
                # Clear failures
                self.redis.delete(self.failures_key)
        except Exception as e:
            logger.error(f"Failed to record success: {e}")
    
    def open_circuit(self) -> None:
        """Open the circuit (block all retries)"""
        try:
            self.set_state(CircuitState.OPEN)
            
            # Emit alert event
            self.emit_alert_event(
                "circuit_opened",
                f"Circuit breaker opened for {self.job_type}: "
                f"threshold {self.failure_threshold} exceeded in {self.time_window_minutes} minutes"
            )
            
            logger.critical(
                f"CIRCUIT BREAKER OPEN for {self.job_type}. "
                "Manual override required to resume retries."
            )
        except Exception as e:
            logger.error(f"Failed to open circuit: {e}")
    
    def close_circuit(self) -> None:
        """Close the circuit (allow retries)"""
        try:
            self.set_state(CircuitState.CLOSED)
            self.redis.delete(self.failures_key)
            self.redis.delete(self.manual_override_key)
            logger.info(f"Circuit breaker closed for {self.job_type}")
        except Exception as e:
            logger.error(f"Failed to close circuit: {e}")
    
    def set_half_open(self) -> None:
        """Set circuit to half-open state (test if system recovered)"""
        try:
            self.set_state(CircuitState.HALF_OPEN)
            logger.info(f"Circuit breaker half-open for {self.job_type} - testing recovery")
        except Exception as e:
            logger.error(f"Failed to set half-open state: {e}")
    
    def is_open(self) -> bool:
        """Check if circuit is open (retries blocked)"""
        state = self.get_state()
        return state == CircuitState.OPEN
    
    def can_retry(self) -> tuple[bool, Optional[str]]:
        """
        Check if retry is allowed.
        
        Returns:
            Tuple of (allowed, reason)
            - allowed: True if retry allowed, False otherwise
            - reason: Reason for blocking if not allowed
        """
        state = self.get_state()
        
        if state == CircuitState.CLOSED:
            return True, None
        
        if state == CircuitState.OPEN:
            # Check if manual override is set
            if self.has_manual_override():
                logger.info(f"Manual override active for {self.job_type}, allowing retry")
                return True, None
            
            return False, f"Circuit breaker open for {self.job_type}. Manual override required."
        
        if state == CircuitState.HALF_OPEN:
            # Allow limited retries in half-open state
            return True, None
        
        return False, f"Unknown circuit state: {state}"
    
    def set_manual_override(self, user: str, reason: str) -> None:
        """
        Set manual override to allow retries despite open circuit.
        
        Args:
            user: User who set the override
            reason: Reason for override
        """
        try:
            override_data = {
                "user": user,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.redis.hset(self.manual_override_key, mapping=override_data)
            
            # Move to half-open state to test recovery
            self.set_half_open()
            
            logger.warning(
                f"Manual override set for {self.job_type} by {user}: {reason}"
            )
            
            self.emit_alert_event(
                "manual_override_set",
                f"Manual override set for {self.job_type} by {user}: {reason}"
            )
        except Exception as e:
            logger.error(f"Failed to set manual override: {e}")
    
    def has_manual_override(self) -> bool:
        """Check if manual override is active"""
        try:
            return self.redis.exists(self.manual_override_key) > 0
        except Exception as e:
            logger.error(f"Failed to check manual override: {e}")
            return False
    
    def get_failure_count(self) -> int:
        """Get current failure count in time window"""
        try:
            # Remove old failures
            current_time = time.time()
            cutoff_time = current_time - (self.time_window_minutes * 60)
            self.redis.zremrangebyscore(self.failures_key, 0, cutoff_time)
            
            return self.redis.zcard(self.failures_key)
        except Exception as e:
            logger.error(f"Failed to get failure count: {e}")
            return 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        try:
            state = self.get_state()
            failure_count = self.get_failure_count()
            has_override = self.has_manual_override()
            
            return {
                "job_type": self.job_type,
                "state": state,
                "failure_count": failure_count,
                "failure_threshold": self.failure_threshold,
                "time_window_minutes": self.time_window_minutes,
                "has_manual_override": has_override,
                "can_retry": self.can_retry()[0]
            }
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {
                "job_type": self.job_type,
                "error": str(e)
            }
    
    def emit_alert_event(self, event_type: str, message: str) -> None:
        """
        Emit alert event (can be integrated with monitoring system).
        
        Args:
            event_type: Type of alert event
            message: Alert message
        """
        try:
            # Check alert cooldown to prevent spam
            last_alert = self.redis.get(self.last_alert_key)
            if last_alert:
                last_alert_time = float(last_alert)
                if time.time() - last_alert_time < self.alert_cooldown_seconds:
                    logger.debug("Alert cooldown active, skipping alert emission")
                    return
            
            # Update last alert time
            self.redis.set(self.last_alert_key, str(time.time()))
            
            # Log the alert
            logger.critical(f"ALERT [{event_type}]: {message}")
            
            # TODO: Integrate with external alerting system (PagerDuty, Slack, etc.)
            # For now, just log
            
        except Exception as e:
            logger.error(f"Failed to emit alert event: {e}")
    
    def reset(self) -> None:
        """Reset circuit breaker (clear all state)"""
        try:
            self.redis.delete(self.state_key)
            self.redis.delete(self.failures_key)
            self.redis.delete(self.manual_override_key)
            self.redis.delete(self.last_alert_key)
            logger.info(f"Circuit breaker reset for {self.job_type}")
        except Exception as e:
            logger.error(f"Failed to reset circuit breaker: {e}")


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers for different job types.
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize circuit breaker manager.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self,
        job_type: str,
        failure_threshold: int = 10,
        time_window_minutes: int = 5
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker for a job type.
        
        Args:
            job_type: Type of job
            failure_threshold: Number of failures to trigger circuit break
            time_window_minutes: Time window for counting failures
            
        Returns:
            CircuitBreaker instance
        """
        if job_type not in self.breakers:
            self.breakers[job_type] = CircuitBreaker(
                self.redis,
                job_type,
                failure_threshold,
                time_window_minutes
            )
        return self.breakers[job_type]
    
    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {
            job_type: breaker.get_status()
            for job_type, breaker in self.breakers.items()
        }
