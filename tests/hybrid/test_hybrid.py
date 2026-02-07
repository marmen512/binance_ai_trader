"""
Tests for hybrid decision engine.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from decision.hybrid_engine import (
    HybridDecisionEngine,
    Signal,
    SignalSource,
    HybridDecision
)


class TestHybridDecisionEngine:
    """Test hybrid decision engine."""
    
    def test_engine_creation(self):
        """Test engine can be created."""
        engine = HybridDecisionEngine()
        assert engine is not None
    
    def test_engine_decide_no_signals(self):
        """Test engine returns flat with no signals."""
        engine = HybridDecisionEngine()
        
        decision = engine.decide()
        
        assert decision.direction == "flat"
        assert decision.confidence == 0.0
    
    def test_engine_decide_single_long_signal(self):
        """Test engine with single long signal."""
        engine = HybridDecisionEngine()
        
        signal = Signal(
            source=SignalSource.OWN_MODEL,
            direction="long",
            confidence=0.8,
            strength=0.9
        )
        
        decision = engine.decide(own_model_signal=signal)
        
        assert decision.direction == "long"
        assert decision.confidence > 0
    
    def test_engine_decide_conflicting_signals(self):
        """Test engine with conflicting signals."""
        engine = HybridDecisionEngine()
        
        long_signal = Signal(
            source=SignalSource.OWN_MODEL,
            direction="long",
            confidence=0.7,
            strength=0.8
        )
        
        short_signal = Signal(
            source=SignalSource.COPY_VALIDATED,
            direction="short",
            confidence=0.6,
            strength=0.7
        )
        
        decision = engine.decide(
            own_model_signal=long_signal,
            copy_signal=short_signal
        )
        
        # Should pick one based on weights, or go flat if insufficient agreement
        assert decision.direction in ["long", "short", "flat"]
    
    def test_engine_decide_agreeing_signals(self):
        """Test engine with agreeing signals."""
        engine = HybridDecisionEngine()
        
        long_signal1 = Signal(
            source=SignalSource.OWN_MODEL,
            direction="long",
            confidence=0.7,
            strength=0.8
        )
        
        long_signal2 = Signal(
            source=SignalSource.COPY_VALIDATED,
            direction="long",
            confidence=0.6,
            strength=0.7
        )
        
        decision = engine.decide(
            own_model_signal=long_signal1,
            copy_signal=long_signal2
        )
        
        assert decision.direction == "long"
        assert decision.confidence > 0
    
    def test_engine_low_confidence_threshold(self):
        """Test engine respects confidence threshold."""
        engine = HybridDecisionEngine(min_confidence_threshold=0.9)
        
        signal = Signal(
            source=SignalSource.OWN_MODEL,
            direction="long",
            confidence=0.5,  # Low confidence
            strength=0.5
        )
        
        decision = engine.decide(own_model_signal=signal)
        
        # Should go flat due to low confidence
        assert decision.direction == "flat"
    
    def test_engine_update_weights(self):
        """Test engine can update weights."""
        engine = HybridDecisionEngine()
        
        initial_weight = engine.own_model_weight
        
        engine.update_weights(own_model_weight=0.6)
        
        # Weight should change (will be normalized)
        assert engine.own_model_weight != initial_weight
