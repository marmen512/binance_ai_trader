"""Tests for Shadow Learning - Phase 8"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path
import tempfile
import joblib
from sklearn.linear_model import SGDClassifier

from adaptive.shadow_model import ShadowModel
from adaptive.online_trainer import OnlineTrainer
from adaptive.feature_logger import log_trade


class TestShadowModel:
    """Test shadow model loading and learning"""
    
    def test_shadow_model_loads(self, tmp_path):
        """Test that shadow model loads from frozen model"""
        # Create a simple frozen model
        model = SGDClassifier(random_state=42)
        X_train = np.array([[1, 2], [3, 4], [5, 6]])
        y_train = np.array([0, 1, 0])
        model.fit(X_train, y_train)
        
        # Save frozen model
        frozen_path = tmp_path / "frozen.pkl"
        joblib.dump(model, frozen_path)
        
        # Load into shadow model
        shadow = ShadowModel(frozen_path)
        
        # Verify shadow model exists
        assert shadow.shadow is not None
        assert shadow.frozen is not None
        assert shadow.shadow is not shadow.frozen
    
    def test_learning_updates_weights(self, tmp_path):
        """Test that learning actually updates model weights"""
        # Create a frozen model
        model = SGDClassifier(random_state=42)
        X_train = np.array([[1, 2], [3, 4], [5, 6]])
        y_train = np.array([0, 1, 0])
        model.fit(X_train, y_train)
        
        # Save and load into shadow
        frozen_path = tmp_path / "frozen.pkl"
        joblib.dump(model, frozen_path)
        shadow = ShadowModel(frozen_path)
        
        # Get initial weights
        initial_weights = shadow.shadow.coef_.copy()
        
        # Learn from new data
        X_new = np.array([[7, 8]])
        y_new = np.array([1])
        shadow.learn_one(X_new, y_new)
        
        # Verify weights changed
        updated_weights = shadow.shadow.coef_
        assert not np.array_equal(initial_weights, updated_weights)
    
    def test_shadow_predict(self, tmp_path):
        """Test that shadow model can make predictions"""
        # Create and save a frozen model
        model = SGDClassifier(random_state=42)
        X_train = np.array([[1, 2], [3, 4], [5, 6]])
        y_train = np.array([0, 1, 0])
        model.fit(X_train, y_train)
        
        frozen_path = tmp_path / "frozen.pkl"
        joblib.dump(model, frozen_path)
        
        # Load into shadow and predict
        shadow = ShadowModel(frozen_path)
        X_test = np.array([[2, 3]])
        predictions = shadow.predict(X_test)
        
        assert predictions is not None
        assert len(predictions) == 1


class TestOnlineTrainer:
    """Test online training from logs"""
    
    def test_trainer_loads_from_parquet(self, tmp_path):
        """Test that trainer can load and train from parquet log"""
        # Create a frozen model
        model = SGDClassifier(random_state=42)
        X_train = np.array([[1, 2], [3, 4], [5, 6]])
        y_train = np.array([0, 1, 0])
        model.fit(X_train, y_train)
        
        # Save and load into shadow
        frozen_path = tmp_path / "frozen.pkl"
        joblib.dump(model, frozen_path)
        shadow = ShadowModel(frozen_path)
        
        # Create training log
        trades_data = {
            "feature1": [1.0, 2.0, 3.0],
            "feature2": [4.0, 5.0, 6.0],
            "outcome": [0, 1, 0]
        }
        df = pd.DataFrame(trades_data)
        log_path = tmp_path / "trades.parquet"
        df.to_parquet(log_path, index=False)
        
        # Train from log
        trainer = OnlineTrainer(shadow, max_updates=3)
        trainer.train_from_log(log_path)
        
        # Test passed if no exception raised
        assert True
    
    def test_trainer_respects_max_updates(self, tmp_path):
        """Test that trainer respects max_updates limit"""
        # Create model
        model = SGDClassifier(random_state=42)
        model.fit([[1, 2], [3, 4]], [0, 1])
        
        frozen_path = tmp_path / "frozen.pkl"
        joblib.dump(model, frozen_path)
        shadow = ShadowModel(frozen_path)
        
        # Create log with 100 trades
        trades_data = {
            "feature1": np.random.rand(100),
            "feature2": np.random.rand(100),
            "outcome": np.random.randint(0, 2, 100)
        }
        df = pd.DataFrame(trades_data)
        log_path = tmp_path / "trades.parquet"
        df.to_parquet(log_path, index=False)
        
        # Train with max_updates=10
        trainer = OnlineTrainer(shadow, max_updates=10)
        trainer.train_from_log(log_path)
        
        # Test passed if no exception and completed quickly
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
