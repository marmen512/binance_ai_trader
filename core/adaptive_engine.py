"""
AdaptiveEngine — використовує LiveModel для адаптивного трейдингу.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from core.live_model import LiveModel


class AdaptiveEngine:
    """Адаптивний движок з можливістю online оновлення моделі."""

    def __init__(self, prob_threshold=0.6):
        """
        Ініціалізація AdaptiveEngine.

        Args:
            prob_threshold (float): Поріг ймовірності для сигналу
        """
        self.model = LiveModel('models/adaptive_latest.pkl')
        self.feature_builder = FeatureBuilder()
        self.prob_threshold = prob_threshold
        self.features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']

    def signal(self, df):
        """
        Генерує сигнал з використанням адаптивної моделі.

        Args:
            df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            tuple: (signal, probability) де signal це 'BUY', 'HOLD', або 'SELL'
        """
        # Будуємо фічі
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return 'HOLD', 0.0

        # Беремо останній рядок
        row = df_features[self.features].iloc[-1:].values

        # Отримуємо predict_proba
        proba = self.model.predict_proba(row)[0]
        predicted_class = proba.argmax()
        confidence = proba[predicted_class]

        # Мапінг класів: 0 = SELL, 1 = HOLD, 2 = BUY
        class_to_signal = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = class_to_signal[predicted_class]

        # Застосовуємо поріг
        if confidence < self.prob_threshold:
            return 'HOLD', confidence

        return signal, confidence
