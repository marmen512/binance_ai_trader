"""
RegimeModelEngine - двигун з вибором моделі залежно від режиму.
"""
import pickle
import numpy as np
from core.feature_builder import FeatureBuilder
from core.regime_detector import RegimeDetector


class RegimeModelEngine:
    """
    Використовує різні моделі залежно від поточного режиму ринку.
    """
    
    def __init__(self):
        # Завантажуємо моделі для кожного режиму
        self.models = {}
        
        for regime in ['TREND', 'RANGE', 'VOLATILE']:
            try:
                with open(f'models/model_{regime}.pkl', 'rb') as f:
                    self.models[regime] = pickle.load(f)
                print(f"Завантажено модель для {regime}")
            except FileNotFoundError:
                print(f"⚠️ Модель для {regime} не знайдено")
        
        self.feature_builder = FeatureBuilder()
        self.regime_detector = RegimeDetector()
        
        self.FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
        self.prob_threshold = 0.62
    
    def signal(self, df):
        """
        Генерує сигнал використовуючи модель відповідну режиму.
        
        Args:
            df: DataFrame з OHLCV даними
            
        Returns:
            tuple: (signal, prob) де signal in ['BUY', 'SELL', 'HOLD']
        """
        # Визначаємо режим
        regime = self.regime_detector.detect(df)
        
        # Перевіряємо наявність моделі для цього режиму
        if regime not in self.models:
            return 'HOLD', 0.0
        
        # Будуємо ознаки
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return 'HOLD', 0.0
        
        # Беремо останній рядок
        X = df_features[self.FEATURES].iloc[-1:].values
        
        # Отримуємо predict_proba
        model = self.models[regime]
        proba = model.predict_proba(X)[0]
        
        # Клас з максимальною ймовірністю
        cls = np.argmax(proba)
        prob = proba[cls]
        
        # Перевірка порогу
        if prob < self.prob_threshold:
            return 'HOLD', prob
        
        # Маппінг класів: 0 -> SELL, 1 -> HOLD, 2 -> BUY
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = signal_map.get(cls, 'HOLD')
        
        return signal, prob
