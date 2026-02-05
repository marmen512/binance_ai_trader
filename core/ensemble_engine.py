"""
Ensemble Engine for Signal Generation
Loads ensemble models and generates trading signals with probability thresholds
"""
import joblib
import numpy as np
import pandas as pd


class EnsembleEngine:
    """Ensemble model engine for signal generation"""
    
    def __init__(self, model_paths=None, weights=None, min_prob_override=None):
        """
        Initialize ensemble engine
        
        Args:
            model_paths: List of paths to model files (default: RF, GB, ET for BTC 5m)
            weights: List of weights for ensemble voting (default: [0.4, 0.3, 0.3])
            min_prob_override: Override minimum probability threshold (used by threshold optimizer)
        """
        if model_paths is None:
            model_paths = [
                'models/rf_btc_5m.pkl',
                'models/gb_btc_5m.pkl',
                'models/et_btc_5m.pkl'
            ]
        
        if weights is None:
            weights = [0.4, 0.3, 0.3]
        
        self.models = [joblib.load(path) for path in model_paths]
        self.weights = np.array(weights)
        self.min_prob_override = min_prob_override
        
        # Feature columns used for prediction
        self.feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 
                             'range', 'body', 'body_pct', 'vol_spike']
        
        # Class mapping: index 0=SELL, 1=HOLD, 2=BUY
        # This maps to model predictions where classes are [-1, 0, 1]
        self.class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
    
    def signal(self, df):
        """
        Generate trading signal from ensemble models
        
        Args:
            df: DataFrame with features (last row is used for prediction)
            
        Returns:
            Tuple of (signal, confidence) where:
                signal: "BUY", "SELL", or "HOLD"
                confidence: probability of predicted class (0-1)
        """
        # Get last row features
        last_row = df[self.feature_cols].iloc[-1:].values
        
        # Get predictions from all models
        predictions = []
        probabilities = []
        
        for model in self.models:
            pred_proba = model.predict_proba(last_row)[0]
            probabilities.append(pred_proba)
            pred_class = np.argmax(pred_proba)
            predictions.append(pred_class)
        
        # Weighted ensemble voting
        # Average probabilities with weights
        weighted_proba = np.average(probabilities, axis=0, weights=self.weights)
        
        # Get predicted class and confidence
        pred_class = np.argmax(weighted_proba)
        confidence = weighted_proba[pred_class]
        
        # Apply minimum probability threshold
        min_prob = self.min_prob_override if self.min_prob_override is not None else 0.55
        
        if confidence < min_prob:
            return "HOLD", confidence
        
        signal = self.class_map[pred_class]
        return signal, confidence
