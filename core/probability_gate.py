"""
ProbabilityGate - фільтрація сигналів за порогом ймовірності залежно від режиму.
"""


def pass_probability(prob: float, regime: str) -> bool:
    """
    Перевіряє, чи проходить ймовірність поріг для даного режиму.
    
    Args:
        prob: ймовірність сигналу (0-1)
        regime: режим ринку ('TREND', 'RANGE', 'VOLATILE')
        
    Returns:
        bool: True якщо prob >= порогу для режиму
    """
    thresholds = {
        'TREND': 0.58,
        'RANGE': 0.66,
        'VOLATILE': 0.72
    }
    
    threshold = thresholds.get(regime, 0.66)
    return prob >= threshold
