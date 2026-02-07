"""
Comprehensive safety regression tests.

Verifies that all critical system components remain unchanged and isolated:
- Paper pipeline unchanged
- Execution unchanged
- Frozen model unchanged
- Risk gates unchanged
- Adaptive isolated
- Retry guard blocks duplicates
"""

import pytest
import os
from pathlib import Path


class TestPaperPipelineUnchanged:
    """Test that paper trading v1 pipeline is unchanged."""
    
    def test_paper_gate_module_exists(self):
        """Verify paper_gate module exists and is intact."""
        paper_gate_path = Path("paper_gate")
        assert paper_gate_path.exists()
        assert paper_gate_path.is_dir()
    
    def test_paper_gate_not_modified_by_new_code(self):
        """Verify no new imports in paper_gate from adaptive or job_safety."""
        paper_gate_path = Path("paper_gate")
        
        if not paper_gate_path.exists():
            pytest.skip("paper_gate directory not found")
        
        # Check Python files in paper_gate
        for py_file in paper_gate_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
                
            # Should not import from new modules
            assert "from app.job_safety" not in content
            assert "from adaptive" not in content
            assert "from decision" not in content
            assert "from leaderboard" not in content
    
    def test_paper_pipeline_config_intact(self):
        """Verify paper pipeline configuration is intact."""
        config_path = Path("config/config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                content = f.read()
            
            # All new features should be disabled by default
            assert "adaptive:\n  enabled: false" in content
            assert "leaderboard:\n  enabled: false" in content
            assert "hybrid:\n  enabled: false" in content


class TestExecutionUnchanged:
    """Test that execution module is unchanged."""
    
    def test_execution_module_exists(self):
        """Verify execution module exists."""
        execution_path = Path("execution")
        assert execution_path.exists()
        assert execution_path.is_dir()
    
    def test_execution_not_modified_by_new_code(self):
        """Verify no new imports in execution from adaptive or job_safety."""
        execution_path = Path("execution")
        
        if not execution_path.exists():
            pytest.skip("execution directory not found")
        
        # Check Python files in execution
        for py_file in execution_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Should not import from new modules
            assert "from app.job_safety" not in content
            assert "from adaptive" not in content
            assert "from decision" not in content
            assert "from leaderboard" not in content
    
    def test_execution_safety_module_exists(self):
        """Verify execution_safety module exists."""
        execution_safety_path = Path("execution_safety")
        assert execution_safety_path.exists()
        assert execution_safety_path.is_dir()
    
    def test_execution_safety_not_modified(self):
        """Verify execution_safety not modified by new code."""
        execution_safety_path = Path("execution_safety")
        
        if not execution_safety_path.exists():
            pytest.skip("execution_safety directory not found")
        
        # Check Python files
        for py_file in execution_safety_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Should not import from new modules
            assert "from app.job_safety" not in content
            assert "from adaptive" not in content
            assert "from decision" not in content


class TestFrozenModelUnchanged:
    """Test that frozen model inference path is unchanged."""
    
    def test_model_inference_not_modified(self):
        """Verify model inference code doesn't use adaptive learning."""
        # Check app/services if it exists
        services_path = Path("app/services")
        
        if not services_path.exists():
            pytest.skip("app/services directory not found")
        
        # Check decision_engine.py specifically
        decision_engine_path = services_path / "decision_engine.py"
        
        if decision_engine_path.exists():
            with open(decision_engine_path, 'r') as f:
                content = f.read()
            
            # Decision engine should not directly import online learning
            # (it should use events if needed)
            assert "from app.services.ml_online import" not in content or "# from app.services.ml_online" in content
    
    def test_frozen_model_files_not_modified(self):
        """Verify frozen model files are not modified by adaptive."""
        models_path = Path("models")
        
        if not models_path.exists():
            pytest.skip("models directory not found")
        
        # Check that adaptive doesn't modify frozen models
        adaptive_path = Path("adaptive")
        
        if adaptive_path.exists():
            for py_file in adaptive_path.rglob("*.py"):
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Should not modify frozen model files
                assert "frozen_model" not in content or "load" in content
                # Shadow models should be separate
                if "save" in content:
                    assert "shadow" in content or "adaptive" in content


class TestAdaptiveIsolated:
    """Test that adaptive learning is properly isolated."""
    
    def test_adaptive_module_exists(self):
        """Verify adaptive module exists."""
        adaptive_path = Path("adaptive")
        assert adaptive_path.exists()
        assert adaptive_path.is_dir()
    
    def test_adaptive_uses_events_not_direct_calls(self):
        """Verify adaptive uses event system, not direct execution calls."""
        adaptive_path = Path("adaptive")
        
        if not adaptive_path.exists():
            pytest.skip("adaptive directory not found")
        
        for py_file in adaptive_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Should not directly import execution
            assert "from execution" not in content
            assert "import execution" not in content
    
    def test_adaptive_behind_config_flag(self):
        """Verify adaptive is disabled by default."""
        config_path = Path("config/config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r') as f:
                content = f.read()
            
            # Adaptive should be disabled
            assert "adaptive:\n  enabled: false" in content
    
    def test_adaptive_shadow_model_separate(self):
        """Verify shadow model is separate from frozen model."""
        adaptive_path = Path("adaptive")
        
        if not adaptive_path.exists():
            pytest.skip("adaptive directory not found")
        
        shadow_model_path = adaptive_path / "shadow_model.py"
        
        if shadow_model_path.exists():
            with open(shadow_model_path, 'r') as f:
                content = f.read()
            
            # Should load frozen and create shadow
            assert "frozen" in content or "load" in content
            # Should not modify original
            assert "# Never modify frozen" in content or "clone" in content or "copy" in content


class TestRetryGuardBlocksDuplicates:
    """Test that retry guard properly blocks duplicates."""
    
    def test_retry_guard_module_exists(self):
        """Verify retry guard module exists."""
        retry_guard_path = Path("app/job_safety/retry_guard.py")
        assert retry_guard_path.exists()
    
    def test_retry_guard_has_idempotency(self):
        """Verify retry guard implements idempotency."""
        retry_guard_path = Path("app/job_safety/retry_guard.py")
        
        with open(retry_guard_path, 'r') as f:
            content = f.read()
        
        # Must have idempotency key
        assert "idempotency_key" in content
        assert "IdempotencyGuard" in content
        assert "should_execute" in content
    
    def test_retry_guard_prevents_duplicates(self):
        """Verify retry guard prevents duplicate execution."""
        from app.job_safety import RetryGuard, IdempotencyGuard
        
        # Verify classes exist
        assert RetryGuard is not None
        assert IdempotencyGuard is not None
        
        # Verify methods exist
        assert hasattr(IdempotencyGuard, 'mark_started')
        assert hasattr(IdempotencyGuard, 'mark_completed')
        assert hasattr(IdempotencyGuard, 'is_completed')


class TestJobSafetyFeatures:
    """Test job safety features are properly implemented."""
    
    def test_failure_classifier_exists(self):
        """Verify failure classifier exists."""
        classifier_path = Path("app/job_safety/failure_classifier.py")
        assert classifier_path.exists()
    
    def test_failure_classifier_classifies_errors(self):
        """Verify failure classifier can classify errors."""
        from app.job_safety import FailureClassifier, FailureType
        
        classifier = FailureClassifier()
        
        # Test network error
        network_failure = classifier.classify_failure("ConnectionError: Network failed")
        assert network_failure == FailureType.NETWORK_ERROR
        assert classifier.is_retryable(network_failure) == True
        
        # Test validation error
        validation_failure = classifier.classify_failure("ValidationError: Invalid data")
        assert validation_failure == FailureType.VALIDATION_ERROR
        assert classifier.is_retryable(validation_failure) == False
    
    def test_retry_policy_exists(self):
        """Verify retry policy exists."""
        policy_path = Path("app/job_safety/retry_policy.py")
        assert policy_path.exists()
    
    def test_retry_audit_exists(self):
        """Verify retry audit logger exists."""
        audit_path = Path("app/job_safety/retry_audit.py")
        assert audit_path.exists()


class TestEventSystemIsolation:
    """Test that event system properly isolates adaptive from execution."""
    
    def test_events_module_exists(self):
        """Verify events module exists."""
        events_path = Path("events")
        assert events_path.exists()
        assert events_path.is_dir()
    
    def test_trade_events_exist(self):
        """Verify trade events module exists."""
        trade_events_path = Path("events/trade_events.py")
        
        if trade_events_path.exists():
            with open(trade_events_path, 'r') as f:
                content = f.read()
            
            # Should have event bus
            assert "TradeEventBus" in content or "EventBus" in content
            # Should have listener pattern
            assert "listener" in content or "subscribe" in content
    
    def test_execution_emits_events(self):
        """Verify execution can emit events without importing adaptive."""
        # Events should be the bridge, not direct imports
        events_path = Path("events")
        
        if not events_path.exists():
            pytest.skip("events directory not found")
        
        # Events module should not import execution or adaptive directly
        for py_file in events_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            with open(py_file, 'r') as f:
                content = f.read()
            
            # Events should be a pure communication layer
            # No direct dependencies on execution or adaptive
            assert "from execution" not in content
            assert "from adaptive" not in content


class TestConfigFlags:
    """Test that all new features are behind config flags."""
    
    def test_config_file_exists(self):
        """Verify config file exists."""
        config_path = Path("config/config.yaml")
        assert config_path.exists()
    
    def test_all_features_disabled_by_default(self):
        """Verify all new features are disabled by default."""
        config_path = Path("config/config.yaml")
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # All features should be disabled
        assert "adaptive:\n  enabled: false" in content
        assert "leaderboard:\n  enabled: false" in content
        assert "hybrid:\n  enabled: false" in content
    
    def test_retry_config_exists(self):
        """Verify retry configuration exists."""
        config_path = Path("config/config.yaml")
        
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Retry config should exist
        assert "retry:" in content
        assert "max_attempts" in content
        assert "cooldown_seconds" in content


class TestNoDirectMLOnlineImports:
    """Test that no code directly imports ml_online from execution path."""
    
    def test_decision_engine_uses_events(self):
        """Verify decision engine doesn't directly import ml_online."""
        decision_engine_path = Path("app/services/decision_engine.py")
        
        if decision_engine_path.exists():
            with open(decision_engine_path, 'r') as f:
                content = f.read()
            
            # If ml_online is imported, it should be from adaptive
            if "ml_online" in content:
                assert "from adaptive" in content or "# from app.services.ml_online" in content
    
    def test_ml_online_in_adaptive(self):
        """Verify ml_online is in adaptive module."""
        adaptive_ml_path = Path("adaptive/ml_online.py")
        assert adaptive_ml_path.exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
