# AI Signal Pipeline

This directory contains the AI-powered signal generation pipeline for the binance_ai_trader project.

## Overview

The pipeline consists of:

1. **FeatureBuilder** (`core/feature_builder.py`) - Extracts technical indicators from OHLCV data
2. **Target Builder** (`training/build_target.py`) - Creates labeled training data
3. **Training Script** (`training/train_model.py`) - Trains a RandomForest classifier
4. **DecisionEngine** (`core/decision_engine.py`) - Generates BUY/SELL/HOLD signals
5. **Risk Filter** (`core/risk_filter.py`) - Applies risk management rules

## Quick Start

### 1. Train the Model

```bash
# Train on default data/candles.csv
PYTHONPATH=/home/runner/work/binance_ai_trader/binance_ai_trader python training/train_model.py

# Or specify a custom CSV file
PYTHONPATH=/home/runner/work/binance_ai_trader/binance_ai_trader python training/train_model.py path/to/candles.csv
```

The CSV file must have columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`

### 2. Generate Signals

```python
from core.decision_engine import DecisionEngine
from core.risk_filter import risk_filter
import pandas as pd

# Load your data
df = pd.read_csv("data/candles.csv")

# Initialize decision engine
engine = DecisionEngine("models/signal_model.pkl")

# Get signal
signal, prob = engine.predict(df)
print(f"Signal: {signal}, Confidence: {prob:.2f}")

# Apply risk filter
volatility = df["close"].pct_change().std()
filtered_signal = risk_filter(signal, prob, volatility)
print(f"Filtered Signal: {filtered_signal}")
```

## Features

The FeatureBuilder extracts the following features:

- **Returns**: 1-period and 5-period percentage changes
- **Volatility**: 10-period rolling standard deviation of returns
- **EMA**: 9-period and 21-period exponential moving averages and their difference
- **RSI**: 14-period Relative Strength Index
- **Candle Features**: Range, body, and body percentage

## Model Training

The training script:
- Splits data 80/20 train/test (time-series split, no shuffling)
- Uses RandomForestClassifier with 200 trees and max depth of 6
- Outputs model to `models/signal_model.pkl`
- Prints test accuracy

## Decision Engine

The DecisionEngine:
- Loads the trained model
- Applies feature extraction to input data
- Returns signal (BUY/SELL/HOLD) and confidence probability
- Only generates BUY/SELL if confidence > 0.55, otherwise HOLD

## Risk Filter

The risk_filter function:
- Returns HOLD if volatility > 0.03 (3%)
- Returns HOLD if confidence < 0.6 (60%)
- Otherwise returns the original signal

## Integration Examples

### Paper Trader Integration

```python
from core.decision_engine import DecisionEngine
from core.risk_filter import risk_filter

engine = DecisionEngine()

# In your trading loop
signal, prob = engine.predict(df)
signal = risk_filter(signal, prob, df["close"].pct_change().std())

# Use signal for trading decisions
if signal == "BUY":
    # Execute buy order
    pass
elif signal == "SELL":
    # Execute sell order
    pass
```

### Backtest Loop

```python
from core.decision_engine import DecisionEngine

engine = DecisionEngine()
signals = []

for i in range(200, len(df)):
    window = df.iloc[:i]
    signal, prob = engine.predict(window)
    signals.append((df.iloc[i]['timestamp'], signal, prob))
```

## Testing

Run the smoke test to verify the entire pipeline:

```bash
PYTHONPATH=/home/runner/work/binance_ai_trader/binance_ai_trader python tests/smoke_test_signal_pipeline.py
```

The smoke test:
1. Trains a model on sample data
2. Generates predictions with DecisionEngine
3. Tests risk_filter integration
4. Runs a backtest-style loop

## Requirements

- pandas
- numpy
- scikit-learn
- joblib

## Directory Structure

```
binance_ai_trader/
├── core/
│   ├── feature_builder.py    # Feature extraction
│   ├── decision_engine.py    # Signal generation
│   └── risk_filter.py        # Risk management
├── training/
│   ├── build_target.py       # Target creation
│   └── train_model.py        # Model training
├── models/
│   └── signal_model.pkl      # Trained model (generated)
├── data/
│   └── candles.csv           # Training data (user-provided)
└── tests/
    └── smoke_test_signal_pipeline.py  # Integration test
```
