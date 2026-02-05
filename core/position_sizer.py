"""
PositionSizer - розрахунок розміру позиції на основі волатильності.
"""


def compute_position_size(balance: float, vol: float, risk_pct: float = 0.01) -> float:
    """
    Обчислює розмір позиції на основі балансу, волатильності та рівня ризику.
    
    Args:
        balance: поточний баланс рахунку
        vol: волатильність (std returns)
        risk_pct: відсоток ризику від балансу (default=0.01 = 1%)
        
    Returns:
        float: розмір позиції в валюті балансу
    """
    if vol <= 0:
        return balance * risk_pct
    
    # Розмір на основі волатильності
    size = balance * risk_pct / (vol * 12)
    
    # Обмеження
    min_size = balance * 0.003
    max_size = balance * 0.05
    
    size = max(min_size, min(size, max_size))
    
    return size
