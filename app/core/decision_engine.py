"""
Decision engine for trading signals.

Loads trained models and applies risk filters to generate trading decisions.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class TradingDecision:
    """Represents a trading decision with confidence and reasoning."""
    action: str  # 'BUY', 'SELL', 'HOLD'
    confidence: float
    model_score: float
    reasons: list[str]


class DecisionEngine:
    """
    Decision engine that loads a trained model and applies risk filters
    to generate trading signals.
    """
    
    def __init__(self, model_path: str | Path):
        """
        Initialize the decision engine.
        
        Args:
            model_path: Path to the serialized model artifact (.pkl file)
        """
        self.model_path = Path(model_path)
        self._model = None
        self._preprocessor = None
        self._feature_names = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the model artifact from disk."""
        try:
            import joblib
        except ImportError:
            raise ImportError("joblib is required. Install it with: pip install joblib")
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at: {self.model_path}")
        
        artifact = joblib.load(self.model_path)
        
        # Handle both bare model and dict format
        if isinstance(artifact, dict):
            self._model = artifact.get('model')
            self._preprocessor = artifact.get('preprocessor')
            self._feature_names = artifact.get('feature_names', [])
            
            if self._model is None:
                raise ValueError("Model artifact dict must contain 'model' key")
        else:
            # Bare model
            self._model = artifact
            self._preprocessor = None
            self._feature_names = []
    
    def predict_score(self, features: dict[str, float]) -> float:
        """
        Predict a score for the given features.
        
        Args:
            features: Dictionary of feature name -> value
        
        Returns:
            Float score representing model confidence (0-1 for probability)
        """
        # Build DataFrame row
        if self._feature_names:
            # Use saved feature order
            feature_values = [features.get(name, 0.0) for name in self._feature_names]
            df = pd.DataFrame([feature_values], columns=self._feature_names)
        else:
            # Use features dict directly
            df = pd.DataFrame([features])
        
        # Apply preprocessor if present
        if self._preprocessor is not None:
            X = self._preprocessor.transform(df)
        else:
            X = df.values
        
        # Get prediction probabilities if available
        if hasattr(self._model, 'predict_proba'):
            proba = self._model.predict_proba(X)[0]
            # For multi-class: return max probability
            # This represents confidence in the predicted class
            score = float(np.max(proba))
        else:
            # Fall back to predict if no predict_proba
            pred = self._model.predict(X)[0]
            score = float(pred)
        
        return score
    
    def apply_risk_filters(
        self,
        features: dict[str, float],
        min_confidence: float = 0.5,
        volatility_max: float = 0.05,
        max_spread_pct: float = 0.01
    ) -> TradingDecision:
        """
        Apply risk filters and generate a trading decision.
        
        Args:
            features: Dictionary of feature values
            min_confidence: Minimum confidence threshold for BUY/SELL
            volatility_max: Maximum allowed volatility
            max_spread_pct: Maximum allowed spread
        
        Returns:
            TradingDecision with action, confidence, and reasons
        """
        reasons = []
        
        # Get model prediction
        if self._feature_names:
            feature_values = [features.get(name, 0.0) for name in self._feature_names]
            df = pd.DataFrame([feature_values], columns=self._feature_names)
        else:
            df = pd.DataFrame([features])
        
        if self._preprocessor is not None:
            X = self._preprocessor.transform(df)
        else:
            X = df.values
        
        # Get probabilities for multi-class
        if hasattr(self._model, 'predict_proba'):
            proba = self._model.predict_proba(X)[0]
            pred_class = self._model.predict(X)[0]
            max_prob = float(np.max(proba))
            
            # Assume classes are in order: -1 (SELL), 0 (HOLD), 1 (BUY)
            # or for binary: 0 (negative/SELL), 1 (positive/BUY)
            if len(proba) == 3:
                # Multi-class: -1, 0, 1
                class_idx = int(pred_class) + 1  # Convert -1,0,1 to 0,1,2
                if class_idx < 0 or class_idx >= 3:
                    # Handle edge case: use argmax
                    class_idx = int(np.argmax(proba))
                confidence = float(proba[class_idx])
            else:
                # Binary or other: use max probability
                confidence = max_prob
        else:
            pred_class = self._model.predict(X)[0]
            confidence = 0.5  # No probability available
        
        model_score = confidence
        
        # Determine base action from prediction
        if pred_class == 1:
            base_action = 'BUY'
        elif pred_class == -1:
            base_action = 'SELL'
        else:
            base_action = 'HOLD'
        
        # Apply risk filters
        action = base_action
        
        # Check confidence threshold
        if confidence < min_confidence and base_action != 'HOLD':
            action = 'HOLD'
            reasons.append(f'Low confidence: {confidence:.3f} < {min_confidence}')
        
        # Check volatility
        volatility = features.get('volatility_30', features.get('volatility_10', 0.0))
        if volatility > volatility_max and base_action != 'HOLD':
            action = 'HOLD'
            reasons.append(f'High volatility: {volatility:.4f} > {volatility_max}')
        
        # Check spread
        spread = features.get('high_low_spread', 0.0)
        if spread > max_spread_pct and base_action != 'HOLD':
            action = 'HOLD'
            reasons.append(f'Wide spread: {spread:.4f} > {max_spread_pct}')
        
        if action == base_action and base_action != 'HOLD':
            reasons.append(f'Model predicts {base_action} with confidence {confidence:.3f}')
        elif action == 'HOLD' and not reasons:
            reasons.append('Model predicts HOLD')
        
        return TradingDecision(
            action=action,
            confidence=confidence,
            model_score=model_score,
            reasons=reasons
        )


# Singleton instance
_engine_instance: DecisionEngine | None = None


def get_engine(model_path: str | Path | None = None) -> DecisionEngine:
    """
    Get or create a singleton DecisionEngine instance.
    
    Args:
        model_path: Path to model artifact. Required on first call.
    
    Returns:
        DecisionEngine instance
    """
    global _engine_instance
    
    if _engine_instance is None:
        if model_path is None:
            # Try default path
            default_path = Path("models/signal_model.pkl")
            if default_path.exists():
                model_path = default_path
            else:
                raise ValueError("model_path required on first call to get_engine()")
        _engine_instance = DecisionEngine(model_path)
    
    return _engine_instance
