# Policy Correction System Implementation

This document describes the complete policy correction system that implements the deterministic trading policy correction engine as specified in the requirements.

## Overview

The policy correction system is designed to improve trading decision quality by:
- Evaluating completed paper trades with deterministic rules
- Generating corrective logic for bad trades
- Creating weighted training datasets to reinforce good behavior
- Prioritizing capital preservation over profit optimization

## Core Components

### 1. Policy Corrector (`trading/policy_corrector.py`)
**Purpose**: Implements deterministic policy correction logic

**Key Features**:
- **GOOD trades** (PnL ≥ +15%): CONFIRM - Logic was correct
- **OK trades** (0% < PnL < +15%): REFINE - Logic needs improvement
- **BAD trades** (PnL ≤ 0%): REJECT - Logic was wrong, HOLD would be better

**Correction Logic**:
```python
if label == "GOOD":
    correction_type = "CONFIRM"
    correct_action = trade.direction
elif label == "BAD":
    correction_type = "REJECT"
    correct_action = "HOLD"  # Always safer
else:  # OK
    correction_type = "REFINE"
    correct_action = self._determine_ok_correction(trade)
```

### 2. Policy Correction Prompt Handler (`trading/policy_correction_prompt.py`)
**Purpose**: Formats prompts for LLM-based policy correction

**Strict Output Format**:
```
Correct_Action: BUY | SELL | HOLD
Correction_Type: CONFIRM | REJECT | REFINE
Reasoning:
- One concise paragraph (3–5 sentences max)
- Focus on logic, not hindsight
- Explicitly mention risk, uncertainty, or lack of edge
- If rejecting, explain why HOLD would have preserved capital
```

### 3. Enhanced Replay Converter (`training/enhanced_replay_converter.py`)
**Purpose**: Creates weighted training datasets with policy corrections

**Weighting Strategy**:
- **BAD corrections**: 1.5x weight (highest priority)
- **OK corrections**: 1.2x weight (medium priority)
- **GOOD corrections**: 0.8x weight (lower priority)

This ensures the model learns more from mistakes than successes.

## CLI Commands

### Generate Policy Corrections
```bash
binance_ai_trader correct-policy \
    --replay-path ai_data/paper/replay.jsonl \
    --evaluations-path ai_data/paper/evaluations.json \
    --output-path ai_data/paper/corrections.json
```

### Create Weighted Training Dataset
```bash
binance_ai_trader create-policy-correction-dataset \
    --replay-path ai_data/paper/replay.jsonl \
    --stable-path ai_data/trading/stable_instructions.jsonl \
    --output-path ai_data/trading/weighted_training.jsonl \
    --policy-weight 2.0 \
    --stable-weight 1.0
```

### Offline Fine-Tuning with Policy Corrections
```bash
binance_ai_trader offline-finetune \
    --train-path ai_data/trading/weighted_training.jsonl \
    --model-name microsoft/DialoGPT-medium \
    --learning-rate 1e-5 \
    --num-epochs 3
```

## Training Pipeline Integration

### Phase 1: Evaluation
1. Run paper trades and log to replay buffer
2. Evaluate trades with deterministic rules
3. Generate policy corrections

### Phase 2: Dataset Creation
1. Convert corrections to instruction format
2. Apply weighted sampling (BAD > OK > GOOD)
3. Mix with stable instruction data

### Phase 3: Fine-Tuning
1. Use low learning rate (1e-5) to prevent catastrophic forgetting
2. Train on weighted dataset
3. Validate on hold-out set

## Expected Behavior Changes

After 1-2 offline fine-tuning cycles:

- **HOLD decisions increase**: Model becomes more conservative
- **BAD trades decrease**: Model avoids low-quality setups
- **Profit factor stabilizes**: Not necessarily "better" but more consistent
- **Paper gate may still be NO-GO**: But for different, more refined reasons

## Key Principles

1. **Capital Preservation First**: HOLD is always the safe default
2. **Risk Avoidance**: Prefer no trade over uncertain trades
3. **Asymmetric Edge Required**: Only trade when edge is clear
4. **Learn from Mistakes**: BAD trades get highest learning weight
5. **Stability Over Profit**: Consistent performance over occasional wins

## File Structure

```
ai_data/
├── paper/
│   ├── replay.jsonl              # Original trade records
│   ├── evaluations.json           # Trade evaluations (GOOD/OK/BAD)
│   └── corrections.json          # Policy corrections
└── trading/
    ├── policy_corrections.jsonl   # Instruction format corrections
    ├── weighted_training.jsonl    # Weighted dataset for training
    └── stable_instructions.jsonl  # Existing stable data
```

## Integration with Existing System

The policy correction system integrates seamlessly with:
- Existing paper trading infrastructure
- Current CLI command structure
- Offline fine-tuning pipeline
- Model evaluation and validation systems

All components maintain strict no-overwrite policies and follow existing logging patterns.
