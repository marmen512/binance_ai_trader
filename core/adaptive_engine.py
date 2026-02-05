"""
AdaptiveEngine - двигун з LiveModel для онлайн-оновлень.
"""
import numpy as np
from core.live_model import LiveModel
from core.feature_builder import FeatureBuilder


class AdaptiveEngine:
    """
    Двигун, що використовує LiveModel для автоматичного перезавантаження моделі.
    """
    
    def __init__(self, model_path='models/adaptive_latest.pkl'):
        """
        Args:
            model_path: шлях до адаптивної моделі
        """
        self.live_model = LiveModel(model_path)
        self.feature_builder = FeatureBuilder()
        
        self.FEATURES = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']
        self.prob_threshold = 0.6
    
    def signal(self, df):
        """
        Генерує сигнал з автоматичним перезавантаженням моделі.
        
        Args:
            df: DataFrame з OHLCV даними
            
        Returns:
            tuple: (signal, prob) де signal in ['BUY', 'SELL', 'HOLD']
        """
        # Будуємо ознаки
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return 'HOLD', 0.0
        
        # Беремо останній рядок
        X = df_features[self.FEATURES].iloc[-1:].values
        
        # Отримуємо predict_proba (з автоматичним перезавантаженням)
        try:
            proba = self.live_model.predict_proba(X)[0]
        except Exception as e:
            print(f"⚠️ Помилка при predict_proba: {e}")
            return 'HOLD', 0.0
        
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
