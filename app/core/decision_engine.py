"""
Decision engine for signal prediction using trained models.
"""
import os
import joblib
import numpy as np
from typing import Dict, Any, Optional


class DecisionEngine:
    """
    Decision engine that loads a serialized model artifact and makes predictions.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the decision engine.
        
        Args:
            model_path: Path to the serialized model artifact (joblib file).
                       Defaults to models/signal_model.pkl or SIGNAL_MODEL_PATH env var.
        """
        if model_path is None:
            model_path = os.getenv('SIGNAL_MODEL_PATH', 'models/signal_model.pkl')
        
        self.model_path = model_path
        self.artifact = None
        self.model = None
        self.preprocessor = None
        self.feature_names = None
        
        # Risk management parameters (can be overridden)
        self.min_confidence = 0.6
        self.volatility_max = 0.05
        self.max_spread_pct = 0.02
        
        self._load_artifact()
    
    def _load_artifact(self):
        """Load the serialized model artifact."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model artifact not found at {self.model_path}")
        
        self.artifact = joblib.load(self.model_path)
        
        # Extract components from artifact
        self.model = self.artifact.get('model')
        self.preprocessor = self.artifact.get('preprocessor')
        self.feature_names = self.artifact.get('feature_names', [])
        
        if self.model is None:
            raise ValueError("Model not found in artifact")
    
    def predict_score(self, features: Dict[str, Any]) -> float:
        """
        Predict the probability score for the positive class.
        
        Args:
            features: Dictionary of feature name -> value
            
        Returns:
            Probability score for the positive class (class 1)
        """
        # Convert features dict to array in the correct order
        feature_values = []
        for fname in self.feature_names:
            feature_values.append(features.get(fname, 0.0))
        
        X = np.array([feature_values])
        
        # Apply preprocessor if present
        if self.preprocessor is not None:
            X = self.preprocessor.transform(X)
        
        # Get probability predictions
        if hasattr(self.model, 'predict_proba'):
            proba = self.model.predict_proba(X)[0]
            
            # Handle multiclass: return probability of positive class (class 1)
            # For 3-class: [-1, 0, 1], we want probability of class index 2 (label 1)
            # We need to check the classes_ attribute
            if hasattr(self.model, 'classes_'):
                classes = self.model.classes_
                if 1 in classes:
                    # Find index of class 1
                    pos_idx = list(classes).index(1)
                    return float(proba[pos_idx])
                else:
                    # Fallback: return max probability
                    return float(np.max(proba))
            else:
                # Binary classification: return probability of class 1
                if len(proba) == 2:
                    return float(proba[1])
                else:
                    return float(np.max(proba))
        else:
            # Model doesn't support predict_proba, use decision_function or predict
            if hasattr(self.model, 'decision_function'):
                decision = self.model.decision_function(X)[0]
                # Convert to probability-like score using sigmoid
                score = 1.0 / (1.0 + np.exp(-decision))
                return float(score)
            else:
                # Last resort: use prediction as binary score
                pred = self.model.predict(X)[0]
                return 1.0 if pred == 1 else 0.0
    
    def apply_risk_filters(self, features: Dict[str, Any], score: float) -> Dict[str, Any]:
        """
        Apply risk management filters to the prediction score.
        
        Args:
            features: Dictionary of feature name -> value
            score: Model prediction score
            
        Returns:
            Dictionary with keys: action, confidence, reasons, model_score
        """
        reasons = []
        action = "hold"  # default action
        
        # Check minimum confidence
        if score < self.min_confidence:
            reasons.append(f"Score {score:.3f} below minimum confidence {self.min_confidence}")
        
        # Check volatility
        volatility = features.get('volatility', 0.0)
        if volatility > self.volatility_max:
            reasons.append(f"Volatility {volatility:.4f} exceeds maximum {self.volatility_max}")
        
        # Check spread
        spread = features.get('high_low_spread', 0.0)
        if spread > self.max_spread_pct:
            reasons.append(f"Spread {spread:.4f} exceeds maximum {self.max_spread_pct}")
        
        # Determine action
        if len(reasons) == 0 and score >= self.min_confidence:
            action = "buy"
            confidence = score
        else:
            confidence = 0.0
        
        return {
            'action': action,
            'confidence': confidence,
            'reasons': reasons,
            'model_score': score
        }
    
    def decide(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a final trading decision based on features.
        
        Args:
            features: Dictionary of feature name -> value
            
        Returns:
            Decision dictionary with action, confidence, reasons, and model_score
        """
        # Get model prediction score
        score = self.predict_score(features)
        
        # Apply risk filters
        decision = self.apply_risk_filters(features, score)
        
        return decision


# Singleton instance and path tracking
_engine_instance = None
_engine_model_path = None


def get_engine(model_path: Optional[str] = None) -> DecisionEngine:
    """
    Get or create a singleton DecisionEngine instance.
    
    Args:
        model_path: Optional path to model artifact. If not provided, uses default.
        
    Returns:
        DecisionEngine instance
        
    Note:
        If model_path changes between calls, a new instance will be created.
    """
    global _engine_instance, _engine_model_path
    
    # Normalize model_path to handle None case
    if model_path is None:
        model_path = os.getenv('SIGNAL_MODEL_PATH', 'models/signal_model.pkl')
    
    # Create new instance if none exists or path has changed
    if _engine_instance is None or _engine_model_path != model_path:
        _engine_instance = DecisionEngine(model_path=model_path)
        _engine_model_path = model_path
    
    return _engine_instance
