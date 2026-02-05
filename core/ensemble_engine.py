"""
EnsembleEngine — завантажує три моделі та генерує сигнали на основі зваженого голосування.
"""

import joblib
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feature_builder import FeatureBuilder


class EnsembleEngine:
    """
    Ансамблевий движок, що комбінує три моделі ML для прийняття торгових рішень.
    """

    def __init__(self, conf_threshold=0.6):
        """
        Ініціалізація EnsembleEngine.

        Args:
            conf_threshold (float): Мінімальна впевненість для сигналу (за замовчуванням 0.6)
        """
        self.models = [
            joblib.load('models/rf_btc_5m.pkl'),
            joblib.load('models/gb_btc_5m.pkl'),
            joblib.load('models/et_btc_5m.pkl')
        ]
        self.weights = [0.4, 0.3, 0.3]
        self.feature_builder = FeatureBuilder()
        self.min_prob_override = None
        self.conf_threshold = conf_threshold
        self.features = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 'rsi', 'body_pct', 'vol_spike']

    def signal(self, df):
        """
        Генерує торговий сигнал на основі останнього рядка даних.

        Args:
            df (pd.DataFrame): DataFrame з OHLCV даними

        Returns:
            tuple: (signal, confidence) де signal це 'BUY', 'HOLD', або 'SELL'
        """
        # Будуємо фічі
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return 'HOLD', 0.0

        # Беремо останній рядок
        row = df_features[self.features].iloc[-1:].values

        # Отримуємо predict_proba від кожної моделі
        probas = []
        for model in self.models:
            proba = model.predict_proba(row)[0]
            probas.append(proba)

        # Зважене усереднення
        weighted_proba = np.zeros(3)
        for i, (proba, weight) in enumerate(zip(probas, self.weights)):
            weighted_proba += proba * weight

        # Визначаємо клас з найвищою ймовірністю
        predicted_class = np.argmax(weighted_proba)
        confidence = weighted_proba[predicted_class]

        # Мапінг класів: 0 = SELL, 1 = HOLD, 2 = BUY
        class_to_signal = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
        signal = class_to_signal[predicted_class]

        # Застосовуємо override якщо встановлено
        if self.min_prob_override is not None and confidence < self.min_prob_override:
            return 'HOLD', confidence

        # Застосовуємо базовий поріг
        if confidence < self.conf_threshold:
            return 'HOLD', confidence

        return signal, confidence
