"""
Position Sizer
Volatility-based position sizing
"""
import numpy as np


class PositionSizer:
    """Compute position size based on volatility and account balance"""
    
    def __init__(self, base_risk=0.02, max_position_pct=0.5):
        """
        Initialize position sizer
        
        Args:
            base_risk: Base risk per trade as fraction of balance (default 0.02 = 2%)
            max_position_pct: Maximum position size as fraction of balance (default 0.5 = 50%)
        """
        self.base_risk = base_risk
        self.max_position_pct = max_position_pct
    
    def compute_position_size(self, df, balance, regime=None):
        """
        Compute position size based on volatility
        
        Args:
            df: DataFrame with OHLCV data and features
            balance: Current account balance
            regime: Optional market regime for adjustment
            
        Returns:
            Position size in currency units
        """
        # Calculate recent volatility
        if 'vol10' in df.columns:
            volatility = df['vol10'].iloc[-1]
        else:
            returns = df['close'].pct_change()
            volatility = returns.iloc[-10:].std()
        
        # Base position size
        position_size = balance * self.base_risk
        
        # Adjust for volatility (inverse relationship)
        # Higher volatility = smaller position
        if volatility > 0:
            vol_adjustment = 1.0 / (1.0 + volatility * 10)
            position_size *= vol_adjustment
        
        # Regime adjustment
        if regime == "VOLATILE":
            position_size *= 0.5  # Reduce size in volatile markets
        elif regime == "TREND":
            position_size *= 1.2  # Increase size in trending markets
        
        # Cap at maximum position size
        max_position = balance * self.max_position_pct
        position_size = min(position_size, max_position)
        
        return position_size
