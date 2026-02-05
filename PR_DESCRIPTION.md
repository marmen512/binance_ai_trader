# Production: Adaptive Retrain, Drift Detector, Live Model & WTR/Ensemble Integration

## Короткий опис змін

Цей PR додає продакшн-готовий механізм адаптивного перенавчання, детектор дрейфу моделі, систему онлайн-оновлення моделей та інтеграцію Walk-Forward Retraining з Ensemble движком.

### Додані файли:

**Core компоненти:**
- `core/drift_detector.py` - детектор дрейфу, що відслідковує PnL торгів і сигналізує про погіршення продуктивності
- `core/live_model.py` - обгортка для hot-reload моделей при зміні файлу на диску
- `core/adaptive_engine.py` - адаптивний движок прогнозування з автоматичним оновленням
- `core/regime_model_engine.py` - система режим-специфічних моделей (TREND/RANGE/VOLATILE)
- `core/ensemble_engine.py` - ансамбль моделей з підтримкою min_prob_override
- `core/regime_detector.py` - детектор ринкового режиму
- `core/probability_gate.py` - фільтр сигналів за порогом впевненості
- `core/position_sizer.py` - розрахунок розміру позиції

**Тренування:**
- `training/adaptive_retrain.py` - адаптивне перенавчання на останніх 12k рядків даних
- `training/walk_forward.py` - Walk-Forward валідація з ковзними вікнами
- `training/threshold_optimizer.py` - оптимізація порогу ймовірності (0.55-0.73)
- `training/train_regime_models.py` - тренування окремих моделей для кожного режиму
- `training/train_ensemble.py` - тренування ансамблю (RF + GB + ET)
- `training/train_btc_5m.py` - базовий скрипт тренування

**AI Backtest:**
- `ai_backtest/engine.py` - бектестер з інтеграцією drift detector
- `ai_backtest/metrics.py` - розрахунок метрик бектесту

**Scripts:**
- `scripts/download_btc_5m.py` - завантаження даних BTC/USDT 5m з Binance
- `scripts/retrain_if_drift.py` - запуск перенавчання при дрейфі
- `scripts/run_ai_backtest.py` - запуск бектесту з ensemble
- `scripts/run_ai_backtest_regime.py` - запуск бектесту з regime models
- `scripts/test_signal.py` - тестування генерації сигналів
- `scripts/plot_equity.py` - побудова графіку equity curve

**Допоміжні:**
- `features/feature_builder.py` - побудова технічних індикаторів
- `models/.gitkeep` - placeholder для моделей

## Як запускати (швидкий чеклист)

1. **Створити віртуальне середовище і встановити залежності:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # На Windows: venv\Scripts\activate
   pip install pandas numpy scikit-learn joblib requests matplotlib
   ```

2. **Завантажити дані:**
   ```bash
   python scripts/download_btc_5m.py
   ```

3. **Навчити ensemble моделей:**
   ```bash
   python training/train_ensemble.py
   ```

4. **(Опція) Прогнати walk-forward валідацію:**
   ```bash
   python training/walk_forward.py
   ```

5. **(Опція) Підібрати оптимальний поріг:**
   ```bash
   python training/threshold_optimizer.py
   ```

6. **Навчити regime-specific моделі:**
   ```bash
   python training/train_regime_models.py
   ```

7. **Навчити adaptive модель:**
   ```bash
   python training/adaptive_retrain.py
   ```

8. **Запустити backtest (ensemble):**
   ```bash
   python scripts/run_ai_backtest.py
   ```

9. **Запустити backtest (regime models):**
   ```bash
   python scripts/run_ai_backtest_regime.py
   ```

10. **Авто-перенавчання при дрейфі:**
    - Налаштувати cron/scheduler для періодичного запуску `scripts/retrain_if_drift.py`
    - Або інтегрувати в продакшн процес моніторингу

## Notes & Caveats (важливі примітки)

### Маппінг класів sklearn
⚠️ **ВАЖЛИВО:** sklearn використовує внутрішні індекси [0, 1, 2] які маппяться як:
- `0` → `SELL`
- `1` → `HOLD`
- `2` → `BUY`

Це критично для правильної інтерпретації прогнозів. Всі engine-и використовують цей маппінг.

### Реалістична симуляція виконання
- Поточна версія використовує спрощену модель виконання
- Для продакшн потрібно:
  - Більш реалістична симуляція slippage
  - Моделювання order book depth
  - Врахування market impact
  - Латентність виконання

### Логування та моніторинг
- Додайте більш robust логування в продакшн
- Інтегруйте з системою моніторингу (Prometheus/Grafana)
- Налаштуйте alerting для критичних подій (drift detection)

### Paper Trading перед Live
⚠️ **ОБОВ'ЯЗКОВО:** Протестуйте на paper trading перед запуском на реальних коштах!
- Запустіть мінімум 1-2 тижні на paper trading
- Верифікуйте всі компоненти працюють коректно
- Моніторте drift detection в реальному часі
- Перевірте adaptive retraining pipeline

### Ризики
- ML моделі можуть давати false signals
- Drift detection може бути занадто чутливим/нечутливим
- Адаптивне перенавчання може overfitting на recent data
- Завжди використовуйте risk management та position sizing

### Подальші покращення
- [ ] Більш складна feature engineering
- [ ] Hyperparameter optimization для моделей
- [ ] Більш robust drift detection (Kolmogorov-Smirnov test, etc.)
- [ ] A/B testing framework для порівняння стратегій
- [ ] Real-time model performance dashboard
- [ ] Automated model rollback при поганій performance

## Архітектурні рішення

### Drift Detection
Використовується sliding window approach з відслідковуванням win rate. Коли win rate падає нижче threshold, сигналізується drift.

### Live Model Reloading
LiveModel wrapper перевіряє modification time файлу моделі та перезавантажує при змінах. Дозволяє hot-swap моделей без перезапуску процесу.

### Regime-Specific Models
Окремі моделі для різних ринкових режимів (TREND/RANGE/VOLATILE) дозволяють краще адаптуватися до поточних умов.

### Ensemble Approach
Комбінація RandomForest, GradientBoosting та ExtraTrees з weighted voting для більш robust прогнозів.

## Тестування

Всі компоненти протестовані на imports та базову функціональність. Для повного тестування:

```bash
# Тест імпортів
python scripts/test_signal.py

# Тест бектестів
python scripts/run_ai_backtest.py
python scripts/run_ai_backtest_regime.py

# Візуалізація
python scripts/plot_equity.py
```

---

**Автор:** Binance AI Trader Team  
**Дата:** 2026-02-05  
**Версія:** 1.0.0
