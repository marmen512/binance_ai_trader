"""
Execution hardening verification tests.

Tests to verify existing execution safeguards are in place and functioning,
without modifying the execution logic itself.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestExecutionHardeningPresent:
    """
    Verify execution hardening features exist.
    
    These tests do NOT modify execution - they verify safeguards are present.
    """
    
    def test_execution_safety_module_exists(self):
        """Test that execution_safety module exists."""
        from execution_safety import pre_trade_checks, post_trade_checks
        
        assert pre_trade_checks is not None
        assert post_trade_checks is not None
    
    def test_pre_trade_checks_callable(self):
        """Test that pre-trade checks are callable."""
        from execution_safety.pre_trade_checks import run_pre_trade_checks
        
        assert callable(run_pre_trade_checks)
    
    def test_post_trade_checks_callable(self):
        """Test that post-trade checks are callable."""
        from execution_safety.post_trade_checks import run_post_trade_checks
        
        assert callable(run_post_trade_checks)
    
    def test_execution_guards_exist(self):
        """Test that execution guards module exists."""
        from execution_safety import execution_guards
        
        assert execution_guards is not None
    
    def test_duplicate_order_guard_exists(self):
        """Test that duplicate order guard exists."""
        from execution_safety.execution_guards import DuplicateOrderGuard
        
        guard = DuplicateOrderGuard()
        assert guard is not None
        assert hasattr(guard, 'check_order')
    
    def test_position_state_checker_exists(self):
        """Test that position state checker exists."""
        from execution_safety.execution_guards import PositionStateChecker
        
        checker = PositionStateChecker()
        assert checker is not None
        assert hasattr(checker, 'check_position_state')
    
    def test_exposure_limiter_exists(self):
        """Test that exposure limiter exists."""
        from execution_safety.execution_guards import ExposureLimiter
        
        limiter = ExposureLimiter()
        assert limiter is not None
        assert hasattr(limiter, 'check_exposure')
    
    def test_idempotent_retry_manager_exists(self):
        """Test that idempotent retry manager exists."""
        from execution_safety.execution_guards import IdempotentRetryManager
        
        manager = IdempotentRetryManager()
        assert manager is not None
        assert hasattr(manager, 'can_retry')
        assert hasattr(manager, 'record_attempt')


class TestExecutionHardeningFunctionality:
    """
    Test that execution hardening features function correctly.
    """
    
    def test_duplicate_order_guard_functionality(self):
        """Test duplicate order guard prevents duplicates."""
        from execution_safety.execution_guards import DuplicateOrderGuard
        
        guard = DuplicateOrderGuard(window_seconds=60)
        
        order = {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 1.0,
            "price": 50000.0
        }
        
        # First check should pass
        result1 = guard.check_order(order)
        assert result1.ok is True
        
        # Duplicate check should fail
        result2 = guard.check_order(order)
        assert result2.ok is False
        assert "DUPLICATE" in result2.reason
    
    def test_exposure_limiter_functionality(self):
        """Test exposure limiter enforces limits."""
        from execution_safety.execution_guards import ExposureLimiter
        
        limiter = ExposureLimiter(
            max_exposure_per_symbol=1000.0,
            max_total_exposure=5000.0
        )
        
        # Set current exposure
        limiter.update_exposure("BTCUSDT", 900.0)
        
        # Order within limit should pass
        result1 = limiter.check_exposure("BTCUSDT", 50.0)
        assert result1.ok is True
        
        # Order exceeding limit should fail
        result2 = limiter.check_exposure("BTCUSDT", 200.0)
        assert result2.ok is False
        assert "EXPOSURE" in result2.reason
    
    def test_idempotent_retry_with_backoff(self):
        """Test idempotent retry manager handles retries correctly."""
        from execution_safety.execution_guards import IdempotentRetryManager
        
        manager = IdempotentRetryManager(max_retries=3, base_delay=1.0)
        
        request = {"order_id": "test_123", "symbol": "BTCUSDT"}
        
        # First attempt should be allowed
        can_retry, delay = manager.can_retry(request)
        assert can_retry is True
        assert delay > 0
        
        # Record attempts
        for i in range(3):
            manager.record_attempt(request)
        
        # After max retries, should not be allowed
        can_retry, _ = manager.can_retry(request)
        assert can_retry is False


class TestExecutionNotModified:
    """
    Regression tests to ensure execution logic remains unchanged.
    """
    
    def test_execution_builder_signature_unchanged(self):
        """Test that execution builder signature is unchanged."""
        from execution.builder_5m import build_executions_5m
        import inspect
        
        sig = inspect.signature(build_executions_5m)
        
        # Verify key parameters still exist
        assert 'signals_path' in sig.parameters
        assert 'price_path' in sig.parameters
        assert 'features_path' in sig.parameters
        assert 'output_path' in sig.parameters
        assert 'fee_pct' in sig.parameters
        assert 'slippage_pct' in sig.parameters
    
    def test_execution_contracts_enforced(self):
        """Test that execution contracts are still enforced."""
        from execution.builder_5m import build_executions_5m
        from core.exceptions import BinanceAITraderError
        
        # Test that contract violations are caught
        with pytest.raises(BinanceAITraderError):
            build_executions_5m(
                fee_pct=0.001,  # Wrong value - should be 0.0004
                slippage_pct=0.0002,
                sl_mult=0.5,
                tp_mult=1.0,
                max_holding_candles=6
            )
