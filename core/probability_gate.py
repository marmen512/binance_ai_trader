"""
Probability gate that filters signals based on confidence threshold.
"""


class ProbabilityGate:
    """
    Filters trading signals based on model probability threshold.
    """
    
    def __init__(self, min_probability=0.6):
        """
        Args:
            min_probability: Minimum probability to allow signal through
        """
        self.min_probability = min_probability
    
    def filter(self, signal, probability):
        """
        Filter signal based on probability threshold.
        
        Args:
            signal: Trading signal (BUY, SELL, HOLD)
            probability: Model confidence (0-1)
            
        Returns:
            Filtered signal (original or HOLD if below threshold)
        """
        if probability < self.min_probability:
            return 'HOLD'
        return signal
    
    def set_threshold(self, threshold):
        """
        Update probability threshold.
        """
        self.min_probability = threshold
