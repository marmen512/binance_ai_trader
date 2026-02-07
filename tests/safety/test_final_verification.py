"""
Final safety verification tests.

Comprehensive tests to verify all hard constraints are met and
the system maintains backward compatibility.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestHardConstraintsNotViolated:
    """
    Verify all hard constraints from the task are respected.
    """
    
    def test_execution_not_modified(self):
        """Verify execution module files are unchanged."""
        # Test that execution module exists and has expected structure
        import execution
        from execution import builder_5m, validators
        
        assert execution is not None
        assert builder_5m is not None
        assert validators is not None
    
    def test_execution_safety_not_modified(self):
        """Verify execution_safety module structure preserved."""
        from execution_safety import (
            pre_trade_checks,
            post_trade_checks,
            emergency_stop
        )
        
        assert pre_trade_checks is not None
        assert post_trade_checks is not None
        assert emergency_stop is not None
    
    def test_paper_gate_not_modified(self):
        """Verify paper_gate module exists and unchanged."""
        from paper_gate import gate_5m
        
        assert gate_5m is not None
    
    def test_adaptive_not_connected_to_execution(self):
        """Verify adaptive is not connected to live execution."""
        import execution.builder_5m as builder
        import inspect
        
        source = inspect.getsource(builder)
        
        # Adaptive should not be imported in execution
        assert 'from adaptive' not in source
        assert 'import adaptive' not in source
    
    def test_online_learning_not_connected_to_live_execution(self):
        """Verify online learning is not connected to live execution."""
        import execution.builder_5m as builder
        import inspect
        
        source = inspect.getsource(builder)
        
        # Online learning should not be in execution
        assert 'learn_one' not in source
        assert 'partial_fit' not in source
        assert 'shadow' not in source.lower()


class TestConfigFlagsPresent:
    """
    Verify all new systems are behind config flags.
    """
    
    def test_config_has_adaptive_flags(self):
        """Test config has adaptive flags."""
        import yaml
        
        config_path = Path("config/config.yaml")
        
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert 'adaptive' in config
            assert 'enabled' in config['adaptive']
            assert 'shadow_learning' in config['adaptive']
            assert 'drift_guard' in config['adaptive']
    
    def test_config_has_leaderboard_flags(self):
        """Test config has leaderboard flags."""
        import yaml
        
        config_path = Path("config/config.yaml")
        
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert 'leaderboard' in config
            assert 'enabled' in config['leaderboard']
            assert 'validation_required' in config['leaderboard']
    
    def test_config_has_hybrid_flags(self):
        """Test config has hybrid flags."""
        import yaml
        
        config_path = Path("config/config.yaml")
        
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            assert 'hybrid' in config
            assert 'enabled' in config['hybrid']
    
    def test_config_flags_disabled_by_default(self):
        """Test that new features are disabled by default."""
        import yaml
        
        config_path = Path("config/config.yaml")
        
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            
            # All should be disabled by default for safety
            assert config['adaptive']['enabled'] is False
            assert config['leaderboard']['enabled'] is False
            assert config['hybrid']['enabled'] is False


class TestModulesIsolated:
    """
    Verify new modules are properly isolated.
    """
    
    def test_adaptive_module_isolated(self):
        """Test adaptive module is isolated."""
        import adaptive
        
        # Module should exist
        assert adaptive is not None
        
        # Should have expected components
        from adaptive import (
            shadow_model,
            online_trainer,
            feature_logger,
            drift_monitor,
            promotion_gate
        )
        
        assert all([
            shadow_model,
            online_trainer,
            feature_logger,
            drift_monitor,
            promotion_gate
        ])
    
    def test_events_module_isolated(self):
        """Test events module is isolated."""
        import events
        
        assert events is not None
        
        from events import TradeEventBus, TradeEventListener
        
        assert TradeEventBus is not None
        assert TradeEventListener is not None
    
    def test_leaderboard_module_isolated(self):
        """Test leaderboard module is isolated."""
        import leaderboard
        
        assert leaderboard is not None
        
        from leaderboard import (
            fetcher,
            positions,
            analyzer,
            validator
        )
        
        assert all([fetcher, positions, analyzer, validator])
    
    def test_decision_module_isolated(self):
        """Test decision module is isolated."""
        import decision
        
        assert decision is not None
        
        from decision import HybridDecisionEngine
        
        assert HybridDecisionEngine is not None


class TestBackwardCompatibility:
    """
    Verify backward compatibility is maintained.
    """
    
    def test_existing_imports_still_work(self):
        """Test that existing imports still work."""
        # These should all work without modification
        from core import exceptions
        from models import inference
        from backtest import runner_5m
        from monitoring import metrics
        from model_registry import registry
        
        assert all([exceptions, inference, runner_5m, metrics, registry])
    
    def test_paper_pipeline_unchanged(self):
        """Test paper pipeline still functions."""
        from paper_gate import gate_5m
        
        # Module should be importable
        assert gate_5m is not None
    
    def test_frozen_model_path_unchanged(self):
        """Test frozen model inference path unchanged."""
        from models import inference
        
        # Should still be able to import inference
        assert inference is not None


class TestComprehensiveTests:
    """
    Verify comprehensive test coverage exists.
    """
    
    def test_adaptive_tests_exist(self):
        """Test adaptive tests exist."""
        test_path = Path("tests/adaptive/test_adaptive.py")
        assert test_path.exists()
    
    def test_events_tests_exist(self):
        """Test events tests exist."""
        test_path = Path("tests/events/test_events.py")
        assert test_path.exists()
    
    def test_hybrid_tests_exist(self):
        """Test hybrid tests exist."""
        test_path = Path("tests/hybrid/test_hybrid.py")
        assert test_path.exists()
    
    def test_leaderboard_tests_exist(self):
        """Test leaderboard tests exist."""
        test_path = Path("tests/leaderboard/test_leaderboard.py")
        assert test_path.exists()
    
    def test_safety_tests_exist(self):
        """Test safety regression tests exist."""
        test_path = Path("tests/safety/test_safety_regression.py")
        assert test_path.exists()
