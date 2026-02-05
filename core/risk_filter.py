"""
Фільтр ризиків для перевірки сигналів.
Застосовує обмеження на волатильність та впевненість моделі.
"""


def risk_filter(signal: str, prob: float, volatility: float, 
                max_volatility: float = 0.03, min_prob: float = 0.6) -> bool:
    """
    Фільтрує сигнали на основі ризику.
    
    Args:
        signal: Торговий сигнал ('BUY', 'SELL', 'HOLD')
        prob: Ймовірність/впевненість моделі
        volatility: Поточна волатильність
        max_volatility: Максимальна допустима волатильність
        min_prob: Мінімальна допустима впевненість
        
    Returns:
        True якщо сигнал проходить фільтр, False інакше
    """
    # Пропускаємо HOLD без перевірок
    if signal == 'HOLD':
        return True
    
    # Перевірка волатильності
    if volatility > max_volatility:
        return False
    
    # Перевірка впевненості
    if prob < min_prob:
        return False
    
    return True
