"""
RegimeModelEngine — використовує окремі моделі для різних ринкових режимів.
"""

import joblib
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder
from core.regime_detector import RegimeDetector


class RegimeModelEngine:
    """Movement engine що використовує режим-специфічні моделі."""

    def __init__(self, prob_threshold=0.62):
        """
        Ініціалізація RegimeModelEngine.

        Args:
            prob_threshold (float): Поріг ймовірності для сигналу
        """
        self.models = {
            'TREND': joblib.load('models/model_TREND.pkl'),
            'RANGE': joblib.load('models/model_RANGE.pkl'),
            'VOLATILE': joblib.load('models/model_VOLATILE.pkl')
        }
        self.feature_builder = FeatureBuilder()
        self.regime_detector = RegimeDetector()
        self.prob_threshold = prob_threshold
        self.features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']

    def signal(self, df):
        """
        Генерує сигнал на основі поточного режиму.

        Args:
            df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            tuple: (signal, probability) де signal це 'BUY', 'HOLD', або 'SELL'
        """
        # Визначаємо режим
        regime = self.regime_detector.detect(df)

        # Будуємо фічі
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return 'HOLD', 0.0

        # Беремо останній рядок
        row = df_features[self.features].iloc[-1:].values

        # Вибираємо модель для режиму
        model = self.models.get(regime)
        if model is None:
            return 'HOLD', 0.0

        # Отримуємо predict_proba
        proba = model.predict_proba(row)[0]
        predicted_class = proba.argmax()
        confidence = proba[predicted_class]

        # Мапінг класів: 0 = SELL, 1 = HOLD, 2 = BUY
        class_to_signal = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = class_to_signal[predicted_class]

        # Застосовуємо поріг
        if confidence < self.prob_threshold:
            return 'HOLD', confidence

        return signal, confidence
