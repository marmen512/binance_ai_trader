"""
Hybrid decision engine for signal fusion.

Combines multiple signal sources using confidence weighting, voting,
and conflict resolution to produce a final trading decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal
from datetime import datetime, timezone
from enum import Enum


class SignalSource(Enum):
    """Sources of trading signals."""
    OWN_MODEL = "own_model"
    COPY_VALIDATED = "copy_validated"
    REGIME_MODEL = "regime_model"
    HYBRID = "hybrid"


@dataclass
class Signal:
    """
    Trading signal from a source.
    
    Attributes:
        source: Signal source
        direction: Signal direction (long/short/flat)
        confidence: Confidence score (0.0 to 1.0)
        strength: Signal strength (0.0 to 1.0)
        metadata: Optional metadata
    """
    source: SignalSource
    direction: Literal["long", "short", "flat"]
    confidence: float
    strength: float
    metadata: Optional[dict] = None


@dataclass
class HybridDecision:
    """
    Final hybrid decision after signal fusion.
    
    Attributes:
        direction: Final direction
        confidence: Final confidence score
        strength: Final signal strength
        contributing_signals: Signals that contributed to decision
        reasoning: Explanation of decision
        timestamp: Decision timestamp
    """
    direction: Literal["long", "short", "flat"]
    confidence: float
    strength: float
    contributing_signals: list[Signal]
    reasoning: str
    timestamp: str


class HybridDecisionEngine:
    """
    Hybrid decision engine that fuses multiple signal sources.
    
    Uses confidence weighting, voting, and conflict resolution to
    combine signals from own model, copy-trader validation, and regime model.
    """
    
    def __init__(
        self,
        own_model_weight: float = 0.4,
        copy_weight: float = 0.3,
        regime_weight: float = 0.3,
        min_confidence_threshold: float = 0.6,
        min_agreement_ratio: float = 0.5
    ):
        """
        Initialize hybrid decision engine.
        
        Args:
            own_model_weight: Weight for own model signals
            copy_weight: Weight for copy-validated signals
            regime_weight: Weight for regime model signals
            min_confidence_threshold: Minimum confidence to act
            min_agreement_ratio: Minimum ratio of agreeing signals
        """
        self.own_model_weight = own_model_weight
        self.copy_weight = copy_weight
        self.regime_weight = regime_weight
        self.min_confidence_threshold = min_confidence_threshold
        self.min_agreement_ratio = min_agreement_ratio
        
        # Normalize weights
        total_weight = own_model_weight + copy_weight + regime_weight
        if total_weight > 0:
            self.own_model_weight /= total_weight
            self.copy_weight /= total_weight
            self.regime_weight /= total_weight
    
    def decide(
        self,
        own_model_signal: Optional[Signal] = None,
        copy_signal: Optional[Signal] = None,
        regime_signal: Optional[Signal] = None
    ) -> HybridDecision:
        """
        Make a hybrid decision from multiple signals.
        
        Args:
            own_model_signal: Signal from own trading model
            copy_signal: Signal from copy-trader validation
            regime_signal: Signal from regime model
            
        Returns:
            HybridDecision with fused signal
        """
        signals = []
        if own_model_signal:
            signals.append(own_model_signal)
        if copy_signal:
            signals.append(copy_signal)
        if regime_signal:
            signals.append(regime_signal)
        
        # If no signals, return flat
        if not signals:
            return HybridDecision(
                direction="flat",
                confidence=0.0,
                strength=0.0,
                contributing_signals=[],
                reasoning="No signals available",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        # Calculate weighted scores for each direction
        long_score = 0.0
        short_score = 0.0
        flat_score = 0.0
        
        for signal in signals:
            weight = self._get_weight(signal.source)
            weighted_confidence = signal.confidence * signal.strength * weight
            
            if signal.direction == "long":
                long_score += weighted_confidence
            elif signal.direction == "short":
                short_score += weighted_confidence
            elif signal.direction == "flat":
                flat_score += weighted_confidence
        
        # Determine final direction based on highest score
        max_score = max(long_score, short_score, flat_score)
        
        if max_score == long_score:
            direction = "long"
            final_score = long_score
        elif max_score == short_score:
            direction = "short"
            final_score = short_score
        else:
            direction = "flat"
            final_score = flat_score
        
        # Check agreement ratio
        agreeing_signals = [s for s in signals if s.direction == direction]
        agreement_ratio = len(agreeing_signals) / len(signals) if signals else 0
        
        # Generate reasoning
        reasoning_parts = []
        
        if agreement_ratio < self.min_agreement_ratio:
            direction = "flat"
            final_score = 0.0
            reasoning_parts.append(f"Insufficient agreement: {agreement_ratio:.1%} < {self.min_agreement_ratio:.1%}")
        elif final_score < self.min_confidence_threshold:
            direction = "flat"
            final_score = 0.0
            reasoning_parts.append(f"Low confidence: {final_score:.3f} < {self.min_confidence_threshold}")
        else:
            reasoning_parts.append(f"{direction.upper()} signal with {agreement_ratio:.1%} agreement")
            reasoning_parts.append(f"Contributing: {', '.join(s.source.value for s in agreeing_signals)}")
        
        # Add signal details
        if own_model_signal:
            reasoning_parts.append(
                f"Own model: {own_model_signal.direction} "
                f"(conf={own_model_signal.confidence:.2f})"
            )
        if copy_signal:
            reasoning_parts.append(
                f"Copy: {copy_signal.direction} "
                f"(conf={copy_signal.confidence:.2f})"
            )
        if regime_signal:
            reasoning_parts.append(
                f"Regime: {regime_signal.direction} "
                f"(conf={regime_signal.confidence:.2f})"
            )
        
        reasoning = " | ".join(reasoning_parts)
        
        return HybridDecision(
            direction=direction,
            confidence=final_score,
            strength=final_score,  # Could be different if needed
            contributing_signals=agreeing_signals if direction != "flat" else signals,
            reasoning=reasoning,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
    
    def _get_weight(self, source: SignalSource) -> float:
        """Get weight for a signal source."""
        if source == SignalSource.OWN_MODEL:
            return self.own_model_weight
        elif source == SignalSource.COPY_VALIDATED:
            return self.copy_weight
        elif source == SignalSource.REGIME_MODEL:
            return self.regime_weight
        else:
            return 0.0
    
    def update_weights(
        self,
        own_model_weight: Optional[float] = None,
        copy_weight: Optional[float] = None,
        regime_weight: Optional[float] = None
    ) -> None:
        """
        Update signal source weights.
        
        Args:
            own_model_weight: New weight for own model
            copy_weight: New weight for copy signals
            regime_weight: New weight for regime model
        """
        if own_model_weight is not None:
            self.own_model_weight = own_model_weight
        if copy_weight is not None:
            self.copy_weight = copy_weight
        if regime_weight is not None:
            self.regime_weight = regime_weight
        
        # Normalize weights
        total_weight = self.own_model_weight + self.copy_weight + self.regime_weight
        if total_weight > 0:
            self.own_model_weight /= total_weight
            self.copy_weight /= total_weight
            self.regime_weight /= total_weight
