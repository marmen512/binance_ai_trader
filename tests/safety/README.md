# Safety Test Suite

Comprehensive production safety regression tests for the binance_ai_trader system.

## Overview

This directory contains multiple layers of safety tests to ensure production stability and prevent regressions.

## Test Files

### test_full_production_safety.py (NEW)

**Comprehensive production safety test suite covering all critical constraints.**

#### Test Classes:

1. **TestProtectedModulesUnchanged**
   - Verifies `paper_gate/`, `execution/`, `execution_safety/` are unchanged
   - Checks for forbidden imports from new modules
   - Ensures architectural boundaries are maintained

2. **TestExecutionBehaviorUnchanged**
   - Verifies config defaults are safe
   - Checks all new features disabled by default
   - Ensures adaptive module is isolated from execution

3. **TestRetryGuardPreventsDuplicates**
   - Tests retry guard blocks duplicate execution
   - Verifies retry allowed after transient failures
   - Tests max attempts limit is respected

4. **TestSideEffectsIdempotent**
   - Tests side effect guard prevents duplicate orders
   - Verifies retry allowed after failures
   - Tests different effect types tracked independently

5. **TestMetricsGuardActive**
   - Tests retry metrics track job types
   - Verifies cardinality limits prevent explosion
   - Tests metrics cleanup old data

6. **TestCircuitBreakerWorks**
   - Tests circuit breaker opens at threshold
   - Verifies failure window tracking
   - Tests reset after success
   - Tests manual reset requirement

7. **TestRuntimeChecksWork**
   - Tests Redis eviction policy validation
   - Verifies memory usage monitoring
   - Tests key expiration functionality
   - Tests namespace isolation
   - Tests connection resilience

8. **TestFullSafetyIntegration**
   - Integration test of complete safety chain
   - Tests all components working together

#### Fixtures:

- `mock_redis`: Mocked Redis client with pre-configured responses
- `mock_job`: Mocked RQ job object
- `retry_guard`: RetryGuard instance with mocked Redis
- `side_effect_guard`: SideEffectGuard instance with mocked Redis
- `circuit_breaker`: CircuitBreaker instance with mocked Redis
- `retry_metrics`: RetryMetrics instance with mocked Redis

#### Running Tests:

```bash
# Run all safety tests
pytest tests/safety/test_full_production_safety.py -v

# Run specific test class
pytest tests/safety/test_full_production_safety.py::TestProtectedModulesUnchanged -v

# Run specific test
pytest tests/safety/test_full_production_safety.py::TestRetryGuardPreventsDuplicates::test_retry_guard_prevents_duplicate_execution -v

# Run with coverage
pytest tests/safety/test_full_production_safety.py --cov=app.job_safety --cov-report=html
```

### Other Safety Test Files

#### test_comprehensive_safety.py
- Legacy comprehensive safety tests
- Tests paper pipeline, execution, and model isolation

#### test_production_hardening_safety.py
- Production hardening specific tests
- Tests retry guards, side effects, circuit breakers

#### test_safety_regression.py
- General safety regression tests
- Tests architectural boundaries

#### test_execution_hardening.py
- Execution module hardening tests

#### test_final_verification.py
- Final verification before deployment

## Test Requirements

### Required Packages:
- pytest
- pytest-mock
- redis (for Redis integration tests)
- PyYAML (for config tests)

### Install:
```bash
pip install pytest pytest-mock redis PyYAML
```

## Mock Strategy

Tests use `unittest.mock.MagicMock` for Redis mocking to:
- Avoid requiring running Redis instance
- Provide fast, deterministic test execution
- Allow testing error conditions easily

## Test Patterns

### Checking Module Imports
```python
def test_module_no_forbidden_imports(self):
    module_path = Path("protected_module")
    for py_file in module_path.rglob("*.py"):
        content = py_file.read_text()
        assert "from forbidden" not in content
```

### Testing Idempotency
```python
def test_idempotent_operation(self, guard, mock_redis):
    # First execution allowed
    mock_redis.exists.return_value = False
    assert guard.should_execute() is True
    
    # Mark complete
    guard.mark_success()
    
    # Second execution blocked
    mock_redis.exists.return_value = True
    assert guard.should_execute() is False
```

### Testing Circuit Breaker
```python
def test_circuit_opens_at_threshold(self, circuit_breaker, mock_redis):
    # Below threshold
    mock_redis.llen.return_value = 4
    assert circuit_breaker.should_allow_retry() is True
    
    # At threshold
    mock_redis.llen.return_value = 5
    assert circuit_breaker.should_allow_retry() is False
```

## CI/CD Integration

### GitHub Actions Example:
```yaml
name: Safety Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install pytest pytest-mock redis PyYAML
      - name: Run safety tests
        run: |
          pytest tests/safety/test_full_production_safety.py -v
```

## Adding New Safety Tests

### Steps:
1. Identify the safety constraint to test
2. Create test class with descriptive name
3. Add fixtures for dependencies (use mocks)
4. Write test methods (start with `test_`)
5. Document what each test verifies
6. Run tests to ensure they pass
7. Update this README

### Example Template:
```python
class TestNewSafetyConstraint:
    """Test description of constraint."""
    
    def test_constraint_enforced(self, mock_redis):
        """Test that constraint is enforced."""
        # Arrange
        guard = SafetyGuard(mock_redis)
        
        # Act
        result = guard.check_constraint()
        
        # Assert
        assert result is True
```

## Troubleshooting

### Import Errors
If you get import errors:
```bash
# Add project root to PYTHONPATH
export PYTHONPATH=/path/to/binance_ai_trader:$PYTHONPATH
pytest tests/safety/test_full_production_safety.py
```

### Redis Connection Errors
Tests should use mocked Redis. If you see Redis connection errors:
- Check that fixtures are properly configured
- Verify tests use `mock_redis` fixture
- Don't connect to real Redis in unit tests

### Failing Tests
If tests fail:
1. Read the assertion error carefully
2. Check if the safety constraint was intentionally changed
3. Update tests if constraint legitimately changed
4. Get peer review for safety-related changes

## Coverage Goals

Target coverage for safety modules:
- `app.job_safety/*`: 80%+ coverage
- Protected modules verification: 100%
- Config verification: 100%

## Related Documentation

- `scripts/rollout/safety_verify.py` - Automated verification script
- `config/config.yaml` - Configuration with safety flags
- `PRODUCTION_SAFETY_IMPLEMENTATION.md` - Production safety guide

## Support

For test issues:
1. Check test output for specific failure details
2. Review mock setup in fixtures
3. Verify the actual module behavior matches test expectations
4. Consult main test documentation
