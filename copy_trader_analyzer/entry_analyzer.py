"""
Entry analyzer for copy trading.

Analyzes trade entry conditions and timing.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EntryAnalysis:
    """Analysis of trade entry."""
    trade_id: str
    symbol: str
    entry_price: float
    entry_time: str
    market_volatility: float
    liquidity_score: float
    trend_alignment: float
    entry_quality_score: float
    recommendations: list[str]


class EntryAnalyzer:
    """
    Analyzes trade entry quality.
    
    This component is for ANALYSIS only, not execution.
    Connected to decision layer for insights.
    """
    
    def __init__(self):
        """Initialize entry analyzer."""
        pass
    
    def analyze_entry(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        entry_time: str,
        market_data: Optional[dict] = None
    ) -> EntryAnalysis:
        """
        Analyze trade entry quality.
        
        Args:
            symbol: Trading symbol
            side: Trade side (LONG/SHORT)
            entry_price: Entry price
            entry_time: Entry timestamp
            market_data: Optional market context data
            
        Returns:
            EntryAnalysis with quality metrics
        """
        market_data = market_data or {}
        
        # Placeholder calculations
        # In production, would use real market data
        
        volatility = market_data.get("volatility", 0.5)
        liquidity = market_data.get("liquidity_score", 0.7)
        trend = market_data.get("trend_strength", 0.6)
        
        # Calculate entry quality score
        quality_score = (
            volatility * 0.3 +
            liquidity * 0.4 +
            trend * 0.3
        )
        
        recommendations = []
        
        if volatility > 0.8:
            recommendations.append("HIGH_VOLATILITY: Consider reduced position size")
        
        if liquidity < 0.5:
            recommendations.append("LOW_LIQUIDITY: Entry may have slippage")
        
        if trend < 0.4:
            recommendations.append("WEAK_TREND: Counter-trend entry detected")
        
        if quality_score > 0.7:
            recommendations.append("STRONG_ENTRY: All conditions favorable")
        
        return EntryAnalysis(
            trade_id=f"{symbol}_{entry_time}",
            symbol=symbol,
            entry_price=entry_price,
            entry_time=entry_time,
            market_volatility=volatility,
            liquidity_score=liquidity,
            trend_alignment=trend,
            entry_quality_score=quality_score,
            recommendations=recommendations
        )
    
    def compare_entries(
        self,
        entries: list[EntryAnalysis]
    ) -> dict:
        """
        Compare multiple entry analyses.
        
        Args:
            entries: List of entry analyses
            
        Returns:
            Comparison statistics
        """
        if not entries:
            return {}
        
        quality_scores = [e.entry_quality_score for e in entries]
        
        return {
            "avg_quality": sum(quality_scores) / len(quality_scores),
            "max_quality": max(quality_scores),
            "min_quality": min(quality_scores),
            "good_entries": sum(1 for s in quality_scores if s > 0.7),
            "poor_entries": sum(1 for s in quality_scores if s < 0.4)
        }
