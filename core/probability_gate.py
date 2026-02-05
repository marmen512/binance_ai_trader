"""
Probability Gate
Regime-specific probability thresholds for signal filtering
"""


class ProbabilityGate:
    """Apply regime-specific probability thresholds"""
    
    def __init__(self, thresholds=None):
        """
        Initialize probability gate
        
        Args:
            thresholds: Dict mapping regime to min probability threshold
                       Default: {"VOLATILE": 0.65, "TREND": 0.55, "RANGE": 0.60}
        """
        if thresholds is None:
            thresholds = {
                "VOLATILE": 0.65,
                "TREND": 0.55,
                "RANGE": 0.60
            }
        self.thresholds = thresholds
    
    def pass_probability(self, signal, confidence, regime):
        """
        Check if signal passes probability threshold for regime
        
        Args:
            signal: Trading signal ("BUY", "SELL", "HOLD")
            confidence: Signal confidence (0-1)
            regime: Market regime ("VOLATILE", "TREND", "RANGE")
            
        Returns:
            Tuple of (passed, filtered_signal) where:
                passed: Boolean indicating if threshold passed
                filtered_signal: Original signal if passed, "HOLD" otherwise
        """
        threshold = self.thresholds.get(regime, 0.60)
        
        if confidence >= threshold:
            return True, signal
        else:
            return False, "HOLD"
