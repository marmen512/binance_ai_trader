"""
Live model wrapper that hot-reloads model file when modified on disk.
"""
import os
import joblib
from datetime import datetime


class LiveModel:
    """
    Wrapper that reloads model file on disk when modified without restarting process.
    """
    
    def __init__(self, model_path):
        """
        Args:
            model_path: Path to the model file (.pkl)
        """
        self.model_path = model_path
        self.model = None
        self.last_mtime = None
        self._load_model()
    
    def _load_model(self):
        """
        Load or reload model from disk if file has been modified.
        """
        if not os.path.exists(self.model_path):
            print(f"[LiveModel] Model file not found: {self.model_path}")
            return
        
        current_mtime = os.path.getmtime(self.model_path)
        
        # Load model if first time or if file has been modified
        if self.last_mtime is None or current_mtime > self.last_mtime:
            try:
                self.model = joblib.load(self.model_path)
                self.last_mtime = current_mtime
                mtime_str = datetime.fromtimestamp(current_mtime).strftime('%Y-%m-%d %H:%M:%S')
                print(f"[LiveModel] Loaded model from {self.model_path} (mtime: {mtime_str})")
            except Exception as e:
                print(f"[LiveModel] Error loading model: {e}")
    
    def predict(self, X):
        """
        Make predictions, reloading model if file has changed.
        """
        self._load_model()
        
        if self.model is None:
            raise ValueError(f"Model not loaded from {self.model_path}")
        
        return self.model.predict(X)
    
    def predict_proba(self, X):
        """
        Predict probabilities, reloading model if file has changed.
        """
        self._load_model()
        
        if self.model is None:
            raise ValueError(f"Model not loaded from {self.model_path}")
        
        if not hasattr(self.model, 'predict_proba'):
            raise AttributeError("Model does not support predict_proba")
        
        return self.model.predict_proba(X)
