"""Tests for Model Registry - Phase 8"""

import pytest
import joblib
import numpy as np
from pathlib import Path
from sklearn.linear_model import SGDClassifier
import time

from adaptive.model_registry import save_shadow, list_versions, load_version, get_latest_version


class TestModelRegistry:
    """Test model registry versioning and rollback"""
    
    def test_registry_saves_model(self, tmp_path, monkeypatch):
        """Test that registry saves model with timestamp"""
        # Temporarily change registry path
        from adaptive import model_registry
        monkeypatch.setattr(model_registry, "REG_PATH", tmp_path)
        
        # Create a model
        model = SGDClassifier(random_state=42)
        model.fit([[1, 2], [3, 4]], [0, 1])
        
        # Save model
        saved_path = save_shadow(model)
        
        # Verify file exists
        assert saved_path.exists()
        assert saved_path.name.startswith("shadow_")
        assert saved_path.suffix == ".pkl"
        
        # Verify can load back
        loaded = joblib.load(saved_path)
        assert loaded is not None
    
    def test_list_versions(self, tmp_path, monkeypatch):
        """Test listing all saved versions"""
        from adaptive import model_registry
        monkeypatch.setattr(model_registry, "REG_PATH", tmp_path)
        
        # Create and save multiple versions
        for i in range(3):
            model = SGDClassifier(random_state=42 + i)
            model.fit([[1, 2], [3, 4]], [0, 1])
            save_shadow(model)
            time.sleep(0.1)  # Ensure different timestamps
        
        # List versions
        versions = list_versions()
        
        assert len(versions) == 3
        # Should be sorted by timestamp (most recent first)
        assert versions[0][0] > versions[1][0]
        assert versions[1][0] > versions[2][0]
    
    def test_load_version(self, tmp_path, monkeypatch):
        """Test loading a specific version"""
        from adaptive import model_registry
        monkeypatch.setattr(model_registry, "REG_PATH", tmp_path)
        
        # Create and save a model
        model = SGDClassifier(random_state=42)
        model.fit([[1, 2], [3, 4]], [0, 1])
        saved_path = save_shadow(model)
        
        # Extract timestamp from path
        timestamp = int(saved_path.stem.split("_")[1])
        
        # Load by timestamp
        loaded = load_version(timestamp)
        
        assert loaded is not None
        # Verify it's the same model by checking predictions
        X_test = np.array([[2, 3]])
        assert np.array_equal(loaded.predict(X_test), model.predict(X_test))
    
    def test_get_latest_version(self, tmp_path, monkeypatch):
        """Test getting the most recent version"""
        from adaptive import model_registry
        monkeypatch.setattr(model_registry, "REG_PATH", tmp_path)
        
        # No versions initially
        latest = get_latest_version()
        assert latest is None
        
        # Save some versions
        for i in range(3):
            model = SGDClassifier(random_state=42 + i)
            model.fit([[1, 2], [3, 4]], [0, 1])
            last_saved = save_shadow(model)
            time.sleep(0.1)
        
        # Get latest
        latest = get_latest_version()
        
        assert latest is not None
        assert latest[1] == last_saved  # Should be the last saved path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
