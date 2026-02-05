"""
LiveModel — обгортка для моделі з автоматичним перезавантаженням.
"""

import joblib
import os


class LiveModel:
    """Обгортка для моделі з можливістю перезавантаження."""

    def __init__(self, model_path):
        """
        Ініціалізація LiveModel.

        Args:
            model_path (str): Шлях до файлу моделі
        """
        self.model_path = model_path
        self.model = None
        self.last_mtime = None
        self.load()

    def load(self):
        """Завантажує або перезавантажує модель."""
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            self.last_mtime = os.path.getmtime(self.model_path)

    def maybe_reload(self):
        """Перезавантажує модель якщо файл змінився."""
        if not os.path.exists(self.model_path):
            return

        current_mtime = os.path.getmtime(self.model_path)
        if current_mtime != self.last_mtime:
            print(f"Перезавантаження моделі з {self.model_path}...")
            self.load()

    def predict(self, X):
        """Передає виклик до моделі."""
        self.maybe_reload()
        return self.model.predict(X)

    def predict_proba(self, X):
        """Передає виклик до моделі."""
        self.maybe_reload()
        return self.model.predict_proba(X)
