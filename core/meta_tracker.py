"""
EngineTracker — трекер ефективності різних движків.
"""


class EngineTracker:
    """
    Трекер для відстеження ефективності різних движків.
    Зберігає історію результатів для обчислення winrate.
    """

    def __init__(self, window=40):
        """
        Ініціалізація EngineTracker.

        Args:
            window (int): Розмір вікна для трекінгу (кількість трейдів)
        """
        self.window = window
        self.history = {}  # {engine_name: [results]}

    def add(self, name, pnl):
        """
        Додає результат трейду для движка.

        Args:
            name (str): Назва движка
            pnl (float): Прибуток/збиток від трейду
        """
        if name not in self.history:
            self.history[name] = []

        # Додаємо 1 для прибутку, 0 для збитку
        self.history[name].append(1 if pnl > 0 else 0)

        # Обмежуємо розмір вікна
        if len(self.history[name]) > self.window:
            self.history[name].pop(0)

    def score(self, name):
        """
        Обчислює winrate для движка.

        Args:
            name (str): Назва движка

        Returns:
            float: Winrate (0.0 - 1.0) або 0.5 якщо немає історії
        """
        if name not in self.history or len(self.history[name]) == 0:
            return 0.5  # Нейтральний скор за замовчуванням

        winrate = sum(self.history[name]) / len(self.history[name])
        return winrate
