"""
Simple Risk Filter
Basic risk filtering logic
"""


def risk_filter(signal, confidence, balance, position_size):
    """
    Apply risk filter to trading signal
    
    Args:
        signal: Trading signal ("BUY", "SELL", "HOLD")
        confidence: Signal confidence (0-1)
        balance: Current account balance
        position_size: Proposed position size
        
    Returns:
        Tuple of (filtered_signal, filtered_position_size)
    """
    # Simple risk checks
    
    # Check minimum confidence
    if confidence < 0.5:
        return "HOLD", 0
    
    # Check minimum balance
    if balance < 100:
        return "HOLD", 0
    
    # Limit position size to 90% of balance
    max_position = balance * 0.9
    filtered_position_size = min(position_size, max_position)
    
    return signal, filtered_position_size
