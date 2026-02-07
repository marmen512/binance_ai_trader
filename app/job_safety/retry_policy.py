"""
Retry policy module for managing retry limits and cooldowns.

Implements safe retry policies with maximum attempts and cooldown periods.
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from redis import Redis
from rq.job import Job

logger = logging.getLogger(__name__)


@dataclass
class RetryLimits:
    """Retry limits configuration."""
    max_retries: int = 3
    cooldown_seconds: int = 60
    exponential_backoff: bool = True
    max_cooldown_seconds: int = 3600  # 1 hour max


class RetryPolicy:
    """
    Policy for managing job retries with limits and cooldowns.
    """
    
    def __init__(self, redis_conn: Redis, limits: Optional[RetryLimits] = None):
        """
        Initialize retry policy.
        
        Args:
            redis_conn: Redis connection
            limits: Retry limits configuration (uses defaults if None)
        """
        self.redis = redis_conn
        self.limits = limits or RetryLimits()
        self.key_prefix = "job:retry:"
    
    def can_retry(self, job: Job) -> tuple[bool, Optional[str]]:
        """
        Check if a job can be retried.
        
        Args:
            job: RQ Job instance
            
        Returns:
            Tuple of (can_retry: bool, reason: Optional[str])
        """
        # Get retry metadata from job
        attempts = job.meta.get('retry_attempts', 0)
        last_retry_at = job.meta.get('last_retry_at')
        first_failed_at = job.meta.get('first_failed_at')
        
        # Check max retries
        if attempts >= self.limits.max_retries:
            reason = f"Maximum retry attempts ({self.limits.max_retries}) reached"
            logger.warning(f"Job {job.id} cannot retry: {reason}")
            return False, reason
        
        # Check cooldown period
        if last_retry_at:
            last_retry_time = datetime.fromisoformat(last_retry_at)
            cooldown = self._calculate_cooldown(attempts)
            next_retry_time = last_retry_time + timedelta(seconds=cooldown)
            
            if datetime.now() < next_retry_time:
                wait_seconds = (next_retry_time - datetime.now()).total_seconds()
                reason = f"Cooldown period active. Wait {wait_seconds:.0f}s before retry"
                logger.info(f"Job {job.id} cannot retry yet: {reason}")
                return False, reason
        
        logger.info(f"Job {job.id} can be retried (attempt {attempts + 1}/{self.limits.max_retries})")
        return True, None
    
    def _calculate_cooldown(self, attempts: int) -> int:
        """
        Calculate cooldown period based on number of attempts.
        
        Args:
            attempts: Number of retry attempts so far
            
        Returns:
            Cooldown period in seconds
        """
        if not self.limits.exponential_backoff:
            return self.limits.cooldown_seconds
        
        # Exponential backoff: cooldown * (2 ^ attempts)
        cooldown = self.limits.cooldown_seconds * (2 ** attempts)
        
        # Cap at max cooldown
        return min(cooldown, self.limits.max_cooldown_seconds)
    
    def record_retry_attempt(self, job: Job):
        """
        Record a retry attempt in job metadata.
        
        Args:
            job: RQ Job instance
        """
        now = datetime.now().isoformat()
        
        # Initialize or increment attempts
        attempts = job.meta.get('retry_attempts', 0)
        attempts += 1
        
        # Update metadata
        job.meta['retry_attempts'] = attempts
        job.meta['last_retry_at'] = now
        
        if 'first_failed_at' not in job.meta:
            job.meta['first_failed_at'] = now
        
        job.save_meta()
        
        logger.info(
            f"Recorded retry attempt {attempts} for job {job.id} at {now}"
        )
    
    def reset_retry_metadata(self, job: Job):
        """
        Reset retry metadata (e.g., after successful completion).
        
        Args:
            job: RQ Job instance
        """
        job.meta['retry_attempts'] = 0
        job.meta['last_retry_at'] = None
        job.meta['first_failed_at'] = None
        job.save_meta()
        
        logger.info(f"Reset retry metadata for job {job.id}")
    
    def get_retry_status(self, job: Job) -> dict:
        """
        Get current retry status for a job.
        
        Args:
            job: RQ Job instance
            
        Returns:
            Dictionary with retry status information
        """
        attempts = job.meta.get('retry_attempts', 0)
        last_retry_at = job.meta.get('last_retry_at')
        first_failed_at = job.meta.get('first_failed_at')
        
        can_retry, reason = self.can_retry(job)
        
        status = {
            'can_retry': can_retry,
            'reason': reason,
            'attempts': attempts,
            'max_retries': self.limits.max_retries,
            'last_retry_at': last_retry_at,
            'first_failed_at': first_failed_at,
        }
        
        if last_retry_at and can_retry:
            # Calculate next retry time
            last_retry_time = datetime.fromisoformat(last_retry_at)
            cooldown = self._calculate_cooldown(attempts)
            next_retry_time = last_retry_time + timedelta(seconds=cooldown)
            status['next_retry_at'] = next_retry_time.isoformat()
            status['cooldown_seconds'] = cooldown
        
        return status
    
    def extend_retry_limit(self, job: Job, additional_retries: int = 1):
        """
        Extend the retry limit for a specific job.
        
        Args:
            job: RQ Job instance
            additional_retries: Number of additional retries to allow
        """
        current_limit = job.meta.get('custom_max_retries', self.limits.max_retries)
        new_limit = current_limit + additional_retries
        
        job.meta['custom_max_retries'] = new_limit
        job.save_meta()
        
        logger.info(
            f"Extended retry limit for job {job.id} from {current_limit} to {new_limit}"
        )
    
    def get_effective_max_retries(self, job: Job) -> int:
        """
        Get effective max retries for a job (custom or default).
        
        Args:
            job: RQ Job instance
            
        Returns:
            Effective max retries value
        """
        return job.meta.get('custom_max_retries', self.limits.max_retries)
