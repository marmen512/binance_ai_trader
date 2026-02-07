# Chaos Testing Scripts

Chaos testing scripts for validating production safety features under failure conditions.

## Overview

These scripts simulate various failure scenarios to validate:
- Idempotency guarantees
- Circuit breaker behavior
- Retry spike detection
- Error recovery mechanisms
- Alert hook functionality

## Prerequisites

- Redis running locally or accessible via REDIS_URL
- Python dependencies installed (redis, etc.)
- Working binance_ai_trader environment

## Scripts

### 1. kill_redis_test.py

Simulates Redis crash scenarios during critical operations.

**Tests:**
- Operation execution before Redis crash
- Retry attempts during Redis downtime
- Recovery and idempotency verification after reconnection
- Intermittent connection failures

**Usage:**
```bash
python scripts/chaos/kill_redis_test.py
```

**Expected behavior:**
- Operations fail gracefully when Redis is down
- Idempotency is preserved after Redis recovery
- No duplicate side effects occur

### 2. retry_race_test.py

Simulates worker race conditions with concurrent retries.

**Tests:**
- Concurrent execution of same operation by multiple workers
- Staggered retry attempts
- Burst retry patterns
- Lock contention handling

**Usage:**
```bash
python scripts/chaos/retry_race_test.py
```

**Expected behavior:**
- Exactly one execution per operation (idempotency)
- No duplicate side effects
- Consistent result caching

### 3. worker_storm_test.py

Simulates worker storm scenarios with high failure rates.

**Tests:**
- Normal load baseline
- Failure storm (high failure rate)
- Retry spike detection
- Anomalous retry patterns
- Cascading failure scenarios

**Usage:**
```bash
python scripts/chaos/worker_storm_test.py
```

**Expected behavior:**
- Circuit breaker activates under high failure rate
- Spike detector identifies unusual retry patterns
- Anomaly detector flags problematic patterns
- Alert hooks trigger appropriately

## Running All Tests

To run all chaos tests in sequence:

```bash
cd /home/runner/work/binance_ai_trader/binance_ai_trader

# Run each test
python scripts/chaos/kill_redis_test.py
python scripts/chaos/retry_race_test.py
python scripts/chaos/worker_storm_test.py
```

## Interpreting Results

### Success Indicators

- ✓ marks indicate expected behavior
- Exactly one execution per operation
- Circuit breaker activates when threshold exceeded
- Spike alerts trigger during unusual patterns
- No duplicate side effects

### Failure Indicators

- ✗ marks indicate unexpected behavior
- Multiple executions of same operation
- Circuit breaker fails to activate
- Missing spike/anomaly alerts
- Duplicate side effects

## Configuration

Tests use settings from `app/core/config.py`:
- `REDIS_URL`: Redis connection URL (default: redis://localhost:6379/0)

Adjust test parameters in each script:
- Number of workers
- Failure rates
- Duration
- Thresholds

## Safety Notes

- Tests are designed to be non-destructive
- Uses separate Redis keys for testing
- Cleans up test data between runs
- Safe to run in development environments
- **DO NOT run in production**

## Troubleshooting

### Redis Connection Errors

```
Failed to connect to Redis: Connection refused
```
**Solution:** Ensure Redis is running: `redis-server`

### Import Errors

```
ModuleNotFoundError: No module named 'app'
```
**Solution:** Run from repository root or ensure PYTHONPATH is set

### Permission Errors

```
Permission denied: scripts/chaos/kill_redis_test.py
```
**Solution:** Make scripts executable: `chmod +x scripts/chaos/*.py`
