# Decision Engine та BTC 5m AI Backtest

Цей модуль додає систему AI-сигналів для торгівлі BTC/USDT на 5-хвилинних свічках.

## Опис

Система складається з:
- **Feature Builder**: побудова технічних індикаторів з OHLCV даних
- **Target Builder**: створення мульти-класових міток для навчання
- **Decision Engine**: генерація торгових сигналів (BUY/SELL/HOLD)
- **Risk Filter**: фільтрація ризикованих сигналів
- **AI Backtester**: тестування стратегії на історичних даних

## Встановлення

1. Створіть віртуальне середовище:
```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

2. Встановіть залежності:
```bash
pip install pandas numpy scikit-learn joblib requests matplotlib
```

## Використання

### 1. Завантаження даних
```bash
python scripts/download_btc_5m.py
```

### 2. Навчання моделі
```bash
python training/train_btc_5m.py
```

### 3. Тестування сигналів
```bash
python scripts/test_signal.py
```

### 4. Запуск бектесту
```bash
python scripts/run_ai_backtest.py
```

### 5. Візуалізація результатів
```bash
python scripts/plot_equity.py
```

## Необхідні пакети

- pandas
- numpy
- scikit-learn
- joblib
- requests
- matplotlib

## Застереження

⚠️ **Важливо**: Ця система призначена тільки для навчальних цілей. 

- Модель може бути переоптимізована (overfitting) на історичних даних
- Минулі результати не гарантують майбутньої прибутковості
- Не використовуйте на реальних коштах без ретельного тестування

## Наступні кроки

- [ ] Додати більше ознак (On-Balance Volume, MACD, Bollinger Bands)
- [ ] Реалізувати cross-validation для кращої оцінки моделі
- [ ] Додати walk-forward аналіз
- [ ] Інтеграція з системою управління ризиками
- [ ] Додати adaptive position sizing
