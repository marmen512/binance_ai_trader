"""Drift Monitor - Phase 5 (Simplified)

Monitor shadow model performance with rolling window.
Detect degradation via winrate threshold.
"""

import logging

logger = logging.getLogger(__name__)


class DriftMonitor:
    """
    Simple drift monitor using rolling window winrate.
    
    Detects when shadow model performance degrades below threshold.
    """
    
    def __init__(self, window=50, min_winrate=0.45):
        """
        Initialize drift monitor.
        
        Args:
            window: Size of rolling window for drift detection
            min_winrate: Minimum winrate threshold (0.45 = 45%)
        """
        self.window = window
        self.min_winrate = min_winrate
        self.hist = []
        logger.info(f"DriftMonitor initialized: window={window}, min_winrate={min_winrate}")
    
    def add(self, pnl):
        """
        Add a trade result to history.
        
        Args:
            pnl: Profit/loss of trade
        """
        self.hist.append(pnl)
        logger.debug(f"Added PnL to history: {pnl} (total: {len(self.hist)} trades)")
    
    def drifted(self):
        """
        Check if shadow model has drifted.
        
        Returns:
            True if winrate below threshold, False otherwise
        """
        if len(self.hist) < self.window:
            logger.debug(f"Not enough history for drift check: {len(self.hist)}/{self.window}")
            return False
        
        # Get last N trades
        last = self.hist[-self.window:]
        
        # Calculate winrate
        wins = [x for x in last if x > 0]
        winrate = len(wins) / len(last)
        
        has_drifted = winrate < self.min_winrate
        
        if has_drifted:
            logger.warning(f"DRIFT DETECTED: winrate={winrate:.3f} < threshold={self.min_winrate}")
        else:
            logger.debug(f"No drift: winrate={winrate:.3f}")
        
        return has_drifted
    
    def get_stats(self):
        """
        Get current drift monitor statistics.
        
        Returns:
            Dictionary with drift statistics
        """
        if len(self.hist) < self.window:
            return {
                "total_trades": len(self.hist),
                "window_size": self.window,
                "winrate": None,
                "drifted": False,
            }
        
        last = self.hist[-self.window:]
        wins = [x for x in last if x > 0]
        winrate = len(wins) / len(last)
        
        return {
            "total_trades": len(self.hist),
            "window_size": self.window,
            "winrate": winrate,
            "min_winrate": self.min_winrate,
            "drifted": winrate < self.min_winrate,
        }
