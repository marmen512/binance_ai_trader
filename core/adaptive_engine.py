"""
Adaptive engine using live model and feature builder for predictions.
"""
from core.live_model import LiveModel
from features.feature_builder import FeatureBuilder


class AdaptiveEngine:
    """
    Uses LiveModel wrapper that hot-reloads when model file changes.
    Generates (BUY|SELL|HOLD, probability) signals.
    """
    
    def __init__(self, model_path="models/adaptive_latest.pkl"):
        """
        Args:
            model_path: Path to the adaptive model file
        """
        self.model = LiveModel(model_path)
        self.feature_builder = FeatureBuilder()
    
    def signal(self, df):
        """
        Generate trading signal from current data.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (signal, probability) where signal is BUY/SELL/HOLD
        """
        # Build features
        features = self.feature_builder.build(df)
        
        try:
            # Get prediction
            pred_class = self.model.predict(features)[0]
            
            # Get probability if available
            if hasattr(self.model.model, 'predict_proba'):
                proba = self.model.predict_proba(features)[0]
                confidence = proba[pred_class]
            else:
                confidence = 0.7  # Default confidence if probabilities not available
            
            # Map class to signal: 0=SELL, 1=HOLD, 2=BUY
            signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
            signal = signal_map.get(pred_class, 'HOLD')
            
            return (signal, confidence)
        
        except Exception as e:
            print(f"[AdaptiveEngine] Prediction error: {e}")
            return ('HOLD', 0.5)
