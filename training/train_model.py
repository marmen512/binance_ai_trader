"""
Модуль тренування моделі RandomForest для прогнозування торгових сигналів.

Цей скрипт виконує повний цикл навчання: завантаження даних, побудова ознак,
створення цільової змінної, тренування моделі та збереження артефактів.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os


def train_model(data_path, model_path, test_size=0.2, random_state=42):
    """
    Тренує модель RandomForest для прогнозування торгових сигналів.
    
    Параметри:
        data_path (str): шлях до CSV файлу з підготовленими даними (з ознаками та target)
        model_path (str): шлях для збереження навченої моделі
        test_size (float): частка даних для тестування (за замовчуванням 0.2)
        random_state (int): seed для відтворюваності результатів
        
    Повертає:
        dict: словник з метриками точності на train та test наборах
    """
    # Завантажуємо дані
    print(f"Завантаження даних з {data_path}...")
    df = pd.read_csv(data_path)
    
    # Перевіряємо наявність необхідних колонок
    required_cols = ['target']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Відсутня необхідна колонка: {col}")
    
    # Визначаємо ознаки (всі колонки крім target, timestamp та OHLCV)
    exclude_cols = ['target', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
    feature_cols = [col for col in df.columns if col not in exclude_cols]
    
    X = df[feature_cols].values
    y = df['target'].values
    
    # Розділяємо дані зі збереженням часового порядку (не перемішуємо!)
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"Розмір train: {len(X_train)}, test: {len(X_test)}")
    print(f"Розподіл класів у train: {np.bincount(y_train.astype(int) + 1)}")
    
    # Тренуємо модель RandomForest
    print("Тренування моделі RandomForest...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Оцінюємо точність
    train_score = model.score(X_train, y_train)
    test_score = model.score(X_test, y_test)
    
    print(f"Точність на train: {train_score:.4f}")
    print(f"Точність на test: {test_score:.4f}")
    
    # Зберігаємо модель
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Модель збережено: {model_path}")
    
    # Зберігаємо також список ознак
    feature_path = model_path.replace('.pkl', '_features.txt')
    with open(feature_path, 'w') as f:
        f.write('\n'.join(feature_cols))
    print(f"Список ознак збережено: {feature_path}")
    
    return {
        'train_score': train_score,
        'test_score': test_score,
        'n_features': len(feature_cols),
        'feature_cols': feature_cols
    }


# Приклад використання:
# 
# from training.train_model import train_model
# 
# # Тренування моделі на підготовлених даних
# results = train_model(
#     data_path='data/btcusdt_5m_features.csv',
#     model_path='models/signal_model.pkl',
#     test_size=0.2
# )
# 
# print(f"Модель навчено з точністю: {results['test_score']:.4f}")
