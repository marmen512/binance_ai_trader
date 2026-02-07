"""
Confidence validator for copy trading decisions.

Validates confidence in replicating trader positions.
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class ConfidenceValidation:
    """Confidence validation result."""
    is_confident: bool
    confidence_score: float
    validation_reasons: list[str]
    risk_factors: list[str]
    recommendation: str  # REPLICATE/SKIP/REDUCE_SIZE


class ConfidenceValidator:
    """
    Validates confidence in copy trading decisions.
    
    This component feeds into decision layer, NOT execution.
    """
    
    def __init__(
        self,
        min_confidence: float = 0.7,
        min_trader_winrate: float = 0.55,
        max_risk_factors: int = 2
    ):
        """
        Initialize confidence validator.
        
        Args:
            min_confidence: Minimum confidence threshold
            min_trader_winrate: Minimum trader win rate
            max_risk_factors: Maximum acceptable risk factors
        """
        self.min_confidence = min_confidence
        self.min_trader_winrate = min_trader_winrate
        self.max_risk_factors = max_risk_factors
    
    def validate(
        self,
        trader_metrics: dict,
        entry_analysis: dict,
        market_conditions: Optional[dict] = None
    ) -> ConfidenceValidation:
        """
        Validate confidence in replicating a trade.
        
        Args:
            trader_metrics: Trader performance metrics
            entry_analysis: Entry quality analysis
            market_conditions: Optional market context
            
        Returns:
            ConfidenceValidation result
        """
        market_conditions = market_conditions or {}
        
        confidence_score = 0.0
        validation_reasons = []
        risk_factors = []
        
        # Trader performance validation
        winrate = trader_metrics.get("winrate", 0.0)
        if winrate >= self.min_trader_winrate:
            confidence_score += 0.3
            validation_reasons.append(f"GOOD_WINRATE: {winrate:.2%}")
        else:
            risk_factors.append(f"LOW_WINRATE: {winrate:.2%}")
        
        # ROI validation
        roi = trader_metrics.get("roi", 0.0)
        if roi > 0.15:
            confidence_score += 0.2
            validation_reasons.append(f"STRONG_ROI: {roi:.2%}")
        elif roi < 0.05:
            risk_factors.append(f"WEAK_ROI: {roi:.2%}")
        
        # Entry quality validation
        entry_quality = entry_analysis.get("entry_quality_score", 0.0)
        if entry_quality > 0.7:
            confidence_score += 0.3
            validation_reasons.append(f"STRONG_ENTRY: {entry_quality:.2f}")
        elif entry_quality < 0.4:
            risk_factors.append(f"WEAK_ENTRY: {entry_quality:.2f}")
        
        # Market conditions validation
        volatility = market_conditions.get("volatility", 0.5)
        if volatility > 0.8:
            risk_factors.append(f"HIGH_VOLATILITY: {volatility:.2f}")
        else:
            confidence_score += 0.2
            validation_reasons.append("STABLE_MARKET")
        
        # Determine recommendation
        is_confident = (
            confidence_score >= self.min_confidence and
            len(risk_factors) <= self.max_risk_factors
        )
        
        if is_confident and confidence_score > 0.8:
            recommendation = "REPLICATE"
        elif is_confident:
            recommendation = "REDUCE_SIZE"
        else:
            recommendation = "SKIP"
        
        return ConfidenceValidation(
            is_confident=is_confident,
            confidence_score=confidence_score,
            validation_reasons=validation_reasons,
            risk_factors=risk_factors,
            recommendation=recommendation
        )
    
    def batch_validate(
        self,
        trades: list[dict]
    ) -> list[ConfidenceValidation]:
        """
        Validate multiple trades.
        
        Args:
            trades: List of trade data dictionaries
            
        Returns:
            List of validation results
        """
        results = []
        
        for trade in trades:
            validation = self.validate(
                trader_metrics=trade.get("trader_metrics", {}),
                entry_analysis=trade.get("entry_analysis", {}),
                market_conditions=trade.get("market_conditions", {})
            )
            results.append(validation)
        
        return results
