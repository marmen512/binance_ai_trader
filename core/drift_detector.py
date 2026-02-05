"""
Drift detector that monitors recent trade PnL to signal when performance degrades.
"""
from collections import deque


class DriftDetector:
    """
    Tracks recent trade PnL and signals drift when win rate over sliding window
    falls below threshold.
    """
    
    def __init__(self, window_size=50, winrate_threshold=0.45):
        """
        Args:
            window_size: Number of recent trades to track
            winrate_threshold: Minimum win rate before signaling drift
        """
        self.window_size = window_size
        self.winrate_threshold = winrate_threshold
        self.trades = deque(maxlen=window_size)
        self._drifted = False
    
    def add_trade(self, pnl):
        """
        Add a trade result.
        
        Args:
            pnl: Profit/loss of the trade (positive = win, negative = loss)
        """
        self.trades.append(pnl)
        
        # Check if we have enough trades and calculate win rate
        if len(self.trades) >= self.window_size:
            wins = sum(1 for p in self.trades if p > 0)
            winrate = wins / len(self.trades)
            self._drifted = winrate < self.winrate_threshold
    
    def drifted(self):
        """
        Returns True if drift has been detected.
        """
        return self._drifted
    
    def reset(self):
        """
        Reset drift detector state.
        """
        self.trades.clear()
        self._drifted = False
    
    def get_stats(self):
        """
        Get current statistics.
        """
        if len(self.trades) == 0:
            return {"trades": 0, "winrate": 0.0, "drifted": False}
        
        wins = sum(1 for p in self.trades if p > 0)
        winrate = wins / len(self.trades)
        return {
            "trades": len(self.trades),
            "winrate": winrate,
            "drifted": self._drifted,
            "threshold": self.winrate_threshold
        }
