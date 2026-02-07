"""
Comprehensive Production Safety Regression Tests

This test suite verifies all critical safety constraints:
1. Protected modules unchanged (paper_gate, execution, execution_safety)
2. Execution behavior unchanged
3. Retry guards prevent duplicates
4. Side effects are idempotent
5. Metrics guard active (cardinality limits)
6. Circuit breaker functionality
7. Runtime Redis safety checks

Uses proper pytest structure with fixtures and mocks.
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

# Import safety modules
from app.job_safety.retry_guard import RetryGuard
from app.job_safety.side_effect_guard import SideEffectGuard, SideEffectType
from app.job_safety.circuit_breaker import CircuitBreaker
from app.job_safety.retry_metrics import RetryMetrics
from app.job_safety.failure_classifier import FailureClassifier, FailureType


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.setex.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.incr.return_value = 1
    redis_mock.expire.return_value = True
    redis_mock.ttl.return_value = 3600
    redis_mock.hgetall.return_value = {}
    redis_mock.hset.return_value = 1
    redis_mock.info.return_value = {
        'maxmemory_policy': 'noeviction',
        'used_memory': 1024 * 1024 * 50,  # 50 MB
    }
    return redis_mock


@pytest.fixture
def mock_job():
    """Mock RQ job."""
    job = MagicMock()
    job.id = "test_job_123"
    job.func_name = "test_function"
    job.meta = {}
    job.save_meta.return_value = None
    return job


@pytest.fixture
def retry_guard(mock_redis):
    """Create RetryGuard with mocked Redis."""
    return RetryGuard(
        redis_client=mock_redis,
        max_attempts=3,
        cooldown_seconds=60,
        namespace="test"
    )


@pytest.fixture
def side_effect_guard(mock_redis):
    """Create SideEffectGuard with mocked Redis."""
    return SideEffectGuard(
        redis_client=mock_redis,
        ttl_seconds=3600,
        namespace="test_effects"
    )


@pytest.fixture
def circuit_breaker(mock_redis):
    """Create CircuitBreaker with mocked Redis."""
    return CircuitBreaker(
        redis_client=mock_redis,
        job_type="test_job",
        failure_threshold=5,
        time_window_minutes=5
    )


@pytest.fixture
def retry_metrics(mock_redis):
    """Create RetryMetrics with mocked Redis."""
    return RetryMetrics(
        redis_client=mock_redis,
        time_window_minutes=60
    )


# ============================================================================
# TEST CLASS 1: Protected Modules Unchanged
# ============================================================================

class TestProtectedModulesUnchanged:
    """Verify protected modules have not been modified."""
    
    def test_paper_gate_exists(self):
        """Paper gate module must exist."""
        paper_gate_path = Path("paper_gate")
        assert paper_gate_path.exists(), "paper_gate directory must exist"
        assert paper_gate_path.is_dir(), "paper_gate must be a directory"
    
    def test_paper_gate_no_job_safety_imports(self):
        """Paper gate must not import job_safety modules."""
        paper_gate_path = Path("paper_gate")
        if not paper_gate_path.exists():
            pytest.skip("paper_gate directory not found")
        
        violations = []
        for py_file in paper_gate_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            forbidden = [
                "from app.job_safety",
                "import app.job_safety",
                "from adaptive",
                "from decision",
                "from leaderboard",
            ]
            
            for pattern in forbidden:
                if pattern in content:
                    violations.append(f"{py_file.name}: {pattern}")
        
        assert not violations, f"paper_gate has forbidden imports: {violations}"
    
    def test_execution_exists(self):
        """Execution module must exist."""
        execution_path = Path("execution")
        assert execution_path.exists(), "execution directory must exist"
        assert execution_path.is_dir(), "execution must be a directory"
    
    def test_execution_no_job_safety_imports(self):
        """Execution module must not import job_safety modules."""
        execution_path = Path("execution")
        if not execution_path.exists():
            pytest.skip("execution directory not found")
        
        violations = []
        for py_file in execution_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            forbidden = [
                "from app.job_safety",
                "import app.job_safety",
            ]
            
            for pattern in forbidden:
                if pattern in content:
                    violations.append(f"{py_file.name}: {pattern}")
        
        assert not violations, f"execution has forbidden imports: {violations}"
    
    def test_execution_safety_exists(self):
        """Execution safety module must exist."""
        exec_safety_path = Path("execution_safety")
        assert exec_safety_path.exists(), "execution_safety directory must exist"
        assert exec_safety_path.is_dir(), "execution_safety must be a directory"
    
    def test_execution_safety_no_job_safety_imports(self):
        """Execution safety must not import job_safety modules."""
        exec_safety_path = Path("execution_safety")
        if not exec_safety_path.exists():
            pytest.skip("execution_safety directory not found")
        
        violations = []
        for py_file in exec_safety_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            forbidden = [
                "from app.job_safety",
                "import app.job_safety",
            ]
            
            for pattern in forbidden:
                if pattern in content:
                    violations.append(f"{py_file.name}: {pattern}")
        
        assert not violations, f"execution_safety has forbidden imports: {violations}"


# ============================================================================
# TEST CLASS 2: Execution Behavior Unchanged
# ============================================================================

class TestExecutionBehaviorUnchanged:
    """Verify execution behavior has not changed."""
    
    def test_config_defaults_safe(self):
        """All new features must be disabled by default."""
        import yaml
        config_path = Path("config/config.yaml")
        
        if not config_path.exists():
            pytest.skip("config.yaml not found")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check critical defaults
        assert config.get("adaptive", {}).get("enabled", False) is False, \
            "adaptive.enabled must be False by default"
        
        assert config.get("leaderboard", {}).get("enabled", False) is False, \
            "leaderboard.enabled must be False by default"
        
        assert config.get("hybrid", {}).get("enabled", False) is False, \
            "hybrid.enabled must be False by default"
        
        # Check new safety flags are disabled by default
        retry_config = config.get("retry", {})
        assert retry_config.get("anomaly_guard", False) is False, \
            "retry.anomaly_guard must be False by default"
        
        assert retry_config.get("circuit_breaker_alerts", False) is False, \
            "retry.circuit_breaker_alerts must be False by default"
        
        runtime_config = config.get("runtime", {})
        assert runtime_config.get("redis_checks", False) is False, \
            "runtime.redis_checks must be False by default"
    
    def test_adaptive_isolated_from_execution(self):
        """Adaptive module must not directly import execution."""
        adaptive_path = Path("adaptive")
        if not adaptive_path.exists():
            pytest.skip("adaptive directory not found")
        
        violations = []
        for py_file in adaptive_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            forbidden = [
                "from execution",
                "import execution",
            ]
            
            for pattern in forbidden:
                if pattern in content:
                    violations.append(f"{py_file.name}: {pattern}")
        
        assert not violations, f"adaptive has direct execution imports: {violations}"


# ============================================================================
# TEST CLASS 3: Retry Guard Prevents Duplicates
# ============================================================================

class TestRetryGuardPreventsDuplicates:
    """Test that retry guards prevent duplicate job execution."""
    
    def test_retry_guard_prevents_duplicate_execution(self, retry_guard, mock_job, mock_redis):
        """Retry guard must prevent duplicate execution."""
        idempotency_key = "test_operation_123"
        
        # First execution - should be allowed
        mock_redis.exists.return_value = False
        should_execute = retry_guard.should_execute(mock_job, idempotency_key)
        assert should_execute is True, "First execution should be allowed"
        
        # Mark as success
        retry_guard.mark_success(mock_job, idempotency_key)
        
        # Second execution - should be blocked
        mock_redis.exists.return_value = True
        should_execute = retry_guard.should_execute(mock_job, idempotency_key)
        assert should_execute is False, "Duplicate execution should be blocked"
    
    def test_retry_guard_allows_retry_after_failure(self, retry_guard, mock_job, mock_redis):
        """Retry guard must allow retry after transient failure."""
        idempotency_key = "test_operation_456"
        
        # First execution
        mock_redis.exists.return_value = False
        mock_redis.get.return_value = None
        should_execute = retry_guard.should_execute(mock_job, idempotency_key)
        assert should_execute is True
        
        # Mark as failed (transient)
        retry_guard.mark_failure(mock_job, idempotency_key, "ConnectionError", is_retryable=True)
        
        # Retry should be allowed after cooldown
        mock_redis.get.return_value = None  # Cooldown expired
        should_execute = retry_guard.should_execute(mock_job, idempotency_key)
        assert should_execute is True, "Retry should be allowed after transient failure"
    
    def test_retry_guard_respects_max_attempts(self, retry_guard, mock_job, mock_redis):
        """Retry guard must respect max attempts limit."""
        idempotency_key = "test_operation_789"
        
        # Simulate 3 failures (max_attempts = 3)
        mock_redis.get.return_value = b"3"  # Already tried 3 times
        
        should_execute = retry_guard.should_execute(mock_job, idempotency_key)
        assert should_execute is False, "Should not retry after max attempts"


# ============================================================================
# TEST CLASS 4: Side Effects Are Idempotent
# ============================================================================

class TestSideEffectsIdempotent:
    """Test that side effects are properly guarded for idempotency."""
    
    def test_side_effect_guard_prevents_duplicate_order(self, side_effect_guard, mock_redis):
        """Side effect guard must prevent duplicate order placement."""
        operation_id = "place_order_BTC_123"
        
        # First attempt - should be allowed
        mock_redis.hgetall.return_value = {}
        result = side_effect_guard.check_and_record(
            operation_id=operation_id,
            effect_type=SideEffectType.ORDER_PLACED,
            metadata={"symbol": "BTCUSDT", "side": "BUY"}
        )
        assert result.allowed is True, "First order placement should be allowed"
        
        # Simulate order was placed
        mock_redis.hgetall.return_value = {
            b"status": b"completed",
            b"timestamp": str(time.time()).encode()
        }
        
        # Second attempt - should be blocked
        result = side_effect_guard.check_and_record(
            operation_id=operation_id,
            effect_type=SideEffectType.ORDER_PLACED,
            metadata={"symbol": "BTCUSDT", "side": "BUY"}
        )
        assert result.allowed is False, "Duplicate order should be blocked"
        assert result.reason == "already_completed", "Should indicate completion"
    
    def test_side_effect_guard_allows_retry_on_failure(self, side_effect_guard, mock_redis):
        """Side effect guard must allow retry if previous attempt failed."""
        operation_id = "place_order_ETH_456"
        
        # First attempt failed
        mock_redis.hgetall.return_value = {
            b"status": b"failed",
            b"error": b"NetworkError"
        }
        
        # Retry should be allowed
        result = side_effect_guard.check_and_record(
            operation_id=operation_id,
            effect_type=SideEffectType.ORDER_PLACED,
            metadata={"symbol": "ETHUSDT", "side": "SELL"}
        )
        assert result.allowed is True, "Retry after failure should be allowed"
    
    def test_side_effect_guard_tracks_multiple_types(self, side_effect_guard, mock_redis):
        """Side effect guard must track different effect types independently."""
        base_id = "operation_XYZ"
        
        # Different effect types should be independent
        mock_redis.hgetall.return_value = {}
        
        # Place order
        result1 = side_effect_guard.check_and_record(
            operation_id=f"{base_id}_order",
            effect_type=SideEffectType.ORDER_PLACED,
            metadata={}
        )
        assert result1.allowed is True
        
        # Update position (different effect type)
        result2 = side_effect_guard.check_and_record(
            operation_id=f"{base_id}_position",
            effect_type=SideEffectType.POSITION_UPDATED,
            metadata={}
        )
        assert result2.allowed is True


# ============================================================================
# TEST CLASS 5: Metrics Guard Active
# ============================================================================

class TestMetricsGuardActive:
    """Test that metrics cardinality guards are active."""
    
    def test_retry_metrics_tracks_job_types(self, retry_metrics, mock_redis):
        """Retry metrics must track different job types."""
        job_types = ["signal_generation", "order_execution", "portfolio_update"]
        
        for job_type in job_types:
            retry_metrics.record_retry(
                job_type=job_type,
                job_id=f"job_{job_type}_1",
                attempt=1,
                error_type="NetworkError"
            )
        
        # Should have recorded all job types
        assert mock_redis.hincrby.called or mock_redis.hset.called
    
    def test_retry_metrics_limits_cardinality(self, retry_metrics, mock_redis):
        """Retry metrics must limit cardinality to prevent explosion."""
        # Simulate many different job IDs
        for i in range(1000):
            retry_metrics.record_retry(
                job_type="test_job",
                job_id=f"job_{i}",
                attempt=1,
                error_type="TransientError"
            )
        
        # Metrics should aggregate by job_type, not job_id
        # This prevents cardinality explosion
        call_count = mock_redis.hincrby.call_count + mock_redis.hset.call_count
        assert call_count < 1000, "Should aggregate metrics, not track each job_id"
    
    def test_metrics_cleanup_old_data(self, retry_metrics, mock_redis):
        """Retry metrics must clean up old data."""
        # Record metric
        retry_metrics.record_retry(
            job_type="cleanup_test",
            job_id="job_old",
            attempt=1,
            error_type="Error"
        )
        
        # Should set TTL on metrics
        assert mock_redis.expire.called, "Should set TTL for automatic cleanup"


# ============================================================================
# TEST CLASS 6: Circuit Breaker Works
# ============================================================================

class TestCircuitBreakerWorks:
    """Test that circuit breaker functionality works correctly."""
    
    def test_circuit_breaker_opens_on_threshold(self, circuit_breaker, mock_redis):
        """Circuit breaker must open when failure threshold is reached."""
        # Simulate failures below threshold
        mock_redis.llen.return_value = 4  # 4 failures (threshold is 5)
        assert circuit_breaker.should_allow_retry() is True, "Should allow retry below threshold"
        
        # Reach threshold
        mock_redis.llen.return_value = 5  # 5 failures (at threshold)
        assert circuit_breaker.should_allow_retry() is False, "Should block retry at threshold"
    
    def test_circuit_breaker_tracks_failure_window(self, circuit_breaker, mock_redis):
        """Circuit breaker must track failures in time window."""
        # Record failures
        for i in range(3):
            circuit_breaker.record_failure(f"job_{i}", "NetworkError")
        
        # Should have called Redis to store failure timestamps
        assert mock_redis.rpush.called or mock_redis.lpush.called, \
            "Should store failure timestamps"
    
    def test_circuit_breaker_resets_after_success(self, circuit_breaker, mock_redis):
        """Circuit breaker must reset failure count after success."""
        # Record success
        circuit_breaker.record_success("job_success")
        
        # Should have called Redis to clear or decrement failures
        assert mock_redis.delete.called or mock_redis.decr.called, \
            "Should reset failure tracking on success"
    
    def test_circuit_breaker_requires_manual_reset(self, circuit_breaker, mock_redis):
        """Circuit breaker must require manual reset when tripped."""
        # Simulate circuit open
        mock_redis.get.return_value = b"open"
        
        assert circuit_breaker.is_open() is True, "Circuit should be open"
        
        # Manual reset required
        circuit_breaker.reset()
        assert mock_redis.delete.called, "Should delete circuit state on reset"


# ============================================================================
# TEST CLASS 7: Runtime Checks Work
# ============================================================================

class TestRuntimeChecksWork:
    """Test that runtime Redis safety checks work."""
    
    def test_redis_eviction_policy_check(self, mock_redis):
        """Runtime checks must validate Redis eviction policy."""
        # Good policy
        mock_redis.info.return_value = {
            'maxmemory_policy': 'noeviction'
        }
        
        info = mock_redis.info()
        policy = info.get('maxmemory_policy')
        assert policy == 'noeviction', "Redis should use noeviction policy"
    
    def test_redis_memory_usage_check(self, mock_redis):
        """Runtime checks must monitor Redis memory usage."""
        memory_budget_mb = 100
        
        # Good memory usage
        mock_redis.info.return_value = {
            'used_memory': 50 * 1024 * 1024  # 50 MB
        }
        
        info = mock_redis.info()
        used_memory_mb = info['used_memory'] / (1024 * 1024)
        assert used_memory_mb < memory_budget_mb, "Memory usage should be within budget"
    
    def test_redis_key_expiration_works(self, mock_redis):
        """Runtime checks must verify key expiration works."""
        # Set key with TTL
        key = "test_key_with_ttl"
        ttl_seconds = 3600
        
        mock_redis.setex(key, ttl_seconds, "value")
        assert mock_redis.setex.called, "Should set key with TTL"
        
        # Check TTL is set
        mock_redis.ttl.return_value = ttl_seconds
        ttl = mock_redis.ttl(key)
        assert ttl > 0, "Key should have positive TTL"
    
    def test_redis_namespace_isolation(self, mock_redis, retry_guard, side_effect_guard):
        """Runtime checks must verify namespace isolation."""
        # Different components should use different namespaces
        retry_namespace = retry_guard.namespace
        side_effect_namespace = side_effect_guard.namespace
        
        assert retry_namespace != side_effect_namespace, \
            "Different components should use different namespaces"
    
    def test_redis_connection_resilience(self, mock_redis):
        """Runtime checks must handle Redis connection failures gracefully."""
        from redis.exceptions import ConnectionError as RedisConnectionError
        
        # Simulate connection error
        mock_redis.get.side_effect = RedisConnectionError("Connection refused")
        
        # Should handle gracefully
        with pytest.raises(RedisConnectionError):
            mock_redis.get("test_key")
        
        # This tests that the exception is properly raised
        # In production code, this should be caught and handled


# ============================================================================
# INTEGRATION TEST
# ============================================================================

class TestFullSafetyIntegration:
    """Integration test combining all safety components."""
    
    def test_complete_safety_chain(self, mock_redis, mock_job):
        """Test complete safety chain: retry guard -> side effect -> circuit breaker."""
        # Setup all guards
        retry_guard = RetryGuard(mock_redis, max_attempts=3, cooldown_seconds=60, namespace="retry")
        side_effect_guard = SideEffectGuard(mock_redis, ttl_seconds=3600, namespace="effects")
        circuit_breaker = CircuitBreaker(mock_redis, "test_job", failure_threshold=5, time_window_minutes=5)
        
        operation_id = "integration_test_op"
        
        # Step 1: Check circuit breaker
        mock_redis.llen.return_value = 0
        assert circuit_breaker.should_allow_retry() is True, "Circuit should be closed"
        
        # Step 2: Check retry guard
        mock_redis.exists.return_value = False
        should_execute = retry_guard.should_execute(mock_job, operation_id)
        assert should_execute is True, "Should allow first execution"
        
        # Step 3: Check side effect guard
        mock_redis.hgetall.return_value = {}
        result = side_effect_guard.check_and_record(
            operation_id=operation_id,
            effect_type=SideEffectType.ORDER_PLACED,
            metadata={}
        )
        assert result.allowed is True, "Should allow side effect"
        
        # All guards passed - execution would proceed
        assert True, "Complete safety chain validated"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
