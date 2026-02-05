"""
EngineTracker - відстеження ефективності різних двигунів.
"""


class EngineTracker:
    """
    Відстежує ефективність декількох двигунів та вибирає найкращий.
    """
    
    def __init__(self, engine_names):
        """
        Args:
            engine_names: список назв двигунів
        """
        self.engine_names = engine_names
        self.scores = {name: 1.0 for name in engine_names}
        self.trade_counts = {name: 0 for name in engine_names}
        self.win_counts = {name: 0 for name in engine_names}
    
    def update(self, engine_name: str, pnl: float):
        """
        Оновлює статистику двигуна після трейду.
        
        Args:
            engine_name: назва двигуна
            pnl: profit/loss трейду
        """
        if engine_name not in self.scores:
            return
        
        self.trade_counts[engine_name] += 1
        
        if pnl > 0:
            self.win_counts[engine_name] += 1
            self.scores[engine_name] += 0.1  # Збільшуємо скор за виграш
        else:
            self.scores[engine_name] = max(0.1, self.scores[engine_name] - 0.05)  # Зменшуємо за програш
    
    def get_weights(self):
        """
        Обчислює ваги для кожного двигуна на основі їх скорів.
        
        Returns:
            dict: словник {engine_name: weight}
        """
        total_score = sum(self.scores.values())
        
        if total_score == 0:
            # Рівномірний розподіл якщо немає скорів
            return {name: 1.0 / len(self.engine_names) for name in self.engine_names}
        
        return {name: score / total_score for name, score in self.scores.items()}
    
    def get_best_engine(self):
        """
        Повертає назву найкращого двигуна.
        
        Returns:
            str: назва двигуна з найвищим скором
        """
        return max(self.scores, key=self.scores.get)
