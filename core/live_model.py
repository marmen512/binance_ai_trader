"""
LiveModel - модель з автоматичним перезавантаженням при зміні файлу.
"""
import pickle
import os


class LiveModel:
    """
    Обгортка над моделлю, яка автоматично перезавантажує модель при зміні файлу.
    """
    
    def __init__(self, model_path: str):
        """
        Args:
            model_path: шлях до файлу моделі
        """
        self.model_path = model_path
        self.model = None
        self.last_mtime = None
        self._load_model()
    
    def _load_model(self):
        """Завантажує модель з файлу."""
        try:
            with open(self.model_path, 'rb') as f:
                self.model = pickle.load(f)
            self.last_mtime = os.path.getmtime(self.model_path)
            print(f"✅ Модель завантажено з {self.model_path}")
        except FileNotFoundError:
            print(f"⚠️ Модель не знайдено: {self.model_path}")
            self.model = None
    
    def maybe_reload(self):
        """
        Перевіряє, чи змінився файл моделі, і перезавантажує при необхідності.
        """
        if not os.path.exists(self.model_path):
            return
        
        current_mtime = os.path.getmtime(self.model_path)
        
        if current_mtime != self.last_mtime:
            print(f"🔄 Виявлено зміну моделі, перезавантаження...")
            self._load_model()
    
    def predict_proba(self, X):
        """Proxy для predict_proba з автоматичним перезавантаженням."""
        self.maybe_reload()
        if self.model is None:
            raise ValueError("Модель не завантажена")
        return self.model.predict_proba(X)
