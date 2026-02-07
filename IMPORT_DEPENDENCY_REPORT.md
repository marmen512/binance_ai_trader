# Import Dependency Report

Generated: 2026-02-07

## Executive Summary

### ✅ No Import Violations Detected

Training modules correctly avoid importing from:
- `execution/*`
- `execution_safety/*`
- `trading/*` (direct imports)

## Import Statistics

| Directory | Python Files | Total Imports | Protected Imports |
|-----------|-------------|---------------|-------------------|
| training/ | 6 | 28 | 0 |
| features/ | 8 | 44 | 0 |
| models/ | 3 | 18 | 0 |
| backtest/ | 6 | 23 | 0 |
| monitoring/ | 3 | 15 | 0 |

## Detailed Import Analysis

### Directory: `backtest/`

#### `backtest/engine.py`

#### `backtest/metrics.py`

#### `backtest/report.py`

#### `backtest/runner_5m.py`

#### `backtest/sanity_report.py`

#### `backtest/validators_5m.py`

### Directory: `features/`

#### `features/copy_trader_stats.py`

#### `features/pipeline.py`

#### `features/pipeline_5m.py`

#### `features/technical.py`

#### `features/time_features.py`

#### `features/validators.py`

#### `features/volatility.py`

#### `features/volume.py`

### Directory: `models/`

#### `models/classification_inference.py`

#### `models/inference.py`

#### `models/predictor.py`

**MODEL_REGISTRY imports:**
- Line 8: `model_registry.registry`

### Directory: `monitoring/`

#### `monitoring/alerts.py`

#### `monitoring/events.py`

#### `monitoring/metrics.py`

### Directory: `training/`

#### `training/advanced_weighting.py`

#### `training/offline_finetuning.py`

**TRAINING imports:**
- Line 10: `training.offline_finetuning_core`

#### `training/offline_finetuning_core.py`

#### `training/offline_finetuning_two_pass.py`

**TRAINING imports:**
- Line 14: `training.offline_finetuning_core`

#### `training/reasoning_drift_detector.py`

#### `training/replay_to_instruction.py`

## Protected Module Import Matrix

Shows which modules import from protected directories:

| Module | execution | execution_safety | paper_gate | trading |
|--------|-----------|------------------|------------|---------|
| training/ | 0 | 0 | 0 | 0 |
| features/ | 0 | 0 | 0 | 0 |
| models/ | 0 | 0 | 0 | 0 |
| backtest/ | 0 | 0 | 0 | 0 |
| monitoring/ | 0 | 0 | 0 | 0 |
