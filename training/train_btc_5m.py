"""
Скрипт для навчання моделі специфічно для BTC 5m даних.

Використовує оптимізовані ознаки та гіперпараметри для BTCUSDT.
"""
import sys
import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# Додаємо корінь проекту до шляху
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.feature_builder import FeatureBuilder
from training.build_target import build_target


def main():
    csv_path = 'data/btcusdt_5m.csv'
    
    print(f"Завантаження даних з {csv_path}...")
    df = pd.read_csv(csv_path)
    
    # Будуємо ознаки
    print("Побудова ознак для BTC...")
    builder = FeatureBuilder()
    df = builder.build(df)
    
    # Будуємо target
    print("Побудова цільової змінної...")
    df = build_target(df, horizon=5, threshold=0.004)
    
    # Вибираємо оптимізовані ознаки для BTC
    feature_cols = ['ret1', 'ret3', 'ret12', 'vol10', 'ema_diff', 
                   'rsi', 'body_pct', 'vol_spike']
    X = df[feature_cols]
    y = df['target']
    
    # Розділяємо на train/test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    
    print(f"Навчальна вибірка: {len(X_train)} рядків")
    print(f"Тестова вибірка: {len(X_test)} рядків")
    print(f"Розподіл класів: {y.value_counts().to_dict()}")
    
    # Навчаємо модель з оптимізованими параметрами для BTC
    print("Навчання RandomForestClassifier для BTC...")
    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        random_state=42,
        n_jobs=-1,
        min_samples_split=10,
        min_samples_leaf=5
    )
    model.fit(X_train, y_train)
    
    # Оцінюємо точність
    train_acc = model.score(X_train, y_train)
    test_acc = model.score(X_test, y_test)
    
    print(f"Точність на навчальній вибірці: {train_acc:.4f}")
    print(f"Точність на тестовій вибірці: {test_acc:.4f}")
    
    # Показуємо важливість ознак
    feature_importance = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\nВажливість ознак:")
    print(feature_importance)
    
    # Зберігаємо модель
    os.makedirs('models', exist_ok=True)
    model_path = 'models/btc_5m_model.pkl'
    joblib.dump(model, model_path)
    print(f"\nМодель збережено в {model_path}")


if __name__ == '__main__':
    main()
