"""
Retry Metrics

Collects and exposes metrics for retry operations:
- retry_rate: Rate of retries per minute
- retry_success_rate: Percentage of successful retries
- retry_failure_rate: Percentage of failed retries
- avg_attempts: Average number of retry attempts
- retry_block_rate: Rate of retries blocked by guards
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import redis

logger = logging.getLogger(__name__)


class RetryMetrics:
    """
    Collects and tracks metrics for retry operations.
    
    Uses Redis for distributed metric collection across workers.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        namespace: str = "retry_metrics"
    ):
        """
        Initialize retry metrics.
        
        Args:
            redis_client: Redis client instance
            namespace: Redis namespace prefix
        """
        self.redis = redis_client
        self.namespace = namespace
        
        # Metric keys
        self.retry_count_key = f"{namespace}:retry_count"
        self.success_count_key = f"{namespace}:success_count"
        self.failure_count_key = f"{namespace}:failure_count"
        self.block_count_key = f"{namespace}:block_count"
        self.attempts_key = f"{namespace}:attempts"
        self.retry_times_key = f"{namespace}:retry_times"
        
        # Per-job-type metrics
        self.job_type_prefix = f"{namespace}:job_type"
    
    def record_retry_attempt(
        self,
        job_type: str,
        attempt_number: int,
        timestamp: Optional[float] = None
    ) -> None:
        """
        Record a retry attempt.
        
        Args:
            job_type: Type of job being retried
            attempt_number: Attempt number (1, 2, 3, ...)
            timestamp: Timestamp (uses current time if None)
        """
        try:
            ts = timestamp or time.time()
            
            # Increment global retry count
            self.redis.incr(self.retry_count_key)
            
            # Record attempt number for average calculation
            self.redis.rpush(self.attempts_key, str(attempt_number))
            
            # Trim attempts list to last 10000 entries
            self.redis.ltrim(self.attempts_key, -10000, -1)
            
            # Record timestamp in sorted set for rate calculation
            self.redis.zadd(self.retry_times_key, {str(ts): ts})
            
            # Clean old timestamps (keep last 1 hour)
            cutoff = ts - 3600
            self.redis.zremrangebyscore(self.retry_times_key, 0, cutoff)
            
            # Job-type specific metrics
            job_key = f"{self.job_type_prefix}:{job_type}:retry_count"
            self.redis.incr(job_key)
            
        except Exception as e:
            logger.error(f"Failed to record retry attempt: {e}")
    
    def record_retry_success(self, job_type: str) -> None:
        """
        Record a successful retry.
        
        Args:
            job_type: Type of job
        """
        try:
            # Increment global success count
            self.redis.incr(self.success_count_key)
            
            # Job-type specific
            job_key = f"{self.job_type_prefix}:{job_type}:success_count"
            self.redis.incr(job_key)
            
        except Exception as e:
            logger.error(f"Failed to record retry success: {e}")
    
    def record_retry_failure(self, job_type: str) -> None:
        """
        Record a failed retry.
        
        Args:
            job_type: Type of job
        """
        try:
            # Increment global failure count
            self.redis.incr(self.failure_count_key)
            
            # Job-type specific
            job_key = f"{self.job_type_prefix}:{job_type}:failure_count"
            self.redis.incr(job_key)
            
        except Exception as e:
            logger.error(f"Failed to record retry failure: {e}")
    
    def record_retry_blocked(self, job_type: str, reason: str) -> None:
        """
        Record a blocked retry.
        
        Args:
            job_type: Type of job
            reason: Reason for blocking (e.g., "circuit_open", "non_retryable")
        """
        try:
            # Increment global block count
            self.redis.incr(self.block_count_key)
            
            # Job-type specific
            job_key = f"{self.job_type_prefix}:{job_type}:block_count"
            self.redis.incr(job_key)
            
            # Reason-specific count
            reason_key = f"{self.namespace}:block_reason:{reason}"
            self.redis.incr(reason_key)
            
        except Exception as e:
            logger.error(f"Failed to record retry blocked: {e}")
    
    def get_retry_rate(self, time_window_minutes: int = 60) -> float:
        """
        Calculate retry rate (retries per minute).
        
        Args:
            time_window_minutes: Time window for calculation
            
        Returns:
            Retry rate (retries per minute)
        """
        try:
            current_time = time.time()
            cutoff_time = current_time - (time_window_minutes * 60)
            
            # Count retries in time window
            count = self.redis.zcount(self.retry_times_key, cutoff_time, current_time)
            
            # Calculate rate
            return count / time_window_minutes if time_window_minutes > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate retry rate: {e}")
            return 0.0
    
    def get_retry_success_rate(self) -> float:
        """
        Calculate retry success rate (percentage).
        
        Returns:
            Success rate as decimal (0.0 to 1.0)
        """
        try:
            success_count = int(self.redis.get(self.success_count_key) or 0)
            retry_count = int(self.redis.get(self.retry_count_key) or 0)
            
            if retry_count == 0:
                return 0.0
            
            return success_count / retry_count
            
        except Exception as e:
            logger.error(f"Failed to calculate success rate: {e}")
            return 0.0
    
    def get_retry_failure_rate(self) -> float:
        """
        Calculate retry failure rate (percentage).
        
        Returns:
            Failure rate as decimal (0.0 to 1.0)
        """
        try:
            failure_count = int(self.redis.get(self.failure_count_key) or 0)
            retry_count = int(self.redis.get(self.retry_count_key) or 0)
            
            if retry_count == 0:
                return 0.0
            
            return failure_count / retry_count
            
        except Exception as e:
            logger.error(f"Failed to calculate failure rate: {e}")
            return 0.0
    
    def get_avg_attempts(self) -> float:
        """
        Calculate average number of retry attempts.
        
        Returns:
            Average attempts
        """
        try:
            # Get all attempts
            attempts = self.redis.lrange(self.attempts_key, 0, -1)
            
            if not attempts:
                return 0.0
            
            # Convert to integers and calculate average
            attempt_values = [int(a) for a in attempts]
            return sum(attempt_values) / len(attempt_values)
            
        except Exception as e:
            logger.error(f"Failed to calculate average attempts: {e}")
            return 0.0
    
    def get_retry_block_rate(self) -> float:
        """
        Calculate rate of blocked retries (percentage).
        
        Returns:
            Block rate as decimal (0.0 to 1.0)
        """
        try:
            block_count = int(self.redis.get(self.block_count_key) or 0)
            retry_count = int(self.redis.get(self.retry_count_key) or 0)
            
            # Total retry attempts (successful + failed + blocked)
            total_attempts = retry_count + block_count
            
            if total_attempts == 0:
                return 0.0
            
            return block_count / total_attempts
            
        except Exception as e:
            logger.error(f"Failed to calculate block rate: {e}")
            return 0.0
    
    def get_job_type_metrics(self, job_type: str) -> Dict[str, Any]:
        """
        Get metrics for a specific job type.
        
        Args:
            job_type: Type of job
            
        Returns:
            Dictionary of metrics
        """
        try:
            retry_count = int(self.redis.get(f"{self.job_type_prefix}:{job_type}:retry_count") or 0)
            success_count = int(self.redis.get(f"{self.job_type_prefix}:{job_type}:success_count") or 0)
            failure_count = int(self.redis.get(f"{self.job_type_prefix}:{job_type}:failure_count") or 0)
            block_count = int(self.redis.get(f"{self.job_type_prefix}:{job_type}:block_count") or 0)
            
            success_rate = success_count / retry_count if retry_count > 0 else 0.0
            failure_rate = failure_count / retry_count if retry_count > 0 else 0.0
            
            return {
                "job_type": job_type,
                "retry_count": retry_count,
                "success_count": success_count,
                "failure_count": failure_count,
                "block_count": block_count,
                "success_rate": success_rate,
                "failure_rate": failure_rate
            }
            
        except Exception as e:
            logger.error(f"Failed to get job type metrics: {e}")
            return {"job_type": job_type, "error": str(e)}
    
    def get_all_metrics(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get all retry metrics.
        
        Args:
            time_window_minutes: Time window for rate calculation
            
        Returns:
            Dictionary of all metrics
        """
        try:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "time_window_minutes": time_window_minutes,
                "retry_rate_per_minute": self.get_retry_rate(time_window_minutes),
                "retry_success_rate": self.get_retry_success_rate(),
                "retry_failure_rate": self.get_retry_failure_rate(),
                "avg_attempts": self.get_avg_attempts(),
                "retry_block_rate": self.get_retry_block_rate(),
                "total_retries": int(self.redis.get(self.retry_count_key) or 0),
                "total_successes": int(self.redis.get(self.success_count_key) or 0),
                "total_failures": int(self.redis.get(self.failure_count_key) or 0),
                "total_blocks": int(self.redis.get(self.block_count_key) or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to get all metrics: {e}")
            return {"error": str(e)}
    
    def get_block_reasons(self) -> Dict[str, int]:
        """
        Get count of blocks by reason.
        
        Returns:
            Dictionary mapping reason to count
        """
        try:
            # Get all block reason keys
            pattern = f"{self.namespace}:block_reason:*"
            keys = self.redis.keys(pattern)
            
            reasons = {}
            for key in keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                reason = key_str.split(':')[-1]
                count = int(self.redis.get(key) or 0)
                reasons[reason] = count
            
            return reasons
            
        except Exception as e:
            logger.error(f"Failed to get block reasons: {e}")
            return {}
    
    def reset_metrics(self) -> None:
        """Reset all metrics (use with caution)"""
        try:
            # Delete all metric keys
            pattern = f"{self.namespace}:*"
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
            
            logger.info("Retry metrics reset")
            
        except Exception as e:
            logger.error(f"Failed to reset metrics: {e}")
    
    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        try:
            metrics = self.get_all_metrics()
            
            lines = [
                "# HELP retry_rate_per_minute Number of retries per minute",
                "# TYPE retry_rate_per_minute gauge",
                f"retry_rate_per_minute {metrics['retry_rate_per_minute']}",
                "",
                "# HELP retry_success_rate Retry success rate (0.0 to 1.0)",
                "# TYPE retry_success_rate gauge",
                f"retry_success_rate {metrics['retry_success_rate']}",
                "",
                "# HELP retry_failure_rate Retry failure rate (0.0 to 1.0)",
                "# TYPE retry_failure_rate gauge",
                f"retry_failure_rate {metrics['retry_failure_rate']}",
                "",
                "# HELP retry_avg_attempts Average number of retry attempts",
                "# TYPE retry_avg_attempts gauge",
                f"retry_avg_attempts {metrics['avg_attempts']}",
                "",
                "# HELP retry_block_rate Rate of blocked retries (0.0 to 1.0)",
                "# TYPE retry_block_rate gauge",
                f"retry_block_rate {metrics['retry_block_rate']}",
                "",
                "# HELP retry_total_count Total number of retries",
                "# TYPE retry_total_count counter",
                f"retry_total_count {metrics['total_retries']}",
                "",
                "# HELP retry_total_successes Total number of successful retries",
                "# TYPE retry_total_successes counter",
                f"retry_total_successes {metrics['total_successes']}",
                "",
                "# HELP retry_total_failures Total number of failed retries",
                "# TYPE retry_total_failures counter",
                f"retry_total_failures {metrics['total_failures']}",
                "",
                "# HELP retry_total_blocks Total number of blocked retries",
                "# TYPE retry_total_blocks counter",
                f"retry_total_blocks {metrics['total_blocks']}",
                ""
            ]
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Failed to export Prometheus format: {e}")
            return f"# Error: {e}\n"
