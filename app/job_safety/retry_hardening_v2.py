"""
Retry Hardening v2

Enhanced retry system monitoring with:
- RetryWindowTracker: Track retry windows
- RetryHistogram: Attempt distribution analysis
- RetryAnomalyDetector: Detect anomalies in retry patterns
- RetrySpikeDetector: Detect sudden spikes in retries
"""

import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import redis

logger = logging.getLogger(__name__)


class RetryWindow:
    """Represents a retry window for tracking"""
    
    def __init__(self, job_id: str, start_time: float):
        self.job_id = job_id
        self.start_time = start_time
        self.end_time: Optional[float] = None
        self.attempt_count = 0
        self.success = False
    
    def close(self, success: bool) -> None:
        """Close the retry window"""
        self.end_time = time.time()
        self.success = success
    
    def duration(self) -> Optional[float]:
        """Get duration of retry window in seconds"""
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def is_closed(self) -> bool:
        """Check if window is closed"""
        return self.end_time is not None


class RetryWindowTracker:
    """
    Tracks retry windows for jobs.
    
    A retry window is the time span from first attempt to final success/failure.
    """
    
    def __init__(self, redis_client: redis.Redis, namespace: str = "retry_window"):
        """
        Initialize retry window tracker.
        
        Args:
            redis_client: Redis client instance
            namespace: Redis namespace prefix
        """
        self.redis = redis_client
        self.namespace = namespace
        self.active_windows: Dict[str, RetryWindow] = {}
    
    def _window_key(self, job_id: str) -> str:
        """Generate Redis key for retry window"""
        return f"{self.namespace}:{job_id}"
    
    def start_window(self, job_id: str) -> RetryWindow:
        """
        Start tracking a retry window.
        
        Args:
            job_id: Job identifier
            
        Returns:
            RetryWindow instance
        """
        if job_id in self.active_windows:
            logger.warning(f"Retry window already exists for job {job_id}")
            return self.active_windows[job_id]
        
        window = RetryWindow(job_id, time.time())
        self.active_windows[job_id] = window
        
        # Store in Redis
        try:
            key = self._window_key(job_id)
            self.redis.hset(key, mapping={
                "start_time": str(window.start_time),
                "attempt_count": "0",
                "status": "active"
            })
            self.redis.expire(key, 86400)  # 24 hours TTL
        except Exception as e:
            logger.error(f"Failed to store retry window in Redis: {e}")
        
        logger.debug(f"Started retry window for job {job_id}")
        return window
    
    def increment_attempt(self, job_id: str) -> int:
        """
        Increment attempt count for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Current attempt count
        """
        if job_id in self.active_windows:
            self.active_windows[job_id].attempt_count += 1
            count = self.active_windows[job_id].attempt_count
        else:
            # Window not in memory, try Redis
            window = self.start_window(job_id)
            window.attempt_count = 1
            count = 1
        
        # Update Redis
        try:
            key = self._window_key(job_id)
            self.redis.hincrby(key, "attempt_count", 1)
        except Exception as e:
            logger.error(f"Failed to increment attempt count in Redis: {e}")
        
        return count
    
    def close_window(self, job_id: str, success: bool) -> Optional[RetryWindow]:
        """
        Close a retry window.
        
        Args:
            job_id: Job identifier
            success: Whether job succeeded
            
        Returns:
            Closed RetryWindow or None if not found
        """
        if job_id not in self.active_windows:
            logger.warning(f"No active retry window for job {job_id}")
            return None
        
        window = self.active_windows[job_id]
        window.close(success)
        
        # Update Redis
        try:
            key = self._window_key(job_id)
            self.redis.hset(key, mapping={
                "end_time": str(window.end_time),
                "success": str(success),
                "status": "closed",
                "duration": str(window.duration())
            })
        except Exception as e:
            logger.error(f"Failed to close retry window in Redis: {e}")
        
        logger.info(
            f"Closed retry window for job {job_id}: "
            f"{window.attempt_count} attempts, duration={window.duration():.2f}s, success={success}"
        )
        
        # Remove from active windows
        del self.active_windows[job_id]
        
        return window
    
    def get_window(self, job_id: str) -> Optional[RetryWindow]:
        """Get retry window for a job"""
        return self.active_windows.get(job_id)
    
    def get_active_count(self) -> int:
        """Get count of active retry windows"""
        return len(self.active_windows)


class RetryHistogram:
    """
    Tracks distribution of retry attempts.
    
    Buckets: 1, 2, 3, 4-5, 6-10, 11-20, 21+
    """
    
    def __init__(self):
        """Initialize retry histogram"""
        self.buckets: Dict[str, int] = {
            "1": 0,
            "2": 0,
            "3": 0,
            "4-5": 0,
            "6-10": 0,
            "11-20": 0,
            "21+": 0
        }
    
    def add_attempt_count(self, count: int) -> None:
        """Add an attempt count to the histogram"""
        if count == 1:
            self.buckets["1"] += 1
        elif count == 2:
            self.buckets["2"] += 1
        elif count == 3:
            self.buckets["3"] += 1
        elif 4 <= count <= 5:
            self.buckets["4-5"] += 1
        elif 6 <= count <= 10:
            self.buckets["6-10"] += 1
        elif 11 <= count <= 20:
            self.buckets["11-20"] += 1
        else:
            self.buckets["21+"] += 1
    
    def get_distribution(self) -> Dict[str, int]:
        """Get current distribution"""
        return self.buckets.copy()
    
    def get_total(self) -> int:
        """Get total count"""
        return sum(self.buckets.values())
    
    def get_percentiles(self) -> Dict[str, float]:
        """Get percentile distribution"""
        total = self.get_total()
        if total == 0:
            return {k: 0.0 for k in self.buckets}
        
        return {k: (v / total) * 100 for k, v in self.buckets.items()}


class RetryAnomalyDetector:
    """
    Detects anomalies in retry patterns.
    
    Anomalies:
    - High retry rate (> threshold)
    - Long retry windows (> threshold)
    - Many excessive attempts (> threshold)
    """
    
    def __init__(
        self,
        high_retry_rate_threshold: float = 0.5,  # 50% of jobs retry
        long_window_threshold_seconds: float = 3600,  # 1 hour
        excessive_attempts_threshold: int = 10
    ):
        """
        Initialize anomaly detector.
        
        Args:
            high_retry_rate_threshold: Threshold for high retry rate (0-1)
            long_window_threshold_seconds: Threshold for long retry windows
            excessive_attempts_threshold: Threshold for excessive attempts
        """
        self.high_retry_rate_threshold = high_retry_rate_threshold
        self.long_window_threshold = long_window_threshold_seconds
        self.excessive_attempts_threshold = excessive_attempts_threshold
        
        self.total_jobs = 0
        self.retried_jobs = 0
        self.long_windows = 0
        self.excessive_attempts = 0
    
    def record_window(self, window: RetryWindow) -> List[str]:
        """
        Record a retry window and detect anomalies.
        
        Args:
            window: Closed retry window
            
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        self.total_jobs += 1
        
        if window.attempt_count > 1:
            self.retried_jobs += 1
        
        if window.duration() and window.duration() > self.long_window_threshold:
            self.long_windows += 1
            anomalies.append(
                f"Long retry window: {window.duration():.2f}s "
                f"(threshold: {self.long_window_threshold}s)"
            )
        
        if window.attempt_count > self.excessive_attempts_threshold:
            self.excessive_attempts += 1
            anomalies.append(
                f"Excessive attempts: {window.attempt_count} "
                f"(threshold: {self.excessive_attempts_threshold})"
            )
        
        # Check retry rate
        if self.total_jobs > 10:  # Need at least 10 jobs for meaningful rate
            retry_rate = self.retried_jobs / self.total_jobs
            if retry_rate > self.high_retry_rate_threshold:
                anomalies.append(
                    f"High retry rate: {retry_rate:.2%} "
                    f"(threshold: {self.high_retry_rate_threshold:.2%})"
                )
        
        return anomalies
    
    def get_stats(self) -> Dict[str, Any]:
        """Get anomaly detector statistics"""
        retry_rate = self.retried_jobs / self.total_jobs if self.total_jobs > 0 else 0
        
        return {
            "total_jobs": self.total_jobs,
            "retried_jobs": self.retried_jobs,
            "retry_rate": retry_rate,
            "long_windows": self.long_windows,
            "excessive_attempts": self.excessive_attempts,
            "thresholds": {
                "high_retry_rate": self.high_retry_rate_threshold,
                "long_window_seconds": self.long_window_threshold,
                "excessive_attempts": self.excessive_attempts_threshold
            }
        }


class RetrySpikeDetector:
    """
    Detects sudden spikes in retry activity.
    
    Uses sliding window to track retry rate over time.
    """
    
    def __init__(
        self,
        window_size_seconds: int = 300,  # 5 minutes
        spike_threshold_multiplier: float = 3.0  # 3x baseline
    ):
        """
        Initialize spike detector.
        
        Args:
            window_size_seconds: Size of sliding window
            spike_threshold_multiplier: Multiplier for spike detection
        """
        self.window_size = window_size_seconds
        self.spike_threshold = spike_threshold_multiplier
        
        # Sliding window of timestamps
        self.events: deque = deque()
        
        # Baseline tracking (events per window)
        self.baseline_samples: deque = deque(maxlen=12)  # Last 12 windows
        self.baseline_rate: Optional[float] = None
    
    def record_retry(self) -> Optional[str]:
        """
        Record a retry event and check for spikes.
        
        Returns:
            Alert message if spike detected, None otherwise
        """
        current_time = time.time()
        
        # Add new event
        self.events.append(current_time)
        
        # Remove events outside window
        cutoff_time = current_time - self.window_size
        while self.events and self.events[0] < cutoff_time:
            self.events.popleft()
        
        # Current rate (events per window)
        current_rate = len(self.events)
        
        # Update baseline
        if len(self.events) > 0:
            self.baseline_samples.append(current_rate)
            if len(self.baseline_samples) >= 3:  # Need at least 3 samples
                self.baseline_rate = sum(self.baseline_samples) / len(self.baseline_samples)
        
        # Check for spike
        if self.baseline_rate and current_rate > self.baseline_rate * self.spike_threshold:
            return (
                f"Retry spike detected: {current_rate} retries in {self.window_size}s "
                f"(baseline: {self.baseline_rate:.1f}, threshold: {self.baseline_rate * self.spike_threshold:.1f})"
            )
        
        return None
    
    def get_current_rate(self) -> int:
        """Get current retry rate (events per window)"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size
        
        # Clean old events
        while self.events and self.events[0] < cutoff_time:
            self.events.popleft()
        
        return len(self.events)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get spike detector statistics"""
        return {
            "current_rate": self.get_current_rate(),
            "baseline_rate": self.baseline_rate,
            "window_size_seconds": self.window_size,
            "spike_threshold_multiplier": self.spike_threshold,
            "spike_threshold_rate": (
                self.baseline_rate * self.spike_threshold 
                if self.baseline_rate else None
            )
        }


def emit_anomaly_alert(anomaly_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> None:
    """
    Emit an anomaly alert event.
    
    Args:
        anomaly_type: Type of anomaly
        message: Alert message
        details: Additional details
    """
    logger.warning(f"ANOMALY ALERT [{anomaly_type}]: {message}")
    
    if details:
        logger.warning(f"Anomaly details: {details}")
    
    # TODO: Integrate with monitoring system (PagerDuty, Slack, etc.)
