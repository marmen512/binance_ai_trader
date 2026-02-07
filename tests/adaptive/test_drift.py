"""Tests for Drift Detection - Phase 8"""

import pytest
import numpy as np

from adaptive.drift_monitor_simple import DriftMonitor


class TestDriftMonitor:
    """Test drift detection"""
    
    def test_drift_detection_triggers(self):
        """Test that drift detection triggers when winrate drops"""
        monitor = DriftMonitor(window=10, min_winrate=0.50)
        
        # Add winning trades (no drift)
        for i in range(10):
            monitor.add(10.0)  # All wins
        
        assert not monitor.drifted()
        
        # Now add losing trades
        for i in range(10):
            monitor.add(-10.0)  # All losses
        
        # Should detect drift (winrate = 0% < 50%)
        assert monitor.drifted()
    
    def test_not_enough_history(self):
        """Test that drift check requires minimum history"""
        monitor = DriftMonitor(window=50, min_winrate=0.45)
        
        # Add only 20 trades
        for i in range(20):
            monitor.add(-10.0)  # All losses
        
        # Should not detect drift yet (not enough history)
        assert not monitor.drifted()
    
    def test_winrate_calculation(self):
        """Test winrate calculation"""
        monitor = DriftMonitor(window=10, min_winrate=0.50)
        
        # Add 6 wins and 4 losses (60% winrate)
        for i in range(6):
            monitor.add(10.0)
        for i in range(4):
            monitor.add(-10.0)
        
        stats = monitor.get_stats()
        
        assert stats["winrate"] == 0.6
        assert not stats["drifted"]
    
    def test_rolling_window(self):
        """Test that only last N trades are considered"""
        monitor = DriftMonitor(window=5, min_winrate=0.50)
        
        # Add 10 wins (old history)
        for i in range(10):
            monitor.add(10.0)
        
        # Add 5 losses (recent history)
        for i in range(5):
            monitor.add(-10.0)
        
        # Should detect drift based on last 5 trades only
        assert monitor.drifted()
    
    def test_get_stats(self):
        """Test getting drift statistics"""
        monitor = DriftMonitor(window=10, min_winrate=0.45)
        
        # Add 7 wins and 3 losses
        for i in range(7):
            monitor.add(10.0)
        for i in range(3):
            monitor.add(-5.0)
        
        stats = monitor.get_stats()
        
        assert stats["total_trades"] == 10
        assert stats["window_size"] == 10
        assert stats["winrate"] == 0.7
        assert stats["min_winrate"] == 0.45
        assert not stats["drifted"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
