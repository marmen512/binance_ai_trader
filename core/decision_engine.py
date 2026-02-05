"""
Модуль рішення торгових сигналів на основі ML моделі.

DecisionEngine завантажує навчену модель та генерує торгові сигнали
(BUY/SELL/HOLD) на основі поточних ринкових даних.
"""

import pandas as pd
import numpy as np
import joblib
import os
from core.feature_builder import FeatureBuilder


class DecisionEngine:
    """
    Механізм прийняття торгових рішень на основі ML моделі.
    
    Завантажує навчену модель та генерує сигнали BUY/SELL/HOLD
    з відповідними ймовірностями для торгової пари BTCUSDT 5m.
    """
    
    def __init__(self, model_path='models/btc_5m_model.pkl'):
        """
        Ініціалізує DecisionEngine та завантажує модель.
        
        Параметри:
            model_path (str): шлях до файлу з навченою моделлю (.pkl)
                            За замовчуванням: 'models/btc_5m_model.pkl'
        """
        self.model_path = model_path
        self.model = None
        self.feature_builder = FeatureBuilder()
        
        # Специфічні ознаки для BTC 5m моделі
        self.feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 
                            'rsi', 'body_pct', 'vol_spike']
        
        # Завантажуємо модель
        self._load_model()
    
    def _load_model(self):
        """
        Завантажує навчену модель з диска.
        
        Викидає:
            FileNotFoundError: якщо файл моделі не знайдено
        """
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Модель не знайдено: {self.model_path}\n"
                f"Спочатку натренуйте модель: python training/train_btc_5m.py"
            )
        
        print(f"Завантаження моделі з {self.model_path}...")
        self.model = joblib.load(self.model_path)
        print("Модель завантажено успішно!")
    
    def signal(self, df):
        """
        Генерує торговий сигнал на основі останніх даних.
        
        Параметри:
            df (pd.DataFrame): DataFrame з OHLCV даними.
                              Повинен містити щонайменше 50 останніх свічок
                              для коректного обчислення індикаторів.
                              Колонки: timestamp, open, high, low, close, volume
        
        Повертає:
            tuple: (signal, probability)
                signal (str): 'BUY', 'SELL' або 'HOLD'
                probability (float): ймовірність класу від моделі (0-1)
        """
        # Перевіряємо, що модель завантажена
        if self.model is None:
            raise RuntimeError("Модель не завантажена")
        
        # Перевіряємо мінімальну кількість даних
        if len(df) < 50:
            print("Недостатньо даних для побудови ознак (потрібно мінімум 50 свічок)")
            return 'HOLD', 0.0
        
        # Будуємо ознаки
        df_features = self.feature_builder.build(df.copy())
        
        if len(df_features) == 0:
            print("Після побудови ознак не залишилось даних")
            return 'HOLD', 0.0
        
        # Беремо останній рядок (найсвіжіші дані)
        latest = df_features.iloc[-1]
        
        # Формуємо вектор ознак
        X = np.array([latest[col] for col in self.feature_cols]).reshape(1, -1)
        
        # Перевіряємо на NaN
        if np.isnan(X).any():
            print("Виявлено NaN значення в ознаках")
            return 'HOLD', 0.0
        
        # Отримуємо прогноз та ймовірності
        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]
        
        # Знаходимо ймовірність прогнозованого класу
        class_idx = int(prediction) + 1  # -1 -> 0, 0 -> 1, 1 -> 2
        probability = probabilities[class_idx]
        
        # Конвертуємо числову мітку у текстовий сигнал
        signal_map = {
            -1: 'SELL',
            0: 'HOLD',
            1: 'BUY'
        }
        signal = signal_map[prediction]
        
        return signal, probability
    
    def get_model_info(self):
        """
        Повертає інформацію про завантажену модель.
        
        Повертає:
            dict: словник з інформацією про модель
        """
        if self.model is None:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'model_type': type(self.model).__name__,
            'model_path': self.model_path,
            'feature_cols': self.feature_cols,
            'n_features': len(self.feature_cols)
        }
