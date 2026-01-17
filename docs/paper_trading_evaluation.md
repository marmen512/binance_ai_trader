# Paper Trading Evaluation and Offline Fine-Tuning Pipeline

This directory contains the implementation of a deterministic paper-trading evaluation and offline fine-tuning pipeline for LLM-based trading agents.

## Components

### 1. Paper Trading Executor (`trading/paper_executor.py`)
- **Purpose**: Opens and closes paper trades, maintains state
- **Features**:
  - Trade execution with BUY/SELL/HOLD decisions
  - JSONL replay buffer for logging all trades
  - PnL calculation for closed trades
  - Real-time trade state management

### 2. Deterministic Trade Evaluator (`trading/trade_evaluator.py`)
- **Purpose**: Evaluates completed trades using strict +15% PnL rule
- **Features**:
  - Deterministic evaluation (GOOD/OK/BAD)
  - No interactive behavior or questions
  - Analysis and improvement suggestions
  - Batch evaluation capabilities

### 3. Replay to Instruction Converter (`training/replay_to_instruction.py`)
- **Purpose**: Converts replay trades to instruction-style dataset
- **Features**:
  - Creates instruction-response pairs from trade data
  - Supports mixing with stable instruction data
  - Configurable sample ratios and limits
  - Avoids catastrophic forgetting

### 4. Offline Fine-Tuning (`training/offline_finetuning.py`)
- **Purpose**: Fine-tunes LLM models on replay data
- **Features**:
  - Low learning rate training
  - Early stopping and validation
  - Mixed dataset support
  - Model checkpointing

## CLI Commands

### Evaluate Paper Trades
```bash
binance_ai_trader evaluate-paper-trades \
    --replay-path ai_data/paper/replay.jsonl \
    --output-path ai_data/paper/evaluations.json
```

### Convert Replay to Instruction Dataset
```bash
binance_ai_trader convert-replay-to-instruction \
    --replay-path ai_data/paper/replay.jsonl \
    --output-path ai_data/trading/instruction_dataset.jsonl \
    --max-samples 1000
```

### Mix with Stable Data
```bash
binance_ai_trader convert-replay-to-instruction \
    --replay-path ai_data/paper/replay.jsonl \
    --stable-path ai_data/trading/stable_instructions.jsonl \
    --output-path ai_data/trading/mixed_dataset.jsonl \
    --mix-ratio 0.3
```

### Offline Fine-Tuning
```bash
binance_ai_trader offline-finetune \
    --train-path ai_data/trading/instruction_dataset.jsonl \
    --model-name microsoft/DialoGPT-medium \
    --output-dir ai_data/models/llm_trader \
    --learning-rate 1e-5 \
    --num-epochs 3
```

## Evaluation Rules

- **GOOD**: PnL ≥ +15%
- **OK**: 0% < PnL < +15%
- **BAD**: PnL ≤ 0%

## Key Constraints

1. **Paper Only**: No real money trading
2. **Deterministic**: No questions or interactive behavior
3. **Offline Learning**: No online backpropagation
4. **Low Learning Rate**: Prevents catastrophic forgetting
5. **Mixed Data**: Combines replay with stable instruction data

## File Structure

```
ai_data/
├── paper/
│   ├── replay.jsonl          # Trade replay buffer
│   ├── evaluations.json       # Trade evaluations
│   └── state.json            # Paper trading state
├── trading/
│   ├── instruction_dataset.jsonl    # Instruction format data
│   └── mixed_dataset.jsonl          # Mixed replay + stable data
└── models/
    └── llm_trader/           # Fine-tuned model
```

## Integration with Existing Pipeline

The paper trading evaluation pipeline integrates seamlessly with the existing 5m trading infrastructure:

- Uses existing `PaperTradeOnceResult` from `trading/paper_trading.py`
- Compatible with current CLI structure
- Maintains strict no-overwrite policies
- Follows existing logging and monitoring patterns
