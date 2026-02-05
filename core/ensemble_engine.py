"""
Ансамблевий двигун сигналів.
Завантажує три моделі (RF, GB, ET), усереднює їх прогнози та видає сигнал.
"""
import numpy as np
import joblib
import os


class EnsembleEngine:
    """
    Ансамблевий двигун для генерації торгових сигналів.
    Завантажує RandomForest, GradientBoosting, ExtraTrees та усереднює їх прогнози.
    """
    
    def __init__(self, model_dir='models'):
        """
        Ініціалізація ансамблю.
        
        Args:
            model_dir: Директорія з моделями
        """
        self.model_dir = model_dir
        self.models = {}
        self.weights = [0.4, 0.3, 0.3]  # Ваги для RF, GB, ET
        
        # Завантаження моделей
        self._load_models()
    
    def _load_models(self):
        """Завантажує всі три моделі."""
        model_files = {
            'rf': os.path.join(self.model_dir, 'rf_btc_5m.pkl'),
            'gb': os.path.join(self.model_dir, 'gb_btc_5m.pkl'),
            'et': os.path.join(self.model_dir, 'et_btc_5m.pkl')
        }
        
        for name, path in model_files.items():
            if os.path.exists(path):
                self.models[name] = joblib.load(path)
                print(f"Завантажено модель: {name} з {path}")
            else:
                raise FileNotFoundError(f"Модель не знайдено: {path}")
        
        print(f"Всього завантажено моделей: {len(self.models)}")
    
    def signal(self, features: dict) -> tuple:
        """
        Генерує сигнал на основі ознак.
        
        Args:
            features: Словник з ознаками {'ret1': ..., 'ret3': ..., ...}
            
        Returns:
            (signal, confidence): signal = 'BUY', 'SELL', 'HOLD'; confidence = ймовірність
        """
        # Перетворення ознак у масив
        feature_names = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
        X = np.array([[features.get(f, 0.0) for f in feature_names]])
        
        # Отримання predict_proba від кожної моделі
        probas = []
        for name in ['rf', 'gb', 'et']:
            if name in self.models:
                proba = self.models[name].predict_proba(X)[0]
                probas.append(proba)
        
        # Усереднення з вагами
        avg_proba = np.average(probas, axis=0, weights=self.weights)
        
        # Маппінг класів: sklearn сортує класи [-1, 0, 1] -> індекси [0, 1, 2]
        # 0 -> SELL (-1)
        # 1 -> HOLD (0)
        # 2 -> BUY (1)
        class_idx = np.argmax(avg_proba)
        confidence = avg_proba[class_idx]
        
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = signal_map[class_idx]
        
        return signal, confidence
    
    def predict_proba(self, features: dict) -> np.ndarray:
        """
        Повертає усереднені ймовірності для кожного класу.
        
        Args:
            features: Словник з ознаками
            
        Returns:
            Масив ймовірностей [prob_sell, prob_hold, prob_buy]
        """
        feature_names = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
        X = np.array([[features.get(f, 0.0) for f in feature_names]])
        
        probas = []
        for name in ['rf', 'gb', 'et']:
            if name in self.models:
                proba = self.models[name].predict_proba(X)[0]
                probas.append(proba)
        
        avg_proba = np.average(probas, axis=0, weights=self.weights)
        return avg_proba
