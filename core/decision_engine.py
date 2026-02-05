"""
Модуль Decision Engine для генерації торгових сигналів.
"""
import joblib
import pandas as pd
import numpy as np
import sys
import os

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder


class DecisionEngine:
    """
    Механізм прийняття рішень для генерації торгових сигналів.
    
    Завантажує навчену модель з models/btc_5m_model.pkl та використовує
    FeatureBuilder для обчислення ознак з вхідних даних.
    """
    
    def __init__(self, model_path='models/btc_5m_model.pkl'):
        """
        Ініціалізує DecisionEngine.
        
        Args:
            model_path: шлях до файлу з навченою моделлю
        """
        self.model_path = model_path
        self.model = joblib.load(model_path)
        self.feature_builder = FeatureBuilder()
        
        # Ознаки, які використовує BTC модель
        self.feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 
                           'rsi', 'body_pct', 'vol_spike']
    
    def signal(self, df: pd.DataFrame) -> tuple:
        """
        Генерує торговий сигнал на основі вхідних даних.
        
        Args:
            df: DataFrame з колонками timestamp, open, high, low, close, volume
            
        Returns:
            tuple (signal, probability) де:
                - signal: "BUY", "SELL" або "HOLD"
                - probability: ймовірність прогнозу (0-1)
        """
        # Будуємо ознаки
        df_features = self.feature_builder.build(df)
        
        if len(df_features) == 0:
            return "HOLD", 0.0
        
        # Беремо останній рядок
        X = df_features[self.feature_cols].iloc[-1:].values
        
        # Отримуємо прогноз та ймовірності
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        # Знаходимо максимальну ймовірність
        max_prob = probabilities.max()
        
        # Перетворюємо у сигнал
        if prediction == 1:
            signal = "BUY"
        elif prediction == -1:
            signal = "SELL"
        else:
            signal = "HOLD"
        
        return signal, float(max_prob)
