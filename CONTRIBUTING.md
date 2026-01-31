# Contributing to Binance AI Trader

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## 🚨 Critical: Read First

**BEFORE making ANY changes**, you MUST read and understand:
- [ARCHITECTURAL_BOUNDARIES.md](ARCHITECTURAL_BOUNDARIES.md) - Critical system constraints
- This system is a PAPER TRADING SYSTEM with strict NO ONLINE LEARNING rules
- Violations of architectural boundaries will be rejected as critical bugs

## Development Setup

### Prerequisites
- Python 3.10 or higher
- pip and virtualenv

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/marmen512/binance_ai_trader.git
cd binance_ai_trader
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
# Install main dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development Workflow

### Running Tests

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=. --cov-report=html

# Run only unit tests
pytest -m unit

# Run specific test file
pytest tests/test_specific.py
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Run linter (Ruff)
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Run formatter
ruff format .

# Type checking (MyPy)
mypy .
```

### Pre-commit Hooks

Pre-commit hooks will automatically run before each commit:
- Code formatting (Ruff)
- Linting (Ruff)
- Type checking (MyPy)
- YAML/JSON validation
- Trailing whitespace removal
- Architectural boundary checks

To run manually:
```bash
pre-commit run --all-files
```

## Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/add-new-validator` - New features
- `fix/correct-pnl-calculation` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/simplify-gate-logic` - Refactoring

### Commit Messages

Follow conventional commits format:
```
type(scope): subject

body (optional)
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(training): add XGBoost 5m training module
fix(finance): correct FIFO accounting in PnL calculation
docs(readme): add setup instructions
```

### Pull Request Process

1. **Create a branch** from `main` for your changes
2. **Make your changes** following the code style
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run tests and linters** locally
6. **Create a pull request** with:
   - Clear title and description
   - Reference to any related issues
   - Screenshots for UI changes

### Code Style Guidelines

- **Line length**: Maximum 100 characters
- **Imports**: Organized with `isort` (automatic via Ruff)
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

Example:
```python
def compute_pnl_from_orders(orders: list[dict[str, Any]]) -> float:
    """
    Compute realized PnL from a sequence of orders using FIFO accounting.
    
    Args:
        orders: List of order dictionaries with keys: qty, price, side, fee
        
    Returns:
        float: Realized PnL after fees
        
    Example:
        >>> orders = [{"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.1}]
        >>> compute_pnl_from_orders(orders)
        -0.1
    """
    # Implementation
```

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── fixtures/       # Test fixtures and data
```

### Writing Tests

```python
import pytest

def test_compute_pnl_simple():
    """Test simple buy-sell PnL calculation."""
    orders = [
        {"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.1},
        {"qty": 1.0, "price": 110.0, "side": "sell", "fee": 0.1},
    ]
    result = compute_pnl_from_orders(orders)
    assert round(result, 2) == 9.8

@pytest.mark.slow
def test_backtest_full():
    """Test full backtest execution (slow)."""
    # Long-running test
```

### Test Markers

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (skip with `-m "not slow"`)

## Architectural Rules

### ⚠️ FORBIDDEN PATTERNS

**NEVER** do the following (will be auto-rejected):

```python
# ❌ FORBIDDEN - Online learning
if paper_trading_active:
    run_training()

# ❌ FORBIDDEN - Feedback loops
from training.offline_finetuning import train
model.update_from_live_data()

# ❌ FORBIDDEN - Automatic model updates
if performance_degrades:
    auto_train_model()
```

### ✅ SAFE PATTERNS

```python
# ✅ SAFE - Read-only monitoring
metrics = monitor(replay_log)

# ✅ SAFE - Manual offline training
# (only in training/ directory, manual execution)
def train_offline():
    # Load historical data
    # Train model
    # Save checkpoint
```

## Documentation

### Update Documentation

When making changes, update relevant documentation:
- Module docstrings
- Function/class docstrings
- README.md sections
- Architecture docs if changing system design

### Adding New Modules

New modules should include:
```python
"""
Module description.

This module provides [functionality].

Example:
    >>> from module import function
    >>> result = function()
"""
```

## Getting Help

- **Questions**: Open a discussion on GitHub
- **Bugs**: Open an issue with reproduction steps
- **Features**: Open an issue with use case description

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the project's technical standards

## License

By contributing, you agree that your contributions will be licensed under the project's license.

---

Thank you for contributing to make this project better! 🚀
