# binance_ai_trader

Phase-based system skeleton.

## Phase 0 commands

- `python -m interfaces.cli.main doctor`

## Web UI

- Install deps (once): `pip install -e .`
- Run web server:
  - `./run.sh web --config config/config.yaml --host 127.0.0.1 --port 8000`
  - or `python -m interfaces.web.main --config config/config.yaml --host 127.0.0.1 --port 8000`
- Open: `http://127.0.0.1:8000/`

## AI Trading Pipeline (WTR)

This repository now includes a comprehensive AI trading pipeline with walk-forward training, threshold optimization, regime detection, and ensemble/regime-specific models.

### Dependencies

Install the required dependencies:
```bash
pip install pandas numpy scikit-learn joblib requests matplotlib
```

### Quick Start

1. **Download BTC 5m data:**
   ```bash
   python scripts/download_btc_5m.py
   ```

2. **Train ensemble models (RF, GB, ET):**
   ```bash
   python training/train_ensemble.py
   ```

3. **Test signal generation:**
   ```bash
   python scripts/test_signal.py
   ```

4. **Run AI backtest with ensemble:**
   ```bash
   python scripts/run_ai_backtest.py
   ```

### Advanced Features

#### Walk-Forward Training
Performs time-series cross-validation with rolling windows:
```bash
python training/walk_forward.py
```

#### Threshold Optimization
Tests different probability thresholds to find optimal settings:
```bash
python training/threshold_optimizer.py
```

#### Regime-Specific Models
Train separate models for VOLATILE, TREND, and RANGE market regimes:
```bash
python training/train_regime_models.py
python scripts/run_ai_backtest_regime.py
```

#### Visualizations
Plot equity curves from backtests:
```bash
python scripts/plot_equity.py
```

### Architecture

**Core Components:**
- `core/feature_builder.py` - Technical indicator feature engineering
- `core/ensemble_engine.py` - Ensemble model loader with weighted voting
- `core/regime_detector.py` - Market regime detection (VOLATILE/TREND/RANGE)
- `core/probability_gate.py` - Regime-specific probability thresholds
- `core/position_sizer.py` - Volatility-based position sizing
- `core/regime_model_engine.py` - Regime-specific model selection

**Training:**
- `training/build_target.py` - Target labeling with forward returns
- `training/train_ensemble.py` - Train RF, GB, ET ensemble
- `training/walk_forward.py` - Walk-forward optimization
- `training/threshold_optimizer.py` - Probability threshold tuning
- `training/train_regime_models.py` - Regime-specific model training

**Backtesting:**
- `ai_backtest/engine.py` - Full backtesting with regime integration
- `ai_backtest/metrics.py` - Performance metrics (Sharpe, drawdown, win rate)

**Notes:**
- Class ordering: sklearn maps [-1,0,1] to indices [0=SELL, 1=HOLD, 2=BUY]
- Ensemble weights: [0.4, 0.3, 0.3] for RF, GB, ET
- Default probability threshold: 0.55 (overridable via `min_prob_override`)
- Regime-specific model threshold: 0.62

