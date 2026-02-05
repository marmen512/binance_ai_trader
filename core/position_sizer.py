"""
position_sizer — обчислює розмір позиції на основі балансу, волатильності та ризику.
"""


def compute_position_size(balance, vol, risk_pct=0.01):
    """
    Обчислює розмір позиції з урахуванням волатильності та ризику.

    Args:
        balance (float): Поточний баланс
        vol (float): Волатильність (стандартне відхилення)
        risk_pct (float): Відсоток ризику від балансу (за замовчуванням 0.01 = 1%)

    Returns:
        float: Розмір позиції
    """
    if vol <= 0:
        return balance * risk_pct

    # Формула: розмір = баланс * ризик% / (волатильність * множник)
    size = balance * risk_pct / (vol * 12)

    # Обмеження: мінімум та максимум
    min_size = balance * 0.003
    max_size = balance * 0.05

    size = max(min_size, min(size, max_size))

    return size
