"""
Калькулятор розміру позиції на основі волатильності та ризику.
"""


def compute_position_size(balance: float, volatility: float, risk_pct: float = 0.01,
                          min_position_pct: float = 0.05, max_position_pct: float = 0.3) -> float:
    """
    Обчислює розмір позиції на основі волатильності.
    
    Args:
        balance: Баланс рахунку
        volatility: Поточна волатильність (std returns)
        risk_pct: Відсоток ризику на угоду (напр., 0.01 = 1%)
        min_position_pct: Мінімальний розмір позиції від балансу
        max_position_pct: Максимальний розмір позиції від балансу
        
    Returns:
        Розмір позиції у валюті балансу
    """
    # Формула: size = balance * risk_pct / (volatility * factor)
    # factor=12 для нормалізації волатильності до денного рівня
    if volatility <= 0:
        volatility = 0.001  # Мінімальна волатильність
    
    size = balance * risk_pct / (volatility * 12)
    
    # Обмеження розміру позиції
    min_size = balance * min_position_pct
    max_size = balance * max_position_pct
    
    size = max(min_size, min(size, max_size))
    
    return size
