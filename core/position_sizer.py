"""
Position sizer that determines trade size based on confidence and risk parameters.
"""


class PositionSizer:
    """
    Calculates position size based on probability and account parameters.
    """
    
    def __init__(self, base_size=0.1, max_size=0.3, min_prob=0.6):
        """
        Args:
            base_size: Base position size as fraction of equity (0-1)
            max_size: Maximum position size as fraction of equity (0-1)
            min_prob: Minimum probability for any position
        """
        self.base_size = base_size
        self.max_size = max_size
        self.min_prob = min_prob
    
    def calculate_size(self, probability, equity):
        """
        Calculate position size.
        
        Args:
            probability: Model confidence (0-1)
            equity: Current account equity
            
        Returns:
            Position size in base currency
        """
        if probability < self.min_prob:
            return 0
        
        # Scale position size linearly with probability
        # At min_prob: base_size
        # At 1.0: max_size
        prob_range = 1.0 - self.min_prob
        scaled_prob = (probability - self.min_prob) / prob_range
        size_fraction = self.base_size + (self.max_size - self.base_size) * scaled_prob
        
        return equity * size_fraction
