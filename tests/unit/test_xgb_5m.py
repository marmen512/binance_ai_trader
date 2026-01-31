"""
Unit tests for XGBoost 5m training module.
"""
import pytest
from training.xgb_5m import train_xgb_5m, TrainResult


class TestXGB5m:
    """Tests for XGBoost 5-minute training module."""

    def test_train_result_structure(self):
        """Test TrainResult dataclass has correct attributes."""
        result = TrainResult(best_iteration=10, val_mlogloss=0.5)
        assert result.best_iteration == 10
        assert result.val_mlogloss == 0.5

    def test_train_xgb_5m_returns_train_result(self):
        """Test that train_xgb_5m returns a TrainResult instance."""
        result = train_xgb_5m()
        assert isinstance(result, TrainResult)

    def test_train_xgb_5m_with_config_path(self):
        """Test that train_xgb_5m accepts config_path parameter."""
        result = train_xgb_5m(config_path="/path/to/config.yaml")
        assert isinstance(result, TrainResult)

    def test_train_result_has_expected_attributes(self):
        """Test that TrainResult has best_iteration and val_mlogloss."""
        result = train_xgb_5m()
        assert hasattr(result, 'best_iteration')
        assert hasattr(result, 'val_mlogloss')
        assert isinstance(result.best_iteration, int)
        assert isinstance(result.val_mlogloss, float)

    def test_train_result_is_json_serializable(self):
        """Test that TrainResult can be serialized to JSON."""
        import json
        result = train_xgb_5m()
        json_str = json.dumps(result.__dict__)
        assert json_str is not None
        
        # Verify we can deserialize
        data = json.loads(json_str)
        assert 'best_iteration' in data
        assert 'val_mlogloss' in data
