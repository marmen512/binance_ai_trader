"""
EnsembleEngine - ансамбль моделей з патчами для порогу ймовірності.
"""
import pickle
import numpy as np
from core.feature_builder import FeatureBuilder


class EnsembleEngine:
    """
    Ансамбль з трьох моделей: Random Forest, Gradient Boosting, Extra Trees.
    Підтримує динамічний поріг мінімальної ймовірності.
    """
    
    def __init__(self):
        # Завантажуємо моделі
        with open('models/rf_btc_5m.pkl', 'rb') as f:
            self.rf = pickle.load(f)
        with open('models/gb_btc_5m.pkl', 'rb') as f:
            self.gb = pickle.load(f)
        with open('models/et_btc_5m.pkl', 'rb') as f:
            self.et = pickle.load(f)
        
        self.models = [self.rf, self.gb, self.et]
        self.weights = [0.4, 0.3, 0.3]
        self.feature_builder = FeatureBuilder()
        
        # Патч: підтримка динамічного порогу
        self.min_prob_override = None
        
        self.FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema9', 'ema21', 'ema_diff',
                         'rsi', 'range', 'body', 'body_pct', 'vol_spike']
    
    def signal(self, df):
        """
        Генерує торговий сигнал на основі ансамблю моделей.
        
        Args:
            df: DataFrame з OHLCV даними
            
        Returns:
            tuple: (signal, confidence) де signal in ['BUY', 'SELL', 'HOLD']
        """
        # Будуємо ознаки
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return 'HOLD', 0.0
        
        # Беремо останній рядок
        X = df_features[self.FEATURES].iloc[-1:].values
        
        # Отримуємо predict_proba від кожної моделі
        probas = []
        for model in self.models:
            proba = model.predict_proba(X)[0]
            probas.append(proba)
        
        # Середньозважені ймовірності
        weighted_proba = np.zeros(3)
        for i, (proba, weight) in enumerate(zip(probas, self.weights)):
            weighted_proba += proba * weight
        
        # Клас з максимальною ймовірністю
        cls = np.argmax(weighted_proba)
        conf = weighted_proba[cls]
        
        # Патч: перевірка на min_prob_override
        if self.min_prob_override is not None:
            if conf < self.min_prob_override:
                return 'HOLD', conf
        
        # Стандартний поріг
        if conf < 0.6:
            return 'HOLD', conf
        
        # Маппінг класів: sklearn для [-1,0,1] створює індекси [0,1,2]
        # 0 -> SELL (-1), 1 -> HOLD (0), 2 -> BUY (1)
        signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = signal_map.get(cls, 'HOLD')
        
        return signal, conf
