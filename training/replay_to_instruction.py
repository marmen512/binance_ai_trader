#!/usr/bin/env python3
"""
PAPER TRADING SYSTEM v1 - REPLAY TO INSTRUCTION CONVERTER (OFFLINE ONLY)

⚠ CRITICAL ARCHITECTURAL BOUNDARY:
This file converts HISTORICAL replay decisions into training datasets.
It does NOT observe live behavior or update models during paper trading.

This file MUST NEVER:
- Be called during live paper trading
- Update model weights or parameters
- Create feedback loops from live data
- Run automatically during inference
- Read real-time market data

This file IS PART OF:
- Post-soak pipeline only
- Manual training preparation only
- Offline dataset creation only

SEPARATION OF CONCERNS:
paper trading → replay_log.json → (offline) replay_to_instruction → dataset → manual training

No shortcuts allowed. No online learning. No automatic updates.
Any violation of this boundary would invalidate all paper trading results.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List

from core.logging import setup_logger
from trading.paper_executor import PaperTradingExecutor
from trading.trade_evaluator import DeterministicTradeEvaluator

logger = setup_logger("binance_ai_trader.replay_to_instruction")

# --- NEW: prompt routing constants ---
PROMPT_POLICY_CORRECTION = "POLICY_CORRECTION"
PROMPT_ANTI_HOLD = "ANTI_HOLD_COLLAPSE"
PROMPT_GOOD_REINFORCE = "GOOD_TRADE_REINFORCEMENT"

# --- NEW: dataset weighting ---
BASE_WEIGHT = {
    "BAD": 1.50,
    "OK": 1.00,
    "GOOD": 0.60,
}

PROMPT_MULTIPLIER = {
    PROMPT_POLICY_CORRECTION: 1.20,
    PROMPT_ANTI_HOLD: 0.90,
    PROMPT_GOOD_REINFORCE: 0.70,
}

HOLD_COLLAPSE_PENALTY = 0.40
OVERTRADING_PENALTY = 0.75


def convert_trade_to_instruction(trade):
    prompt_type = None
    weight = 0.0
    
    label = trade["label"]          # BAD | OK | GOOD
    action = trade["action"]        # BUY | SELL | HOLD
    trades_per_day = trade.get("trades_per_day")
 
    # --- BAD trades: strict policy correction ---
    if label == "BAD":
        prompt_type = PROMPT_POLICY_CORRECTION
        weight = BASE_WEIGHT[label] * PROMPT_MULTIPLIER[prompt_type]
    
    # --- GOOD trades: reinforcement only ---
    elif label == "GOOD":
        prompt_type = PROMPT_GOOD_REINFORCE
        weight = BASE_WEIGHT[label] * PROMPT_MULTIPLIER[prompt_type]
    
    # --- OK trades: anti-HOLD collapse only if action was HOLD ---
    elif label == "OK" and action == "HOLD":
        prompt_type = PROMPT_ANTI_HOLD
        weight = BASE_WEIGHT[label] * PROMPT_MULTIPLIER[prompt_type]
    
    else:
        return None
 
    instruction = render_prompt(prompt_type, trade)
    
    # --- HOLD-collapse penalty ---
    if (
        prompt_type == PROMPT_ANTI_HOLD
        and instruction.get("Correct_Action") in ("BUY", "SELL")
    ):
        weight += HOLD_COLLAPSE_PENALTY
    
    # --- overtrading penalty ---
    if trades_per_day is not None and trades_per_day > 20:
        weight *= OVERTRADING_PENALTY
    
    instruction["weight"] = round(weight, 4)
 
    return instruction


def render_prompt(prompt_type, trade):
    # This would be implemented to render the appropriate prompt
    # For now, return a basic instruction
    return f"Analyze trade: {trade}"


class ReplayToInstructionConverter:
    def __init__(self, replay_path: str | Path = Path("ai_data") / "paper" / "replay.jsonl"):
        self.executor = PaperTradingExecutor(replay_path)
        self.evaluator = DeterministicTradeEvaluator()
        
    def convert_to_instruction_dataset(
        self,
        output_path: str | Path,
        instruction_ratio: float = 0.7,
        max_samples: int | None = None,
        seed: int = 42
    ) -> None:
        random.seed(seed)
        
        trades = self.executor.load_replay_buffer()
        evaluations = self.evaluator.evaluate_batch(trades)
        
        instruction_data = []
        
        for eval_result in evaluations:
            # Create trade dict for convert_trade_to_instruction
            trade_dict = {
                "label": eval_result.label,
                "action": eval_result.direction,
                "trades_per_day": eval_result.trade_id.split("_")[0] if "_" in eval_result.trade_id else None  # Simplified
            }
            
            instruction_entry = convert_trade_to_instruction(trade_dict)
            if instruction_entry:
                instruction_data.append(instruction_entry)
        
        if max_samples and len(instruction_data) > max_samples:
            instruction_data = random.sample(instruction_data, max_samples)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in instruction_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        logger.info(f"Created instruction dataset with {len(instruction_data)} samples at {output_path}")
    
    def create_mixed_dataset(
        self,
        stable_instruction_path: str | Path,
        output_path: str | Path,
        replay_ratio: float = 0.3,
        seed: int = 42
    ) -> None:
        random.seed(seed)
        
        stable_path = Path(stable_instruction_path)
        if not stable_path.exists():
            logger.warning(f"Stable instruction dataset not found at {stable_path}")
            return
        
        stable_data = []
        with open(stable_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    stable_data.append(json.loads(line))
        
        replay_data = []
        trades = self.executor.load_replay_buffer()
        evaluations = self.evaluator.evaluate_batch(trades)
        
        for eval_result in evaluations:
            # Create trade dict for convert_trade_to_instruction
            trade_dict = {
                "label": eval_result.label,
                "action": eval_result.direction,
                "trades_per_day": eval_result.trade_id.split("_")[0] if "_" in eval_result.trade_id else None  # Simplified
            }
            
            instruction_entry = convert_trade_to_instruction(trade_dict)
            if instruction_entry:
                replay_data.append(instruction_entry)
        
        total_replay = len(replay_data)
        replay_samples = int(total_replay * replay_ratio)
        stable_samples = len(stable_data)
        
        if replay_samples > total_replay:
            replay_samples = total_replay
        
        selected_replay = random.sample(replay_data, replay_samples) if replay_samples < total_replay else replay_data
        selected_stable = random.sample(stable_data, min(stable_samples, int(replay_samples * (1 - replay_ratio) / replay_ratio)))
        
        mixed_data = selected_replay + selected_stable
        random.shuffle(mixed_data)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            for entry in mixed_data:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        
        logger.info(f"Created mixed dataset: {len(selected_replay)} replay + {len(selected_stable)} stable samples at {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert replay trades to instruction dataset")
    parser.add_argument("--replay-path", type=str, default="ai_data/paper/replay.jsonl", help="Path to replay buffer")
    parser.add_argument("--output-path", type=str, default="ai_data/trading/instruction_dataset.jsonl", help="Output path")
    parser.add_argument("--max-samples", type=int, default=None, help="Maximum samples to generate")
    parser.add_argument("--stable-path", type=str, default=None, help="Path to stable instruction dataset for mixing")
    parser.add_argument("--mix-ratio", type=float, default=0.3, help="Ratio of replay data in mixed dataset")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    
    args = parser.parse_args()
    
    converter = ReplayToInstructionConverter(args.replay_path)
    
    if args.stable_path:
        converter.create_mixed_dataset(
            stable_instruction_path=args.stable_path,
            output_path=args.output_path,
            replay_ratio=args.mix_ratio,
            seed=args.seed
        )
    else:
        converter.convert_to_instruction_dataset(
            output_path=args.output_path,
            max_samples=args.max_samples,
            seed=args.seed
        )


if __name__ == "__main__":
    main()
