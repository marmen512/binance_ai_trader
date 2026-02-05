"""
Ensemble engine that combines multiple models for robust predictions.
"""
import os
import joblib
import numpy as np


class EnsembleEngine:
    """
    Loads multiple models and combines predictions using weighted voting.
    Class mapping: sklearn indices [0, 1, 2] -> SELL, HOLD, BUY
    """
    
    def __init__(self, model_dir="models"):
        """
        Args:
            model_dir: Directory containing model files
        """
        self.model_dir = model_dir
        self.models = []
        self.weights = [0.4, 0.3, 0.3]  # Default weights
        self.min_prob_override = None
        
        # Load models
        self._load_models()
    
    def _load_models(self):
        """
        Load ensemble models from disk.
        """
        model_files = [
            'rf_btc_5m.pkl',
            'gb_btc_5m.pkl', 
            'et_btc_5m.pkl'
        ]
        
        for fname in model_files:
            fpath = os.path.join(self.model_dir, fname)
            if os.path.exists(fpath):
                try:
                    model = joblib.load(fpath)
                    self.models.append(model)
                    print(f"[EnsembleEngine] Loaded {fname}")
                except Exception as e:
                    print(f"[EnsembleEngine] Error loading {fname}: {e}")
            else:
                print(f"[EnsembleEngine] Warning: {fname} not found")
        
        if len(self.models) == 0:
            print("[EnsembleEngine] Warning: No models loaded")
    
    def signal(self, features):
        """
        Generate trading signal from ensemble.
        
        Args:
            features: Feature array for prediction
            
        Returns:
            Tuple of (signal, probability) where signal is BUY/SELL/HOLD
        """
        if len(self.models) == 0:
            return ('HOLD', 0.5)
        
        # Get predictions from all models
        predictions = []
        probabilities = []
        
        for model in self.models:
            try:
                # Get class prediction
                pred = model.predict(features)[0]
                predictions.append(pred)
                
                # Get probability if available
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(features)[0]
                    probabilities.append(proba)
            except Exception as e:
                print(f"[EnsembleEngine] Prediction error: {e}")
                continue
        
        if len(predictions) == 0:
            return ('HOLD', 0.5)
        
        # Weighted voting
        class_votes = np.zeros(3)  # [SELL, HOLD, BUY]
        
        for i, pred in enumerate(predictions):
            weight = self.weights[i] if i < len(self.weights) else 1.0 / len(predictions)
            class_votes[pred] += weight
        
        # Get winning class
        winning_class = np.argmax(class_votes)
        
        # Calculate confidence (average probability for winning class)
        if len(probabilities) > 0:
            probs_for_class = [p[winning_class] for p in probabilities]
            confidence = np.mean(probs_for_class)
        else:
            confidence = class_votes[winning_class] / sum(class_votes)
        
        # Map class index to signal
        # 0 = SELL, 1 = HOLD, 2 = BUY
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = signal_map.get(winning_class, 'HOLD')
        
        # Apply probability override if set
        if self.min_prob_override is not None:
            if confidence < self.min_prob_override:
                signal = 'HOLD'
        
        return (signal, confidence)
    
    def set_weights(self, weights):
        """
        Update model weights.
        """
        if len(weights) == len(self.models):
            self.weights = weights
