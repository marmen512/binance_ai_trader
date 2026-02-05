"""
probability_gate — перевіряє чи проходить ймовірність поріг для даного режиму.
"""


def pass_probability(prob, regime):
    """
    Перевіряє чи проходить ймовірність поріг для поточного режиму.

    Args:
        prob (float): Ймовірність сигналу (0.0 - 1.0)
        regime (str): Режим ринку ('TREND', 'RANGE', 'VOLATILE')

    Returns:
        bool: True якщо ймовірність достатня для режиму
    """
    thresholds = {
        'TREND': 0.58,
        'RANGE': 0.66,
        'VOLATILE': 0.72
    }

    threshold = thresholds.get(regime, 0.66)
    return prob >= threshold
