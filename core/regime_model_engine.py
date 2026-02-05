"""
Regime-specific model engine that selects model based on current market regime.
"""
import os
import joblib
from core.regime_detector import RegimeDetector
from features.feature_builder import FeatureBuilder


class RegimeModelEngine:
    """
    Loads regime-specific models and uses RegimeDetector to choose which model to predict.
    Returns (signal, probability) with internal probability threshold 0.62.
    """
    
    def __init__(self, model_dir="models", min_prob=0.62):
        """
        Args:
            model_dir: Directory containing regime-specific model files
            min_prob: Minimum probability threshold for signals
        """
        self.model_dir = model_dir
        self.min_prob = min_prob
        self.regime_detector = RegimeDetector()
        self.feature_builder = FeatureBuilder()
        self.models = {}
        
        # Load regime-specific models
        self._load_models()
    
    def _load_models(self):
        """
        Load regime-specific models: model_TREND.pkl, model_RANGE.pkl, model_VOLATILE.pkl
        """
        regimes = ['TREND', 'RANGE', 'VOLATILE']
        
        for regime in regimes:
            fname = f'model_{regime}.pkl'
            fpath = os.path.join(self.model_dir, fname)
            
            if os.path.exists(fpath):
                try:
                    model = joblib.load(fpath)
                    self.models[regime] = model
                    print(f"[RegimeModelEngine] Loaded {fname}")
                except Exception as e:
                    print(f"[RegimeModelEngine] Error loading {fname}: {e}")
            else:
                print(f"[RegimeModelEngine] Warning: {fname} not found")
        
        if len(self.models) == 0:
            print("[RegimeModelEngine] Warning: No regime models loaded")
    
    def signal(self, df):
        """
        Generate trading signal using regime-specific model.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (signal, probability) where signal is BUY/SELL/HOLD
        """
        if len(self.models) == 0:
            return ('HOLD', 0.5)
        
        # Detect current regime
        regime = self.regime_detector.get_current_regime(df)
        
        # Get model for this regime
        model = self.models.get(regime)
        if model is None:
            # Fallback to RANGE if regime model not found
            model = self.models.get('RANGE')
            if model is None:
                return ('HOLD', 0.5)
        
        # Build features
        features = self.feature_builder.build(df)
        
        try:
            # Get prediction
            pred_class = model.predict(features)[0]
            
            # Get probability if available
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(features)[0]
                confidence = proba[pred_class]
            else:
                confidence = 0.7  # Default confidence
            
            # Map class to signal: 0=SELL, 1=HOLD, 2=BUY
            signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
            signal = signal_map.get(pred_class, 'HOLD')
            
            # Apply probability threshold
            if confidence < self.min_prob:
                signal = 'HOLD'
            
            return (signal, confidence)
        
        except Exception as e:
            print(f"[RegimeModelEngine] Prediction error: {e}")
            return ('HOLD', 0.5)
