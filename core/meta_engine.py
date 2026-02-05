"""
MetaEngine — комбінує кілька движків з адаптивними вагами.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.meta_tracker import EngineTracker


class MetaEngine:
    """
    Мета-движок що комбінує сигнали від кількох движків.
    Використовує адаптивні ваги на основі історичної ефективності.
    """

    def __init__(self, engines):
        """
        Ініціалізація MetaEngine.

        Args:
            engines (dict): Словник {name: engine_instance}
        """
        self.engines = engines
        self.tracker = EngineTracker(window=40)

    def signal(self, df):
        """
        Генерує комбінований сигнал від усіх движків.

        Args:
            df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            tuple: (signal, probability, used_names) де signal це 'BUY', 'HOLD', або 'SELL'
        """
        signals = {}
        probabilities = {}

        # Отримуємо сигнали від кожного движка
        for name, engine in self.engines.items():
            try:
                sig, prob = engine.signal(df)
                signals[name] = sig
                probabilities[name] = prob
            except Exception as e:
                print(f"Помилка в движку {name}: {e}")
                signals[name] = 'HOLD'
                probabilities[name] = 0.0

        # Обчислюємо ваги на основі історичної ефективності
        weights = {}
        total_score = 0
        for name in self.engines.keys():
            score = self.tracker.score(name)
            weights[name] = score
            total_score += score

        # Нормалізуємо ваги
        if total_score > 0:
            for name in weights:
                weights[name] /= total_score
        else:
            # Рівні ваги якщо немає історії
            for name in weights:
                weights[name] = 1.0 / len(weights)

        # Зважене голосування
        vote_scores = {'BUY': 0.0, 'SELL': 0.0, 'HOLD': 0.0}
        weighted_prob = 0.0

        for name in self.engines.keys():
            sig = signals[name]
            prob = probabilities[name]
            weight = weights[name]

            vote_scores[sig] += weight * prob
            weighted_prob += weight * prob

        # Визначаємо фінальний сигнал
        final_signal = max(vote_scores, key=vote_scores.get)
        final_prob = vote_scores[final_signal] / len(self.engines) if len(self.engines) > 0 else 0.0

        used_names = list(self.engines.keys())

        return final_signal, final_prob, used_names

    def update(self, used_names, pnl):
        """
        Оновлює трекер результатами трейду.

        Args:
            used_names (list): Список назв движків що використовувались
            pnl (float): Прибуток/збиток від трейду
        """
        for name in used_names:
            self.tracker.add(name, pnl)
