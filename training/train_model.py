"""
Базовий модуль тренування моделі RandomForest для торгових сигналів.
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib
import os


def train_model(df: pd.DataFrame, feature_cols: list, target_col: str = 'target', 
                model_path: str = 'models/signal_model.pkl'):
    """
    Тренує RandomForest модель на часових даних.
    
    Args:
        df: DataFrame з ознаками та цільовою змінною
        feature_cols: Список назв колонок-ознак
        target_col: Назва колонки-таргета
        model_path: Шлях для збереження моделі
    """
    print(f"Тренування моделі на {len(df)} записах...")
    
    # Часово-впорядковане розділення
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_test = test_df[feature_cols]
    y_test = test_df[target_col]
    
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")
    
    # Тренування RandomForest
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=20,
        min_samples_leaf=10,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train)
    
    # Оцінка точності
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"Train accuracy: {train_acc:.4f}")
    print(f"Test accuracy: {test_acc:.4f}")
    
    # Збереження моделі
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Модель збережено: {model_path}")
    
    return model


if __name__ == '__main__':
    print("Використовуйте цей модуль як бібліотеку або створіть власний скрипт тренування")
