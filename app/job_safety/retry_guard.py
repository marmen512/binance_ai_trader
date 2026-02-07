"""
Retry guard module for idempotency checks.

Prevents duplicate job execution by tracking completed jobs.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from redis import Redis
from rq.job import Job

logger = logging.getLogger(__name__)


class IdempotencyGuard:
    """
    Guard to ensure jobs are idempotent and prevent duplicate execution.
    """
    
    def __init__(self, redis_conn: Redis, ttl_hours: int = 72):
        """
        Initialize idempotency guard.
        
        Args:
            redis_conn: Redis connection
            ttl_hours: TTL for idempotency keys in hours (default: 72)
        """
        self.redis = redis_conn
        self.ttl_seconds = ttl_hours * 3600
        self.key_prefix = "job:idempotency:"
    
    def mark_started(self, idempotency_key: str, job_id: str) -> bool:
        """
        Mark a job as started using an idempotency key.
        
        Args:
            idempotency_key: Unique idempotency key for the operation
            job_id: RQ job ID
            
        Returns:
            True if marked successfully (first time), False if already exists
        """
        key = f"{self.key_prefix}{idempotency_key}"
        
        # Use SET NX (set if not exists) for atomic operation
        was_set = self.redis.set(
            key,
            job_id,
            ex=self.ttl_seconds,
            nx=True  # Only set if doesn't exist
        )
        
        if not was_set:
            existing_job_id = self.redis.get(key)
            logger.warning(
                f"Idempotency key {idempotency_key} already exists "
                f"(job_id: {existing_job_id}). Skipping duplicate."
            )
            return False
        
        logger.info(f"Marked job {job_id} as started with key {idempotency_key}")
        return True
    
    def mark_completed(self, idempotency_key: str, result: Any = None):
        """
        Mark a job as completed.
        
        Args:
            idempotency_key: Unique idempotency key for the operation
            result: Optional result to store
        """
        key = f"{self.key_prefix}{idempotency_key}"
        completion_key = f"{key}:completed"
        
        # Mark as completed with extended TTL
        self.redis.set(
            completion_key,
            "true",
            ex=self.ttl_seconds * 2  # Keep completion status longer
        )
        
        if result is not None:
            result_key = f"{key}:result"
            self.redis.set(result_key, str(result), ex=self.ttl_seconds)
        
        logger.info(f"Marked idempotency key {idempotency_key} as completed")
    
    def is_completed(self, idempotency_key: str) -> bool:
        """
        Check if a job with this idempotency key has already completed.
        
        Args:
            idempotency_key: Unique idempotency key for the operation
            
        Returns:
            True if already completed, False otherwise
        """
        key = f"{self.key_prefix}{idempotency_key}"
        completion_key = f"{key}:completed"
        
        return self.redis.exists(completion_key) > 0
    
    def get_result(self, idempotency_key: str) -> Optional[str]:
        """
        Get the result of a completed job.
        
        Args:
            idempotency_key: Unique idempotency key for the operation
            
        Returns:
            Result if available, None otherwise
        """
        key = f"{self.key_prefix}{idempotency_key}"
        result_key = f"{key}:result"
        
        result = self.redis.get(result_key)
        return result.decode() if result else None


class RetryGuard:
    """
    Guard to manage safe job retries with idempotency checks.
    """
    
    def __init__(self, redis_conn: Redis):
        """
        Initialize retry guard.
        
        Args:
            redis_conn: Redis connection
        """
        self.redis = redis_conn
        self.idempotency_guard = IdempotencyGuard(redis_conn)
    
    def should_execute(self, job: Job, idempotency_key: Optional[str] = None) -> bool:
        """
        Check if a job should execute or skip due to idempotency.
        
        Args:
            job: RQ Job instance
            idempotency_key: Optional idempotency key
            
        Returns:
            True if should execute, False if should skip
        """
        # Check if idempotency key provided
        if not idempotency_key:
            # No idempotency key, allow execution
            logger.debug(f"Job {job.id} has no idempotency key, allowing execution")
            return True
        
        # Check if already completed
        if self.idempotency_guard.is_completed(idempotency_key):
            logger.info(
                f"Job {job.id} with idempotency key {idempotency_key} "
                f"already completed. Skipping."
            )
            
            # Update job meta to indicate skip
            job.meta['skipped'] = True
            job.meta['skip_reason'] = 'already_completed'
            job.meta['idempotency_key'] = idempotency_key
            job.save_meta()
            
            return False
        
        # Mark as started
        was_marked = self.idempotency_guard.mark_started(idempotency_key, job.id)
        
        if not was_marked:
            # Another job with same key is running
            logger.info(
                f"Job {job.id} with idempotency key {idempotency_key} "
                f"is already running. Skipping."
            )
            
            job.meta['skipped'] = True
            job.meta['skip_reason'] = 'already_running'
            job.meta['idempotency_key'] = idempotency_key
            job.save_meta()
            
            return False
        
        # Update job meta
        job.meta['idempotency_key'] = idempotency_key
        job.save_meta()
        
        return True
    
    def mark_success(self, job: Job, result: Any = None):
        """
        Mark job as successfully completed.
        
        Args:
            job: RQ Job instance
            result: Optional result to store
        """
        idempotency_key = job.meta.get('idempotency_key')
        
        if idempotency_key:
            self.idempotency_guard.mark_completed(idempotency_key, result)
            logger.info(f"Job {job.id} marked as successfully completed")
    
    def get_idempotency_key(self, func_name: str, *args, **kwargs) -> str:
        """
        Generate an idempotency key from function name and arguments.
        
        Args:
            func_name: Name of the function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Idempotency key string
        """
        # Create a simple hash-based key
        import hashlib
        import json
        
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        
        return f"{func_name}:{key_hash}"
