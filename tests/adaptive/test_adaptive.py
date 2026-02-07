"""
Tests for shadow model and adaptive learning.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from adaptive.shadow_model import ShadowModel
from adaptive.online_trainer import OnlineTrainer
from adaptive.promotion_gate import PromotionGate, PromotionCriteria
from adaptive.drift_monitor import DriftMonitorV2


class TestShadowModel:
    """Test shadow model functionality."""
    
    def test_shadow_model_creation(self):
        """Test shadow model can be created."""
        model = ShadowModel()
        assert model is not None
        assert model.learn_count == 0
    
    def test_shadow_model_learn_one(self):
        """Test shadow model can learn from a single example."""
        model = ShadowModel()
        
        features = {"feature_1": 0.5, "feature_2": 0.7"}
        label = 1
        
        initial_count = model.learn_count
        model.learn_one(features, label)
        
        assert model.learn_count == initial_count + 1
    
    def test_shadow_model_predict(self):
        """Test shadow model can make predictions."""
        model = ShadowModel()
        
        features = {"feature_1": 0.5, "feature_2": 0.7}
        score = model.predict_proba(features)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestPromotionGate:
    """Test promotion gate functionality."""
    
    def test_promotion_gate_creation(self):
        """Test promotion gate can be created."""
        gate = PromotionGate()
        assert gate is not None
        assert isinstance(gate.criteria, PromotionCriteria)
    
    def test_promotion_gate_approve_good_metrics(self):
        """Test promotion gate approves good metrics."""
        gate = PromotionGate()
        
        shadow_metrics = {
            'winrate': 0.60,
            'expectancy': 0.5,
            'total_trades': 150,
            'loss_streak': 2,
            'drawdown_slope': -2.0
        }
        
        decision = gate.evaluate(shadow_metrics)
        
        assert decision.approved is True
        assert len(decision.reasons) > 0
    
    def test_promotion_gate_reject_low_winrate(self):
        """Test promotion gate rejects low winrate."""
        gate = PromotionGate()
        
        shadow_metrics = {
            'winrate': 0.40,  # Below threshold
            'expectancy': 0.5,
            'total_trades': 150,
            'loss_streak': 2,
            'drawdown_slope': -2.0
        }
        
        decision = gate.evaluate(shadow_metrics)
        
        assert decision.approved is False
        assert any('winrate' in r.lower() for r in decision.reasons)
    
    def test_promotion_gate_reject_insufficient_trades(self):
        """Test promotion gate rejects insufficient trades."""
        gate = PromotionGate()
        
        shadow_metrics = {
            'winrate': 0.60,
            'expectancy': 0.5,
            'total_trades': 50,  # Below threshold
            'loss_streak': 2,
            'drawdown_slope': -2.0
        }
        
        decision = gate.evaluate(shadow_metrics)
        
        assert decision.approved is False
        assert any('trade' in r.lower() for r in decision.reasons)


class TestDriftMonitor:
    """Test drift monitoring."""
    
    def test_drift_monitor_creation(self):
        """Test drift monitor can be created."""
        monitor = DriftMonitorV2(window_size=50)
        assert monitor is not None
    
    def test_drift_monitor_add_trade(self):
        """Test drift monitor can track trades."""
        monitor = DriftMonitorV2(window_size=50)
        
        monitor.add_trade(pnl=100.0, is_win=True)
        monitor.add_trade(pnl=-50.0, is_win=False)
        
        metrics = monitor.compute_metrics()
        
        assert metrics is not None
        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
    
    def test_drift_monitor_detect_drift(self):
        """Test drift monitor can detect drift."""
        monitor = DriftMonitorV2(window_size=50)
        
        # Add many losing trades to trigger drift
        for i in range(20):
            monitor.add_trade(pnl=-50.0, is_win=False)
        
        is_drifting, reasons = monitor.is_drifting(
            min_winrate=0.45,
            min_expectancy=0.0,
            max_loss_streak=5
        )
        
        assert is_drifting is True
        assert len(reasons) > 0
