"""
DriftDetector - детектор дрейфу моделі.
"""


class DriftDetector:
    """
    Відстежує дрейф моделі на основі останніх результатів трейдів.
    """
    
    def __init__(self, window: int = 50, min_winrate: float = 0.45):
        """
        Args:
            window: розмір вікна для відстеження (кількість останніх трейдів)
            min_winrate: мінімальний прийнятний winrate (default=0.45)
        """
        self.window = window
        self.min_winrate = min_winrate
        self.recent_trades = []
    
    def add_trade(self, pnl: float):
        """
        Додає результат трейду.
        
        Args:
            pnl: profit/loss трейду
        """
        self.recent_trades.append(pnl)
        
        # Зберігаємо тільки останні window трейдів
        if len(self.recent_trades) > self.window:
            self.recent_trades = self.recent_trades[-self.window:]
    
    def drifted(self) -> bool:
        """
        Перевіряє, чи виявлено дрейф.
        
        Returns:
            bool: True якщо виявлено дрейф (winrate нижче порогу)
        """
        if len(self.recent_trades) < self.window:
            return False
        
        # Обчислюємо winrate останніх трейдів
        wins = sum(1 for pnl in self.recent_trades if pnl > 0)
        winrate = wins / len(self.recent_trades)
        
        return winrate < self.min_winrate
