"""
Загальний скрипт для навчання моделі RandomForest на даних свічок.

Використання:
    python training/train_model.py
    або
    python training/train_model.py --csv_path data/my_candles.csv
"""
import sys
import os
import argparse
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def main():
    parser = argparse.ArgumentParser(description='Навчити модель на свічкових даних')
    parser.add_argument('--csv_path', type=str, default='data/candles.csv',
                       help='Шлях до CSV файлу з даними')
    args = parser.parse_args()
    
    print(f"Завантаження даних з {args.csv_path}...")
    df = pd.read_csv(args.csv_path)
    
    # Будуємо ознаки
    print("Побудова ознак...")
    builder = FeatureBuilder()
    df = builder.build(df)
    
    # Будуємо target
    print("Побудова цільової змінної...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    # Вибираємо ознаки для навчання
    feature_cols = ['ret_1', 'ret_5', 'volatility_10', 'ema_9', 'ema_21', 
                   'ema_diff', 'rsi', 'range', 'body', 'body_pct']
    X = df[feature_cols]
    y = df['target']
    
    # Розділяємо на train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    
    print(f"Навчальна вибірка: {len(X_train)} рядків")
    print(f"Тестова вибірка: {len(X_test)} рядків")
    
    # Навчаємо модель
    print("Навчання RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=6,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    
    # Оцінюємо точність
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"Точність на навчальній вибірці: {train_acc:.4f}")
    print(f"Точність на тестовій вибірці: {test_acc:.4f}")
    
    # Зберігаємо модель
    os.makedirs('models', exist_ok=True)
    model_path = 'models/signal_model.pkl'
    joblib.dump(model, model_path)
    print(f"Модель збережено в {model_path}")


if __name__ == '__main__':
    main()
