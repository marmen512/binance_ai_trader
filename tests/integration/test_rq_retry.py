"""Integration tests for RQ job retry with real Redis instance.

These tests verify the complete retry flow including:
- Real failed jobs in Redis
- Retry once, twice, and max limits
- Idempotent skip functionality
- Non-retryable job blocking
"""

import pytest
import time
from redis import Redis
from rq import Queue
from rq.job import Job
from rq.registry import FailedJobRegistry
from app.job_safety import (
    RetryGuard,
    RetryPolicy,
    RetryLimits,
    FailureClassifier,
    FailureType,
    RetryAuditLogger
)


# Test helper functions that will fail or succeed
def job_that_succeeds():
    """Job that succeeds."""
    return "success"


def job_that_fails_network():
    """Job that fails with network error (retryable)."""
    raise ConnectionError("Network connection failed")


def job_that_fails_validation():
    """Job that fails with validation error (non-retryable)."""
    raise ValueError("Invalid data format")


def job_that_checks_idempotency(guard: RetryGuard, job: Job, key: str):
    """Job that checks idempotency."""
    if not guard.should_execute(job, key):
        return {"skipped": True, "reason": "idempotent"}
    
    # Simulate work
    time.sleep(0.1)
    
    # Mark success
    guard.mark_success(job, "completed")
    return {"completed": True}


@pytest.fixture
def redis_conn():
    """Fixture for Redis connection."""
    # Use test Redis database (db=15)
    redis = Redis(host='localhost', port=6379, db=15, decode_responses=False)
    
    # Clear test database
    redis.flushdb()
    
    yield redis
    
    # Cleanup
    redis.flushdb()
    redis.close()


@pytest.fixture
def queue(redis_conn):
    """Fixture for RQ Queue."""
    q = Queue('test_queue', connection=redis_conn)
    return q


@pytest.fixture
def retry_guard(redis_conn):
    """Fixture for RetryGuard."""
    return RetryGuard(redis_conn)


@pytest.fixture
def retry_policy(redis_conn):
    """Fixture for RetryPolicy with test limits."""
    limits = RetryLimits(
        max_retries=3,
        cooldown_seconds=1,  # Short cooldown for tests
        exponential_backoff=False  # Disable for faster tests
    )
    return RetryPolicy(redis_conn, limits)


@pytest.fixture
def failure_classifier():
    """Fixture for FailureClassifier."""
    return FailureClassifier()


@pytest.fixture
def audit_logger(tmp_path):
    """Fixture for RetryAuditLogger."""
    log_dir = str(tmp_path / "audit_logs")
    return RetryAuditLogger(log_dir)


class TestRQRetryIntegration:
    """Integration tests for RQ retry system."""
    
    def test_job_fails_and_appears_in_failed_registry(self, queue, redis_conn):
        """Test that a failed job appears in the failed registry."""
        # Enqueue a job that will fail
        job = queue.enqueue(job_that_fails_network)
        
        # Process the job (it will fail)
        try:
            job.perform()
        except:
            pass
        
        # Job should be failed
        job.refresh()
        assert job.is_failed
        
        # Check failed registry
        failed_registry = FailedJobRegistry(queue=queue)
        assert job.id in failed_registry.get_job_ids()
    
    def test_retry_failed_job_once(self, queue, redis_conn, retry_policy):
        """Test retrying a failed job once."""
        # Enqueue and fail a job
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        job.refresh()
        assert job.is_failed
        
        # Record retry attempt
        retry_policy.record_retry_attempt(job)
        
        # Check retry status
        status = retry_policy.get_retry_status(job)
        assert status['attempts'] == 1
        assert status['max_retries'] == 3
        assert status['can_retry'] == True
        
        # Requeue the job
        failed_registry = FailedJobRegistry(queue=queue)
        failed_registry.requeue(job.id)
        
        # Job should be back in queue
        assert job.id not in failed_registry.get_job_ids()
    
    def test_retry_failed_job_twice(self, queue, redis_conn, retry_policy):
        """Test retrying a failed job twice."""
        # Enqueue and fail a job
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        # First retry
        retry_policy.record_retry_attempt(job)
        status = retry_policy.get_retry_status(job)
        assert status['attempts'] == 1
        
        # Second retry
        retry_policy.record_retry_attempt(job)
        status = retry_policy.get_retry_status(job)
        assert status['attempts'] == 2
        assert status['can_retry'] == True
    
    def test_retry_blocked_after_max_attempts(self, queue, redis_conn, retry_policy):
        """Test that retry is blocked after max attempts."""
        # Enqueue and fail a job
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        # Exceed max retries
        for _ in range(3):
            retry_policy.record_retry_attempt(job)
        
        # Should not be able to retry
        can_retry, reason = retry_policy.can_retry(job)
        assert can_retry == False
        assert "Maximum retry attempts" in reason
    
    def test_idempotent_skip_works(self, queue, redis_conn, retry_guard):
        """Test that idempotency guard prevents duplicate execution."""
        idempotency_key = "test_job_123"
        
        # First job with idempotency key
        job1 = queue.enqueue(
            job_that_checks_idempotency,
            retry_guard,
            None,  # Will be set to job later
            idempotency_key
        )
        
        # Mark as started
        was_marked = retry_guard.idempotency_guard.mark_started(idempotency_key, job1.id)
        assert was_marked == True
        
        # Try to start again with same key
        was_marked_again = retry_guard.idempotency_guard.mark_started(idempotency_key, "job2")
        assert was_marked_again == False
        
        # Mark as completed
        retry_guard.idempotency_guard.mark_completed(idempotency_key, "result")
        
        # Check if completed
        is_completed = retry_guard.idempotency_guard.is_completed(idempotency_key)
        assert is_completed == True
    
    def test_non_retryable_job_blocked(self, queue, redis_conn, failure_classifier):
        """Test that non-retryable jobs are properly classified and blocked."""
        # Enqueue and fail with validation error
        job = queue.enqueue(job_that_fails_validation)
        try:
            job.perform()
        except:
            pass
        
        job.refresh()
        assert job.is_failed
        
        # Classify the failure
        exc_info = job.exc_info or ""
        should_retry, failure_type = failure_classifier.should_retry_failure(exc_info)
        
        # Should not be retryable
        assert should_retry == False
        assert failure_type in [FailureType.LOGIC_ERROR, FailureType.VALIDATION_ERROR]
    
    def test_retryable_job_allowed(self, queue, redis_conn, failure_classifier):
        """Test that retryable jobs are properly classified."""
        # Enqueue and fail with network error
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        job.refresh()
        assert job.is_failed
        
        # Classify the failure
        exc_info = job.exc_info or ""
        should_retry, failure_type = failure_classifier.should_retry_failure(exc_info)
        
        # Should be retryable
        assert should_retry == True
        assert failure_type == FailureType.NETWORK_ERROR
    
    def test_cooldown_period_enforced(self, queue, redis_conn):
        """Test that cooldown period is enforced between retries."""
        # Create policy with 2-second cooldown
        limits = RetryLimits(
            max_retries=3,
            cooldown_seconds=2,
            exponential_backoff=False
        )
        retry_policy = RetryPolicy(redis_conn, limits)
        
        # Enqueue and fail a job
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        # First retry
        retry_policy.record_retry_attempt(job)
        
        # Immediately check if can retry (should be blocked by cooldown)
        can_retry, reason = retry_policy.can_retry(job)
        assert can_retry == False
        assert "Cooldown period active" in reason
        
        # Wait for cooldown
        time.sleep(2.1)
        
        # Now should be able to retry
        can_retry, reason = retry_policy.can_retry(job)
        assert can_retry == True
    
    def test_audit_logging_records_retry(self, queue, redis_conn, audit_logger):
        """Test that retry attempts are logged to audit trail."""
        # Enqueue and fail a job
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        # Log a retry attempt
        audit_logger.log_retry_attempt(
            job=job,
            retry_reason="test_retry",
            failure_type="network_error",
            dry_run=False,
            success=None
        )
        
        # Flush to ensure write
        audit_logger.flush()
        
        # Get audit history
        history = audit_logger.get_audit_history(job_id=job.id)
        
        assert len(history) > 0
        assert history.iloc[0]['job_id'] == job.id
        assert history.iloc[0]['retry_reason'] == "test_retry"
        assert history.iloc[0]['failure_type'] == "network_error"
    
    def test_dry_run_does_not_execute(self, queue, redis_conn, audit_logger):
        """Test that dry run logs but doesn't execute."""
        # Enqueue and fail a job
        job = queue.enqueue(job_that_fails_network)
        try:
            job.perform()
        except:
            pass
        
        # Log as dry run
        audit_logger.log_dry_run(
            job=job,
            retry_reason="test_dry_run",
            failure_type="network_error"
        )
        
        # Flush
        audit_logger.flush()
        
        # Check audit log
        history = audit_logger.get_audit_history(job_id=job.id)
        assert len(history) > 0
        assert history.iloc[0]['dry_run_flag'] == True
        
        # Job should still be in failed registry
        failed_registry = FailedJobRegistry(queue=queue)
        assert job.id in failed_registry.get_job_ids()
    
    def test_exponential_backoff_calculation(self, redis_conn):
        """Test that exponential backoff increases cooldown properly."""
        limits = RetryLimits(
            max_retries=5,
            cooldown_seconds=10,
            exponential_backoff=True,
            max_cooldown_seconds=1000
        )
        retry_policy = RetryPolicy(redis_conn, limits)
        
        # Test cooldown calculation
        assert retry_policy._calculate_cooldown(0) == 10
        assert retry_policy._calculate_cooldown(1) == 20
        assert retry_policy._calculate_cooldown(2) == 40
        assert retry_policy._calculate_cooldown(3) == 80
        
        # Should cap at max
        assert retry_policy._calculate_cooldown(10) == 1000


class TestFailureClassifier:
    """Tests for failure classifier."""
    
    def test_network_error_classification(self, failure_classifier):
        """Test network error classification."""
        exc_info = "ConnectionError: Failed to connect to host"
        failure_type = failure_classifier.classify_failure(exc_info)
        assert failure_type == FailureType.NETWORK_ERROR
        assert failure_classifier.is_retryable(failure_type) == True
    
    def test_timeout_classification(self, failure_classifier):
        """Test timeout error classification."""
        exc_info = "TimeoutError: Operation timed out after 30s"
        failure_type = failure_classifier.classify_failure(exc_info)
        assert failure_type == FailureType.TIMEOUT
        assert failure_classifier.is_retryable(failure_type) == True
    
    def test_rate_limit_classification(self, failure_classifier):
        """Test rate limit error classification."""
        exc_info = "HTTPError 429: Rate limit exceeded"
        failure_type = failure_classifier.classify_failure(exc_info)
        assert failure_type == FailureType.RATE_LIMIT
        assert failure_classifier.is_retryable(failure_type) == True
    
    def test_validation_error_classification(self, failure_classifier):
        """Test validation error classification."""
        exc_info = "ValidationError: Invalid field format"
        failure_type = failure_classifier.classify_failure(exc_info)
        assert failure_type == FailureType.VALIDATION_ERROR
        assert failure_classifier.is_retryable(failure_type) == False
    
    def test_logic_error_classification(self, failure_classifier):
        """Test logic error classification."""
        exc_info = "ValueError: Cannot convert string to int"
        failure_type = failure_classifier.classify_failure(exc_info)
        assert failure_type == FailureType.LOGIC_ERROR
        assert failure_classifier.is_retryable(failure_type) == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
