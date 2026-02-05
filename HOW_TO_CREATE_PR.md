# Інструкція для створення Pull Request

## Стан виконання

Всі необхідні зміни виконано та закомічено у гілку `feature/decision-engine`:

### Створені файли:

1. ✅ `core/feature_builder.py` - Клас FeatureBuilder для побудови технічних ознак
2. ✅ `training/build_target.py` - Функція build_target для створення цільової змінної
3. ✅ `training/train_model.py` - Пайплайн тренування RandomForest моделі
4. ✅ `scripts/download_btc_5m.py` - Скрипт завантаження даних з Binance
5. ✅ `training/train_btc_5m.py` - BTC-специфічний тренувальний скрипт
6. ✅ `core/decision_engine.py` - Клас DecisionEngine для генерації сигналів
7. ✅ `core/risk_filter.py` - Функція risk_filter для фільтрації ризикованих сигналів
8. ✅ `scripts/test_signal.py` - Скрипт тестування генерації сигналів
9. ✅ `ai_backtest/engine.py` - Клас AIBacktester для бектестингу
10. ✅ `ai_backtest/metrics.py` - Функції обчислення метрик стратегії
11. ✅ `scripts/run_ai_backtest.py` - Скрипт запуску повного бектесту
12. ✅ `scripts/plot_equity.py` - Скрипт візуалізації кривої капіталу
13. ✅ `models/.gitkeep` - Файл для відстеження директорії models
14. ✅ `requirements.txt` - Оновлено з додатковими залежностями
15. ✅ `PR_DESCRIPTION_UKRAINIAN.md` - Повний опис PR українською мовою

### Коміти:

- ✅ "Add feature builder, target builder, RandomForest training and DecisionEngine for BTCUSDT 5m; add download and test scripts"
- ✅ "Add required dependencies: scikit-learn, joblib, requests, matplotlib"
- ✅ "Add Ukrainian PR description with comprehensive instructions"

## Наступні кроки для створення PR

### Опція 1: Через GitHub CLI (якщо gh доступний)

```bash
gh pr create \
  --base main \
  --head feature/decision-engine \
  --title "Add Decision Engine, Feature Engineering and BTC 5m AI Backtest" \
  --body-file PR_DESCRIPTION_UKRAINIAN.md
```

### Опція 2: Через GitHub Web UI

1. Перейдіть на https://github.com/marmen512/binance_ai_trader
2. Натисніть "Pull requests" → "New pull request"
3. Встановіть:
   - **Base:** `main`
   - **Compare:** `feature/decision-engine`
4. Додайте заголовок: **"Add Decision Engine, Feature Engineering and BTC 5m AI Backtest"**
5. Скопіюйте опис з файлу `PR_DESCRIPTION_UKRAINIAN.md`
6. Натисніть "Create pull request"

### Опція 3: Через GitHub API

```bash
curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.github.com/repos/marmen512/binance_ai_trader/pulls \
  -d '{
    "title": "Add Decision Engine, Feature Engineering and BTC 5m AI Backtest",
    "body": "...(content from PR_DESCRIPTION_UKRAINIAN.md)...",
    "head": "feature/decision-engine",
    "base": "main"
  }'
```

## Важливо!

Перед створенням PR переконайтесь, що гілка `feature/decision-engine` відправлена на GitHub:

```bash
git push -u origin feature/decision-engine
```

## Зміст PR Description (Короткий виклад)

**Заголовок:** Add Decision Engine, Feature Engineering and BTC 5m AI Backtest

**Опис (українською):**
- Повний ML пайплайн для торгівлі BTCUSDT 5m
- Модулі побудови ознак, тренування моделі, генерації сигналів
- AI бектестинг з комісіями та проковзуванням
- Візуалізація результатів
- Всі коментарі та docstrings українською мовою

**Інструкції:**
1. Встановити залежності: `pip install -r requirements.txt`
2. Завантажити дані: `python scripts/download_btc_5m.py`
3. Натренувати модель: `python training/train_btc_5m.py`
4. Протестувати сигнали: `python scripts/test_signal.py`
5. Запустити бектест: `python scripts/run_ai_backtest.py`
6. Візуалізувати результати: `python scripts/plot_equity.py`

Детальний опис міститься у файлі `PR_DESCRIPTION_UKRAINIAN.md`.
