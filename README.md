# Binance AI Trader

An AI-powered trading system for Binance with adaptive learning, paper trading, and strict architectural boundaries.

## Overview

Binance AI Trader is a comprehensive trading system that combines:
- **AI/ML Models**: XGBoost-based classification for trade signals
- **Paper Trading**: Risk-free testing environment with full execution simulation
- **Adaptive Learning**: Shadow model learns from paper trades (isolated pipeline)
- **Safety-First Design**: Architectural boundaries prevent accidental live trading
- **Modular Architecture**: Clean separation between data, features, signals, and execution

### Key Features

- ✅ **Paper Trading Mode**: Full simulation with realistic fills, fees, and slippage
- ✅ **5m BTC Pipeline**: Complete data → features → targets → training → signals → execution
- ✅ **Adaptive Learning**: Shadow model learns from paper trades without affecting production
- ✅ **Model Registry**: Versioned model storage with promotion gates
- ✅ **Drift Detection**: Automatic performance monitoring and degradation alerts
- ✅ **Web UI**: Real-time monitoring dashboard
- ✅ **CLI Tools**: Command-line interface for all operations

## Installation

### Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### Setup

```bash
# Clone repository
git clone https://github.com/marmen512/binance_ai_trader.git
cd binance_ai_trader

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Configuration

1. Copy example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings (API keys for paper trading only)

## Usage

### Command Line Interface

```bash
# Check system health
python -m interfaces.cli.main doctor

# Get paper trading status
python -m interfaces.cli.main paper-status

# Run adaptive learning commands
python -m adaptive.cli status      # Check adaptive system status
python -m adaptive.cli init        # Initialize adaptive system
python -m adaptive.cli evaluate    # Evaluate shadow model promotion
python -m adaptive.cli promote     # Promote shadow to frozen (if approved)
```

### Web Interface

```bash
# Start web server
./run.sh web --config config/config.yaml --host 127.0.0.1 --port 8000

# Or using Python directly
python -m interfaces.web.main --config config/config.yaml --host 127.0.0.1 --port 8000
```

Then open: http://127.0.0.1:8000

### Paper Trading

See [RUNBOOK_PAPER_5M.md](RUNBOOK_PAPER_5M.md) for complete paper trading procedures.

Quick start:
```bash
# Verify all systems
python main.py verify-datasets-5m --config config/config.yaml
python main.py verify-features-5m --config config/config.yaml
python main.py paper-gate-5m --config config/config.yaml

# Start paper trading (if gate passes)
# Follow runbook for exact procedures
```

### Adaptive Learning

The adaptive system runs in complete isolation from paper trading:

```bash
# Initialize with frozen model
python -m adaptive.cli init \
  --frozen-model-id m_baseline \
  --frozen-artifact-path model_registry/models/frozen.pkl

# System will learn from paper trades automatically
# Check status periodically
python -m adaptive.cli status

# Evaluate for promotion when ready
python -m adaptive.cli evaluate

# Promote if tests pass
python -m adaptive.cli promote
```

See [adaptive/README.md](adaptive/README.md) for complete adaptive learning documentation.

## Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     DATA PIPELINE                            │
│  Binance API → OHLCV → Features → Targets → Training        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                    FROZEN MODEL (Production)                 │
│              Generates signals, READ ONLY                    │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   EXECUTION ENGINE                           │
│         Paper Trading Only (no live execution)               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│              ADAPTIVE LEARNING (Isolated)                    │
│  Shadow Model ← Paper Trades → Drift Monitor → Promotion    │
│              NEVER affects paper trading                     │
└─────────────────────────────────────────────────────────────┘
```

### Architectural Boundaries

**CRITICAL INVARIANTS:**

1. **No Online Learning in Production**: The frozen model never learns during paper trading
2. **Shadow Isolation**: Shadow model NEVER generates trading signals
3. **Paper Only**: No live trading - system is paper trading only
4. **Capital Preservation**: HOLD is default, conservative by design
5. **Explicit Promotion**: Shadow → Frozen requires passing all tests

See [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md) for complete details.

### Directory Structure

```
binance_ai_trader/
├── adaptive/              # Adaptive learning system (isolated)
│   ├── shadow_model.py    # Shadow model for learning
│   ├── feature_logger.py  # Trade feature logging
│   ├── online_trainer.py  # Online training loop
│   ├── drift_monitor.py   # Performance monitoring
│   ├── model_registry.py  # Versioned model storage
│   └── promotion_gate.py  # Promotion decision logic
├── data_pipeline/         # Data ingestion and processing
├── features/              # Feature engineering
├── targets/               # Target variable generation
├── models/                # Model training and inference
├── signals/               # Signal generation
├── execution/             # Execution engine (paper only)
├── backtest/              # Backtesting framework
├── interfaces/            # CLI and Web interfaces
├── tests/                 # Test suite
└── config/                # Configuration files
```

## Roadmap

### Current Status: ✅ Paper Trading v1 + Adaptive Learning

- [x] 5m BTC data pipeline
- [x] Feature engineering (technical, market, sentiment)
- [x] Target generation with forward-looking outcomes
- [x] XGBoost training pipeline
- [x] Signal generation with confidence thresholds
- [x] Paper trading execution engine
- [x] Backtest framework with walk-forward validation
- [x] Paper gate with safety checks
- [x] Adaptive learning system (shadow model)
- [x] Drift monitoring and model registry
- [x] Web UI for monitoring

### Phase 2: Enhanced Adaptive Learning (In Progress)

- [ ] River-based incremental learning
- [ ] Advanced drift detection (PSI, KL divergence)
- [ ] Continuous walk-forward testing
- [ ] Automated A/B testing (frozen vs shadow)
- [ ] Feature importance tracking
- [ ] Ensemble methods for promotion decisions

### Phase 3: Copy Trading Integration (Planned)

- [ ] Leader filtering by PnL (scraping/RapidAPI)
- [ ] Entry point analysis with feature extraction
- [ ] Hybrid signals (own model + leader signals)
- [ ] Leader trust scoring
- [ ] Copy trading in paper mode only

### Phase 4: Performance & Scale (Planned)

- [ ] PyArrow-based log sharding for efficiency
- [ ] Incremental feature computation
- [ ] Model serving optimization
- [ ] Multi-symbol support
- [ ] Real-time monitoring dashboard

### Phase 5: Live Trading (Future, Post-Paper Success)

**Requirements before live mode:**
- ✅ 4+ weeks successful paper trading
- ✅ All safety checks passing consistently
- ✅ Max drawdown < 20%
- ✅ Winrate 52-56% maintained
- ✅ Profit factor > 1.15

**Live mode safety:**
- Maximum risk: 1% per trade
- Maximum leverage: 1x
- Hard stop loss: 3% daily, 8% weekly
- Kill switch on 10 consecutive losses
- Rate limiting on order placement
- Extra execution safety checks

**Note**: Live trading is NOT currently implemented and requires significant additional safety measures.

## Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/adaptive/

# Run with coverage
pytest --cov=adaptive tests/adaptive/

# Run manual integration tests
python tests/adaptive/manual_test.py
```

## Documentation

- [README.md](README.md) - This file
- [RUNBOOK_PAPER_5M.md](RUNBOOK_PAPER_5M.md) - Paper trading procedures
- [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md) - System invariants
- [adaptive/README.md](adaptive/README.md) - Adaptive learning guide
- [adaptive/INTEGRATION_GUIDE.md](adaptive/INTEGRATION_GUIDE.md) - Integration instructions
- [adaptive/QUICKSTART.md](adaptive/QUICKSTART.md) - Quick start guide

## Safety & Risk Management

**This system is intentionally conservative:**

1. **Default Action**: HOLD (not BUY/SELL)
2. **Paper Trading Only**: No live trading implemented
3. **Frozen Model**: Production model never learns online
4. **Shadow Isolation**: Learning model never trades
5. **Explicit Promotion**: Manual approval required
6. **Drift Detection**: Auto-pause on degradation
7. **Hard Limits**: Trade frequency, daily/weekly loss limits

## Contributing

1. Read [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md)
2. All changes must preserve paper-only constraint
3. No online learning in production path
4. Tests required for new features
5. Documentation for architectural changes

## License

MIT License - see [LICENSE](LICENSE) file

## Disclaimer

**FOR EDUCATIONAL PURPOSES ONLY**

This software is provided for educational and research purposes. Trading cryptocurrencies involves substantial risk of loss. The authors and contributors are not responsible for any financial losses incurred through the use of this software.

**USE AT YOUR OWN RISK**