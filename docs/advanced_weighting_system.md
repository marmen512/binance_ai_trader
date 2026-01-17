# Advanced Dataset Weighting System

This document describes the comprehensive weighting formula that ensures balanced learning from trading data.

## 🎯 Objective

Create a balanced dataset where:
- **BAD trades** are learned from most strongly (avoid mistakes)
- **OK trades** provide moderate corrections (improve decisions)
- **GOOD trades** stabilize behavior (cement correct logic)
- **Anti-HOLD** prevents over-caution (capture opportunities)

## 🧮 Final Weighting Formula

```
sample_weight = (
    base_weight[label] * prompt_multiplier[type] + hold_collapse_penalty
) * overtrading_penalty
```

### Where:

1. **Base Weights by Label**
   - BAD: 1.50
   - OK: 1.00  
   - GOOD: 0.60

2. **Prompt Type Multipliers**
   - POLICY_CORRECTION (BAD): ×1.20
   - ANTI_HOLD_COLLAPSE: ×0.90
   - GOOD_TRADE_REINFORCEMENT: ×0.70

3. **HOLD Collapse Penalty**
   - Applied when: action == HOLD ∧ label ∈ {GOOD, OK} ∧ anti_hold_prompt → Correct_Action ∈ {BUY, SELL}
   - Penalty: +0.40

4. **Overtrading Penalty**
   - Applied when: trades_per_day > 20
   - Penalty: ×0.75

## 🧩 Real-World Examples

### ❌ BAD Trade (Policy Correction)
```
1.50 × 1.20 = 1.80
```

### ⚠️ OK + Anti-HOLD (Missed Edge)
```
1.00 × 0.90 + 0.40 = 1.30
```

### ✅ GOOD Trade (Reinforcement)
```
0.60 × 0.70 = 0.42
```

### 👉 Key Insight: BAD ≈ 4× More Important Than GOOD

This ensures the model learns 4 times more from mistakes than from successes.

## 📊 Expected Dataset Balance

After proper sampling:

- **Σ(weight BAD)**: 45-55%
- **Σ(weight OK)**: 30-40%
- **Σ(weight GOOD)**: 10-20%

### 🚨 Health Checkpoints

- If GOOD > 25% → Model stops believing in itself
- If BAD < 45% → Insufficient mistake learning
- If OK > 50% → Too much correction, not enough stabilization

## ❌ What's Forbidden

- **Equal weights**: All labels treated equally
- **Oversampling GOOD**: Encourages overtrading
- **Reward for frequency**: No "more trades = better"
- **PnL-based weights**: Weight depends on outcome magnitude, not decision quality

## 🧠 Why This Works

### 1. **Strong Mistake Learning**
BAD trades with 1.80 weight dominate learning, ensuring the model strongly avoids repeating errors.

### 2. **Balanced Opportunity Learning**
Anti-HOLD entries (1.30 weight) teach the model when HOLD is over-conservative.

### 3. **Stabilization Without Overconfidence**
GOOD trades (0.42 weight) reinforce correct behavior without making the model "believe in itself."

### 4. **Natural Frequency Regulation**
The weighting naturally leads to 5-20 trades/day:
- BAD corrections discourage frequent trading
- Anti-HOLD encourages necessary action
- GOOD reinforcement maintains discipline

## 🛠️ Implementation

### CLI Commands

```bash
# Analyze weighting system
binance_ai_trader analyze-weighting-system \
    --replay-path ai_data/paper/replay.jsonl

# Create comprehensive dataset with advanced weighting
binance_ai_trader create-policy-correction-dataset \
    --comprehensive \
    --policy-weight 2.0 \
    --anti-hold-weight 1.5 \
    --stable-weight 1.0
```

### Weight Validation

The system includes automatic validation:

```python
# Example calculations
examples = weighting_system.validate_weighting_examples()
# Returns:
# {
#     "BAD_policy_correction": 1.80,
#     "OK_anti_hold_collapse": 1.30,
#     "GOOD_reinforcement": 0.42,
#     "BAD_to_GOOD_ratio": 4.3
# }
```

## 📋 Configuration

All weighting parameters are configurable via `WeightingConfig`:

```python
config = WeightingConfig(
    BAD_BASE_WEIGHT=1.50,
    OK_BASE_WEIGHT=1.00,
    GOOD_BASE_WEIGHT=0.60,
    POLICY_CORRECTION_MULTIPLIER=1.20,
    ANTI_HOLD_COLLAPSE_MULTIPLIER=0.90,
    GOOD_TRADE_REINFORCEMENT_MULTIPLIER=0.70,
    HOLD_COLLAPSE_PENALTY=0.40,
    OVERTRADING_PENALTY_MULTIPLIER=0.75,
    MAX_TRADES_PER_DAY=20.0,
    MAX_GOOD_RATIO=0.25
)
```

## 🧪 Expected Training Outcomes

### After 1-2 Fine-Tuning Cycles:

1. **HOLD Behavior**:
   - Becomes conditional, not automatic
   - Applied only when edge is unclear
   - Reduces excessive risk aversion

2. **Trade Frequency**:
   - Naturally settles to 5-20 trades/day
   - Avoids both overtrading and undertrading
   - Responds to market conditions, not frequency targets

3. **Decision Quality**:
   - BAD trades decrease significantly
   - OK trades improve with corrections
   - GOOD trades stabilize correct patterns

4. **Performance Stability**:
   - Reduced V-shape equity curves
   - More consistent risk management
   - Profit factor stabilizes (not necessarily "better")

## 🔍 Monitoring

The system provides comprehensive analysis:

- **Dataset balance**: Verify 45-55% BAD, 30-40% OK, 10-20% GOOD
- **Health warnings**: Alert if balance is outside expected ranges
- **Weight distribution**: Show actual vs expected weight percentages
- **Example validation**: Confirm BAD:GOOD ≈ 4:1 ratio

This ensures the training dataset is optimally balanced for learning robust trading behavior.
