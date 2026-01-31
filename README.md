# Binance AI Trader

A paper trading system for cryptocurrency trading with strict architectural boundaries to prevent online learning and ensure capital preservation.

## 🚨 Important

This is a **PAPER TRADING SYSTEM** with no online learning. Read [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md) before making any changes.

## Features

- 📊 Paper trading simulation with frozen models
- 🔒 Strict separation between trading and training
- 📈 Backtesting framework for 5-minute strategies
- 🎯 XGBoost-based trading models
- 📉 Comprehensive PnL calculation and reporting
- 🖥️ Multiple interfaces: CLI, Web UI, Streamlit dashboard

## Quick Start

### Prerequisites

- Python 3.10 or higher
- pip and virtualenv

### Installation

1. Clone the repository:
```bash
git clone https://github.com/marmen512/binance_ai_trader.git
cd binance_ai_trader
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .

# For development
pip install -e ".[dev]"
```

### Basic Usage

#### System Check
```bash
python -m interfaces.cli.main doctor
```

#### Web UI
```bash
# Start web server
./run.sh web --config config/config.yaml --host 127.0.0.1 --port 8000

# Or manually
python -m interfaces.web.main --config config/config.yaml --host 127.0.0.1 --port 8000

# Open in browser
# http://127.0.0.1:8000/
```

#### CLI Commands

See available commands:
```bash
python -m interfaces.cli.main --help
```

## Architecture

### Core Principles

1. **No Online Learning** - Models are frozen during paper trading
2. **No Feedback Loops** - Training happens offline, manually
3. **Capital Preservation First** - Conservative by design
4. **Read-Only Monitoring** - No side effects from monitoring

### Directory Structure

```
├── app/                    # Application services
├── backtest/               # Backtesting framework
├── core/                   # Core utilities (logging, config)
├── data_pipeline/          # Data processing
├── execution/              # Trade execution logic
├── features/               # Feature engineering
├── interfaces/             # CLI, Web, GUI interfaces
│   ├── cli/               # Command-line interface
│   ├── web/               # Web interface
│   ├── streamlit/         # Streamlit dashboard
│   └── gui/               # GUI components
├── models/                 # Model inference
├── monitoring/             # System monitoring
├── paper_gate/             # Paper trading gates
├── signals/                # Signal generation
├── strategies/             # Trading strategies
├── targets/                # Target generation
├── trading/                # Trading logic
└── training/               # Offline training (manual only)
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest -m unit
```

### Code Quality

```bash
# Linting
ruff check .

# Formatting
ruff format .

# Type checking
mypy .

# Run all checks
pre-commit run --all-files
```

## Testing

Currently, the project has:
- Unit tests in `app/tests/`
- Test utilities in `scripts/test_trained_model.py`

To run tests:
```bash
pytest app/tests/test_compute_pnl.py
```

## Configuration

Configuration files are in the `config/` directory:
- `config/config.yaml` - Main configuration file

Environment variables can be set in `.env` (see `.env.example`).

## Documentation

- [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md) - System constraints and rules
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [docs/](docs/) - Additional documentation

Key documents:
- [Paper Trading Evaluation](docs/paper_trading_evaluation.md)
- [Advanced Weighting System](docs/advanced_weighting_system.md)
- [Policy Correction System](docs/policy_correction_system.md)

## Monitoring

The system includes built-in monitoring for:
- Trading performance metrics
- System health checks
- Reasoning drift detection
- PnL tracking

## Safety Features

- **Paper Gate**: Validates system state before deployment
- **Anti-Hold Collapse**: Prevents excessive holding
- **Good Trade Reinforcement**: Positive behavior tracking
- **Reasoning Drift Detection**: Monitors AI reasoning quality

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development workflow
- Code style guidelines
- Testing requirements
- Pull request process

**Important**: Review [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md) before contributing.

## License

[Add license information]

## Support

- **Issues**: [GitHub Issues](https://github.com/marmen512/binance_ai_trader/issues)
- **Discussions**: [GitHub Discussions](https://github.com/marmen512/binance_ai_trader/discussions)

## Acknowledgments

Built with a focus on capital preservation and systematic trading principles.