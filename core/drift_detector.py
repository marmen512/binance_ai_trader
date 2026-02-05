"""
DriftDetector — виявляє дрифт моделі на основі останніх трейдів.
"""


class DriftDetector:
    """Детектор дрифту моделі на основі winrate."""

    def __init__(self, window=50, min_winrate=0.45):
        """
        Ініціалізація DriftDetector.

        Args:
            window (int): Розмір вікна для перевірки (кількість трейдів)
            min_winrate (float): Мінімальний допустимий winrate
        """
        self.window = window
        self.min_winrate = min_winrate
        self.trades = []

    def add_trade(self, pnl):
        """
        Додає результат трейду.

        Args:
            pnl (float): Прибуток/збиток від трейду
        """
        self.trades.append(1 if pnl > 0 else 0)
        if len(self.trades) > self.window:
            self.trades.pop(0)

    def drifted(self):
        """
        Перевіряє чи виявлено дрифт.

        Returns:
            bool: True якщо winrate нижче мінімального порогу
        """
        if len(self.trades) < self.window:
            return False

        winrate = sum(self.trades) / len(self.trades)
        return winrate < self.min_winrate
