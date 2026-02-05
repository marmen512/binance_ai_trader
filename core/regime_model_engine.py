"""
Regime Model Engine
Uses regime-specific models for trading signal generation
"""
import joblib
import numpy as np
from core.regime_detector import RegimeDetector


class RegimeModelEngine:
    """
    Trading engine that uses regime-specific models
    Detects regime and uses corresponding model
    """
    
    def __init__(self, regime_detector=None, min_prob=0.62):
        """
        Initialize regime model engine
        
        Args:
            regime_detector: RegimeDetector instance (creates default if None)
            min_prob: Minimum probability threshold (default 0.62)
        """
        self.regime_detector = regime_detector or RegimeDetector()
        self.min_prob = min_prob
        
        # Load regime-specific models
        self.models = {
            'VOLATILE': joblib.load('models/model_VOLATILE.pkl'),
            'TREND': joblib.load('models/model_TREND.pkl'),
            'RANGE': joblib.load('models/model_RANGE.pkl')
        }
        
        # Feature columns
        self.feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 
                             'range', 'body', 'body_pct', 'vol_spike']
        
        # Class mapping: index 0=SELL, 1=HOLD, 2=BUY
        self.class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
    
    def signal(self, df):
        """
        Generate trading signal using regime-specific model
        
        Args:
            df: DataFrame with features
            
        Returns:
            Tuple of (signal, confidence) where:
                signal: "BUY", "SELL", or "HOLD"
                confidence: probability of predicted class (0-1)
        """
        # Detect current regime
        regime = self.regime_detector.detect(df)
        
        # Get corresponding model
        model = self.models[regime]
        
        # Get last row features
        last_row = df[self.feature_cols].iloc[-1:].values
        
        # Get prediction
        pred_proba = model.predict_proba(last_row)[0]
        pred_class = np.argmax(pred_proba)
        confidence = pred_proba[pred_class]
        
        # Apply minimum probability threshold
        if confidence < self.min_prob:
            return "HOLD", confidence
        
        signal = self.class_map[pred_class]
        return signal, confidence
