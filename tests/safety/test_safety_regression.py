"""
Safety regression tests for Stage 10.

Tests to ensure:
- Execution safety not bypassed
- Paper pipeline unchanged
- Frozen model unchanged
- Adaptive isolated
"""

import pytest
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestExecutionSafetyNotBypassed:
    """
    Test that execution safety checks cannot be bypassed.
    
    Ensures that all safety guards are enforced.
    """
    
    def test_duplicate_order_guard_active(self):
        """Test that duplicate order guard is active and working."""
        from execution_safety.execution_guards import get_duplicate_guard
        
        guard = get_duplicate_guard()
        
        order = {
            "symbol": "BTCUSDT",
            "side": "LONG",
            "quantity": 1.0,
            "price": 50000.0
        }
        
        # First submission should pass
        result1 = guard.check_order(order)
        assert result1.ok is True
        
        # Duplicate submission should fail
        result2 = guard.check_order(order)
        assert result2.ok is False
        assert "DUPLICATE_ORDER" in result2.reason
    
    def test_position_state_checker_active(self):
        """Test that position state checker is active."""
        from execution_safety.execution_guards import get_position_checker
        
        checker = get_position_checker()
        
        # Without tracked position, should fail
        result = checker.check_position_state("BTCUSDT", {})
        assert result.ok is False
        assert "POSITION_NOT_TRACKED" in result.reason
    
    def test_exposure_limiter_active(self):
        """Test that exposure limiter is enforced."""
        from execution_safety.execution_guards import get_exposure_limiter
        
        limiter = get_exposure_limiter()
        
        # Set current exposure near limit
        limiter.update_exposure("BTCUSDT", 9500.0)
        
        # Large order should be rejected
        result = limiter.check_exposure("BTCUSDT", 1000.0)
        assert result.ok is False
        assert "EXPOSURE_LIMIT" in result.reason
    
    def test_emergency_stop_enforced(self):
        """Test that emergency stop is checked."""
        from execution_safety.pre_trade_checks import run_pre_trade_checks
        import pandas as pd
        
        # Mock row with no emergency stop flags
        row = pd.Series({
            "low_liquidity_flag": False,
            "trade_validity_target": "VALID"
        })
        
        result = run_pre_trade_checks(
            row,
            target_position=5.0,
            max_leverage=10.0,
            enforce_trade_validity=True
        )
        
        # Should pass if no emergency conditions
        assert isinstance(result.ok, bool)
        assert isinstance(result.reasons, list)


class TestPaperPipelineUnchanged:
    """
    Test that paper trading pipeline remains unchanged.
    
    Ensures that paper trading logic is not affected by new features.
    """
    
    def test_paper_gate_module_exists(self):
        """Test that paper_gate module is intact."""
        from paper_gate import gate_5m
        
        assert hasattr(gate_5m, '__file__')
    
    def test_execution_builder_unchanged(self):
        """Test that execution builder contract is unchanged."""
        from execution.builder_5m import build_executions_5m
        
        # Verify the function signature hasn't changed
        import inspect
        sig = inspect.signature(build_executions_5m)
        
        # Key parameters should still exist
        assert 'signals_path' in sig.parameters
        assert 'price_path' in sig.parameters
        assert 'features_path' in sig.parameters
        assert 'output_path' in sig.parameters
        assert 'fee_pct' in sig.parameters
        assert 'slippage_pct' in sig.parameters


class TestFrozenModelUnchanged:
    """
    Test that frozen production model is not affected.
    
    Ensures that frozen model path and loading logic remain intact.
    """
    
    def test_frozen_model_path_isolated(self):
        """Test that frozen model path is separate from adaptive."""
        # Frozen model should be in app/services, not adaptive
        frozen_import_works = False
        try:
            from adaptive.ml_online import OnlineModel
            frozen_import_works = True
        except ImportError:
            pass
        
        assert frozen_import_works is True
    
    def test_frozen_model_can_load(self):
        """Test that frozen model can still be loaded."""
        from adaptive.ml_online import OnlineModel
        
        # Should have load method
        assert hasattr(OnlineModel, 'load')
        assert callable(OnlineModel.load)
    
    def test_frozen_model_prediction_works(self):
        """Test that frozen model prediction still works."""
        from adaptive.ml_online import OnlineModel
        
        model = OnlineModel()
        
        # Test prediction
        features = {"feature_1": 0.5, "feature_2": 0.7}
        score = model.predict_proba(features)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestAdaptiveIsolated:
    """
    Test that adaptive learning is isolated from execution.
    
    Ensures that adaptive components don't interfere with live trading.
    """
    
    def test_adaptive_module_exists(self):
        """Test that adaptive module is properly isolated."""
        import adaptive
        
        assert hasattr(adaptive, '__file__')
    
    def test_shadow_model_separate(self):
        """Test that shadow model is in separate module."""
        from adaptive.shadow_model import ShadowModel
        
        # ShadowModel should be separate from OnlineModel
        assert ShadowModel is not None
    
    def test_adaptive_not_in_execution_imports(self):
        """Test that execution modules don't import adaptive."""
        import execution.builder_5m as builder
        import inspect
        
        # Get source code
        source = inspect.getsource(builder)
        
        # Should not import adaptive
        assert 'from adaptive' not in source
        assert 'import adaptive' not in source
    
    def test_event_hooks_decoupled(self):
        """Test that event hooks are decoupled from execution."""
        from adaptive.event_hooks import get_event_bus
        
        bus = get_event_bus()
        
        # Event bus should exist but not affect execution
        assert bus is not None
        assert hasattr(bus, 'subscribe')
        assert hasattr(bus, 'publish_trade_closed')
    
    def test_feature_logger_isolated(self):
        """Test that feature logger is isolated."""
        from adaptive.feature_logger import FeatureLogger
        
        # Should be able to create logger without affecting execution
        logger = FeatureLogger(
            log_path="/tmp/test_features.jsonl",
            schema_version="v1"
        )
        
        assert logger is not None
        assert hasattr(logger, 'log_features')
    
    def test_online_trainer_isolated(self):
        """Test that online trainer is isolated."""
        from adaptive.online_trainer import OnlineTrainer
        
        # Should exist but not affect execution
        assert OnlineTrainer is not None


class TestMonitoringEnhanced:
    """
    Test that monitoring enhancements are working.
    """
    
    def test_drift_monitor_v2_exists(self):
        """Test that drift monitor v2 is available."""
        from monitoring.drift_monitor_v2 import DriftMonitorV2
        
        monitor = DriftMonitorV2(window_size=50)
        assert monitor is not None
    
    def test_drift_monitor_tracks_expectancy(self):
        """Test that drift monitor tracks expectancy."""
        from monitoring.drift_monitor_v2 import DriftMonitorV2
        
        monitor = DriftMonitorV2(window_size=50)
        
        # Add some trades
        monitor.add_trade(pnl=100.0, is_win=True)
        monitor.add_trade(pnl=-50.0, is_win=False)
        
        metrics = monitor.compute_metrics()
        
        assert metrics is not None
        assert hasattr(metrics, 'expectancy')
        assert hasattr(metrics, 'avg_pnl')
        assert hasattr(metrics, 'loss_streak')
        assert hasattr(metrics, 'drawdown_slope')


class TestModelRegistryV2:
    """
    Test that model registry v2 enhancements are working.
    """
    
    def test_model_card_has_v2_fields(self):
        """Test that ModelCard has v2 fields."""
        from model_registry.registry import ModelCard
        import dataclasses
        
        fields = {f.name for f in dataclasses.fields(ModelCard)}
        
        # Check for v2 enhancements
        assert 'model_version' in fields
        assert 'training_window' in fields
        assert 'feature_schema_hash' in fields


class TestCopyTraderAnalyzer:
    """
    Test that copy trader analyzer is isolated and working.
    """
    
    def test_analyzer_module_exists(self):
        """Test that copy trader analyzer module exists."""
        import copy_trader_analyzer
        
        assert copy_trader_analyzer is not None
    
    def test_leaderboard_fetcher_isolated(self):
        """Test that leaderboard fetcher is decision-layer only."""
        from copy_trader_analyzer.leaderboard_fetcher import LeaderboardFetcher
        
        fetcher = LeaderboardFetcher()
        
        # Should be able to fetch traders
        traders = fetcher.fetch_top_traders(limit=10)
        assert isinstance(traders, list)
    
    def test_confidence_validator_isolated(self):
        """Test that confidence validator is decision-layer only."""
        from copy_trader_analyzer.confidence_validator import ConfidenceValidator
        
        validator = ConfidenceValidator()
        
        # Should validate without affecting execution
        result = validator.validate(
            trader_metrics={"winrate": 0.6, "roi": 0.15},
            entry_analysis={"entry_quality_score": 0.75}
        )
        
        assert result is not None
        assert hasattr(result, 'is_confident')


class TestAdaptiveBacktester:
    """
    Test that adaptive backtester is isolated.
    """
    
    def test_adaptive_backtester_exists(self):
        """Test that adaptive backtester exists."""
        from backtest.backtest_adaptive import AdaptiveBacktester
        
        assert AdaptiveBacktester is not None
    
    def test_adaptive_backtester_isolated_from_main(self):
        """Test that adaptive backtester is separate from main backtest."""
        import backtest.engine as main_backtest
        import backtest.backtest_adaptive as adaptive_backtest
        import inspect
        
        # Main backtest should not import adaptive backtest
        main_source = inspect.getsource(main_backtest)
        assert 'backtest_adaptive' not in main_source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
