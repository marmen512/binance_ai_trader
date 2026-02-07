"""
Chaos and Race Condition Tests

Tests for extreme failure scenarios:
- Redis crash mid-retry
- Double worker retry race
- Network failure during side-effect
- Duplicate retry storm

Verifies:
- No duplicate side effects
- Idempotency holds under race conditions
- Circuit breaker triggers appropriately
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import redis

from app.job_safety.side_effect_guard import (
    SideEffectGuard,
    SideEffectType,
    order_entity_id
)
from app.job_safety.circuit_breaker import CircuitBreaker, CircuitState
from app.job_safety.retry_metrics import RetryMetrics


@pytest.fixture
def redis_client():
    """Redis client for testing (uses test database)"""
    client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=False)
    yield client
    # Cleanup
    client.flushdb()


@pytest.fixture
def side_effect_guard(redis_client):
    """Side effect guard fixture"""
    return SideEffectGuard(redis_client)


@pytest.fixture
def circuit_breaker(redis_client):
    """Circuit breaker fixture"""
    return CircuitBreaker(redis_client, job_type="test_job")


@pytest.fixture
def retry_metrics(redis_client):
    """Retry metrics fixture"""
    return RetryMetrics(redis_client)


class TestChaosScenarios:
    """Test extreme failure scenarios"""
    
    def test_redis_crash_mid_retry(self, redis_client, side_effect_guard):
        """Test handling of Redis crash during retry operation"""
        # Setup: Mark side effect as in progress
        entity_id = order_entity_id("BTCUSDT", "BUY", 0.001)
        effect_type = SideEffectType.ORDER_PLACEMENT
        
        # First execution succeeds
        executed, result = side_effect_guard.execute_once(
            effect_type,
            entity_id,
            lambda: "order_123"
        )
        
        assert executed is True
        assert result == "order_123"
        
        # Simulate Redis crash by closing connection
        with patch.object(redis_client, 'get', side_effect=redis.ConnectionError("Connection lost")):
            # Attempt to check if executed (should handle gracefully)
            try:
                is_exec = side_effect_guard.is_executed(effect_type, entity_id)
                # Should return False to allow retry (fail-safe)
                assert is_exec is False
            except redis.ConnectionError:
                # Also acceptable - will trigger retry
                pass
    
    def test_double_worker_retry_race(self, redis_client, side_effect_guard):
        """Test race condition with two workers retrying same job"""
        entity_id = order_entity_id("ETHUSDT", "SELL", 0.1)
        effect_type = SideEffectType.ORDER_PLACEMENT
        
        results = []
        errors = []
        
        def worker_retry():
            """Simulates a worker retrying a job"""
            try:
                executed, result = side_effect_guard.execute_once(
                    effect_type,
                    entity_id,
                    lambda: f"order_{threading.current_thread().name}"
                )
                results.append((executed, result))
            except Exception as e:
                errors.append(e)
        
        # Start two workers simultaneously
        thread1 = threading.Thread(target=worker_retry, name="worker1")
        thread2 = threading.Thread(target=worker_retry, name="worker2")
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Verify: Only one worker executed, one skipped
        assert len(results) == 2
        executed_count = sum(1 for executed, _ in results if executed)
        skipped_count = sum(1 for executed, _ in results if not executed)
        
        assert executed_count == 1, "Exactly one worker should execute"
        assert skipped_count == 1, "Exactly one worker should skip"
        assert len(errors) == 0, "No errors should occur"
    
    def test_network_failure_during_side_effect(self, redis_client, side_effect_guard):
        """Test network failure during side effect execution"""
        entity_id = order_entity_id("BNBUSDT", "BUY", 1.0)
        effect_type = SideEffectType.ORDER_PLACEMENT
        
        call_count = [0]
        
        def failing_operation():
            """Operation that fails on first call"""
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Network failure")
            return "order_success"
        
        # First attempt fails
        with pytest.raises(ConnectionError):
            side_effect_guard.execute_once(
                effect_type,
                entity_id,
                failing_operation
            )
        
        # Verify mark was removed after failure
        is_exec = side_effect_guard.is_executed(effect_type, entity_id)
        # Note: Current implementation removes mark on failure
        # This allows retry, which is correct behavior
        
        # Second attempt succeeds
        executed, result = side_effect_guard.execute_once(
            effect_type,
            entity_id,
            failing_operation
        )
        
        assert executed is True
        assert result == "order_success"
        assert call_count[0] == 2, "Operation called twice"
    
    def test_duplicate_retry_storm(self, redis_client, side_effect_guard):
        """Test handling of many simultaneous retries"""
        entity_id = order_entity_id("ADAUSDT", "BUY", 100.0)
        effect_type = SideEffectType.ORDER_PLACEMENT
        
        results = []
        
        def storm_worker():
            """Simulates one of many retry attempts"""
            executed, result = side_effect_guard.execute_once(
                effect_type,
                entity_id,
                lambda: "order_storm"
            )
            results.append(executed)
        
        # Launch 10 simultaneous workers (retry storm)
        threads = []
        for i in range(10):
            thread = threading.Thread(target=storm_worker, name=f"storm_worker_{i}")
            threads.append(thread)
            thread.start()
        
        # Wait for all
        for thread in threads:
            thread.join()
        
        # Verify: Only ONE execution, rest skipped
        executed_count = sum(1 for executed in results if executed)
        assert executed_count == 1, "Only one execution should occur in retry storm"
        assert len(results) == 10, "All workers completed"
    
    def test_circuit_breaker_triggers_on_storm(self, redis_client, circuit_breaker):
        """Test circuit breaker opens during failure storm"""
        # Record multiple failures quickly
        for i in range(12):  # Threshold is 10
            circuit_breaker.record_failure()
            time.sleep(0.1)  # Small delay to stay within time window
        
        # Verify circuit opened
        assert circuit_breaker.is_open() is True
        
        # Verify retries blocked
        can_retry, reason = circuit_breaker.can_retry()
        assert can_retry is False
        assert "Manual override required" in reason
    
    def test_circuit_breaker_half_open_on_override(self, redis_client, circuit_breaker):
        """Test circuit breaker moves to half-open on manual override"""
        # Open circuit
        for i in range(12):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.is_open() is True
        
        # Set manual override
        circuit_breaker.set_manual_override(user="admin", reason="Testing recovery")
        
        # Verify state is half-open
        assert circuit_breaker.get_state() == CircuitState.HALF_OPEN
        
        # Verify retries allowed with override
        can_retry, reason = circuit_breaker.can_retry()
        assert can_retry is True
    
    def test_circuit_breaker_closes_on_success(self, redis_client, circuit_breaker):
        """Test circuit breaker closes after successful retry in half-open state"""
        # Open circuit
        for i in range(12):
            circuit_breaker.record_failure()
        
        # Set to half-open
        circuit_breaker.set_half_open()
        assert circuit_breaker.get_state() == CircuitState.HALF_OPEN
        
        # Record success
        circuit_breaker.record_success()
        
        # Verify circuit closed
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        assert circuit_breaker.is_open() is False


class TestRaceConditions:
    """Test specific race condition scenarios"""
    
    def test_concurrent_mark_executed(self, redis_client, side_effect_guard):
        """Test concurrent attempts to mark as executed"""
        entity_id = "test_entity_concurrent"
        effect_type = SideEffectType.POSITION_UPDATE
        
        results = []
        
        def mark_worker():
            """Worker that tries to mark as executed"""
            success = side_effect_guard.mark_executed(effect_type, entity_id, "result_data")
            results.append(success)
        
        # Launch 5 concurrent workers
        threads = [threading.Thread(target=mark_worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify: Only ONE succeeded (SETNX ensures atomicity)
        success_count = sum(1 for success in results if success)
        assert success_count == 1, "Only one mark should succeed"
        assert len(results) == 5, "All workers completed"
    
    def test_check_and_execute_race(self, redis_client, side_effect_guard):
        """Test race between check and execute"""
        entity_id = "test_race_check_execute"
        effect_type = SideEffectType.LEDGER_WRITE
        
        execution_count = [0]
        results = []
        
        def operation():
            """Operation to execute"""
            execution_count[0] += 1
            return f"result_{execution_count[0]}"
        
        def race_worker():
            """Worker racing to execute"""
            executed, result = side_effect_guard.execute_once(
                effect_type,
                entity_id,
                operation
            )
            results.append((executed, result))
        
        # Launch 3 concurrent workers
        threads = [threading.Thread(target=race_worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Verify: Operation executed exactly once
        assert execution_count[0] == 1, "Operation executed exactly once"
        
        # Verify: One executed, two skipped
        executed_count = sum(1 for executed, _ in results if executed)
        assert executed_count == 1, "One worker executed"
    
    def test_ttl_expiry_race(self, redis_client, side_effect_guard):
        """Test race condition around TTL expiry"""
        entity_id = "test_ttl_race"
        effect_type = SideEffectType.PNL_WRITE
        
        # Mark with very short TTL
        side_effect_guard.mark_executed(effect_type, entity_id, "result", ttl=1)
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Verify mark expired
        assert side_effect_guard.is_executed(effect_type, entity_id) is False
        
        # Now multiple workers can execute (should only succeed once per TTL window)
        execution_count = [0]
        
        def operation():
            execution_count[0] += 1
            return "new_result"
        
        # Two workers race after expiry
        results = []
        def race_worker():
            executed, result = side_effect_guard.execute_once(
                effect_type,
                entity_id,
                operation
            )
            results.append(executed)
        
        threads = [threading.Thread(target=race_worker) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # One should execute (the other sees it's already marked again)
        assert execution_count[0] == 1, "One execution after TTL expiry"


class TestMetricsUnderChaos:
    """Test metrics collection under chaotic conditions"""
    
    def test_metrics_during_concurrent_retries(self, redis_client, retry_metrics):
        """Test metrics accuracy during concurrent operations"""
        def metric_worker(job_type: str, attempt: int):
            """Worker recording metrics"""
            retry_metrics.record_retry_attempt(job_type, attempt)
            time.sleep(0.01)
            if attempt <= 2:
                retry_metrics.record_retry_success(job_type)
            else:
                retry_metrics.record_retry_failure(job_type)
        
        # Launch many concurrent workers
        threads = []
        for i in range(20):
            job_type = f"job_type_{i % 3}"
            attempt = (i % 4) + 1
            thread = threading.Thread(target=metric_worker, args=(job_type, attempt))
            threads.append(thread)
            thread.start()
        
        for t in threads:
            t.join()
        
        # Verify metrics recorded
        metrics = retry_metrics.get_all_metrics()
        assert metrics['total_retries'] == 20
        # Note: success/failure counts depend on attempt numbers
    
    def test_metrics_survive_redis_hiccup(self, redis_client, retry_metrics):
        """Test metrics handle Redis connection issues"""
        retry_metrics.record_retry_attempt("test_job", 1)
        
        # Simulate Redis error
        with patch.object(redis_client, 'incr', side_effect=redis.ConnectionError("Lost connection")):
            # Should log error but not crash
            retry_metrics.record_retry_attempt("test_job", 2)
        
        # Metrics should still work after recovery
        retry_metrics.record_retry_success("test_job")
        
        # Should have at least the first record
        metrics = retry_metrics.get_all_metrics()
        assert metrics['total_retries'] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
