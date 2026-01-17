#!/usr/bin/env python3
"""
⚠ WARNING: This module performs OFFLINE TRAINING.
It must never be imported or executed during paper trading or live inference.

PAPER TRADING SYSTEM v1 - OFFLINE FINE-TUNING (MANUAL ONLY)

CRITICAL ARCHITECTURAL BOUNDARY:
This file is NOT executed automatically during paper trading.
It MUST ONLY be run:
- Manually by human decision
- Intentionally after soak testing completes
- On curated datasets after human review
- NEVER during inference or monitoring

This module MUST NEVER:
- Be called from inference code
- Be called from monitoring scripts
- Be called from CI pipelines
- Be triggered automatically
- Read live trading data
- Update model during paper trading

OFFLINE TRAINING HAPPENS:
- Once per training cycle
- On historical replay data only
- After explicit human approval
- With manual model replacement

Any violation of these boundaries would invalidate all paper trading results.
The model is intentionally frozen during paper trading mode.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from core.logging import setup_logger
from training.replay_to_instruction import convert_trade_to_instruction
from training.offline_finetuning import fine_tune_pass

logger = setup_logger("binance_ai_trader.offline_finetuning")


def run_pass_1(
    dataset_path: str | Path,
    model_name: str,
    output_dir: str | Path,
    batch_size: int = 4
) -> Dict[str, Any]:
    """PASS 1: BAD-only correction."""
    logger.info("Starting PASS 1: BAD-only correction")
    
    # Create BAD-only dataset using single source of truth
    bad_dataset_path = Path(output_dir) / "pass_1_dataset.jsonl"
    with open(dataset_path, "r") as f_in, open(bad_dataset_path, "w") as f_out:
        for line in f_in:
            trade = json.loads(line)
            instruction = convert_trade_to_instruction(trade)
            if instruction:  # Only keep BAD trades
                f_out.write(json.dumps(instruction) + "\n")
    
    # Fine-tune with PASS 1 parameters
    fine_tune_pass(
        dataset_path=str(bad_dataset_path),
        model_name=model_name,
        output_dir=Path(output_dir) / "pass_1",
        learning_rate=1e-5,  # MANDATORY: LR = 1e-5
        num_epochs=1,  # MANDATORY: Epochs = 1
        batch_size=batch_size,
        early_stopping_patience=3,
        save_total_limit=2,
    )
    
    logger.info("PASS 1 completed")
    return {
        "pass": 1,
        "dataset_path": str(bad_dataset_path),
        "model_output": str(Path(output_dir) / "pass_1"),
    }


def run_pass_2(
    dataset_path: str | Path,
    model_name: str,
    output_dir: str | Path,
    batch_size: int = 4
) -> Dict[str, Any]:
    """PASS 2: Mixed stabilization (BAD + OK + GOOD)."""
    logger.info("Starting PASS 2: Mixed stabilization")
    
    # Create mixed dataset using single source of truth
    mixed_dataset_path = Path(output_dir) / "pass_2_dataset.jsonl"
    with open(dataset_path, "r") as f_in, open(mixed_dataset_path, "w") as f_out:
        for line in f_in:
            trade = json.loads(line)
            instruction = convert_trade_to_instruction(trade)
            if instruction:  # Keep all labels for PASS 2
                f_out.write(json.dumps(instruction) + "\n")
    
    # Fine-tune with PASS 2 parameters
    fine_tune_pass(
        dataset_path=str(mixed_dataset_path),
        model_name=model_name,
        output_dir=Path(output_dir) / "pass_2",
        learning_rate=5e-6,  # MANDATORY: LR = 5e-6
        num_epochs=1,  # MANDATORY: Epochs = 1
        batch_size=batch_size,
        early_stopping_patience=2,
        save_total_limit=2,
    )
    
    logger.info("PASS 2 completed")
    return {
        "pass": 2,
        "dataset_path": str(mixed_dataset_path),
        "model_output": str(Path(output_dir) / "pass_2"),
    }


def run_both_passes(
    dataset_path: str | Path,
    model_name: str,
    output_dir: str | Path,
    batch_size: int = 4
) -> Dict[str, Any]:
    """Run both PASS 1 and PASS 2 sequentially."""
    logger.info("Starting both PASS 1 and PASS 2 sequentially")
    
    # PASS 1: BAD-only correction
    pass_1_result = run_pass_1(dataset_path, model_name, output_dir, batch_size)
    
    # PASS 2: Mixed stabilization
    pass_2_result = run_pass_2(dataset_path, model_name, output_dir, batch_size)
    
    logger.info("Both passes completed successfully")
    return {
        "pass_1": pass_1_result,
        "pass_2": pass_2_result,
    }


def main():
    parser = argparse.ArgumentParser(description="Unified offline fine-tuning with two-pass modes")
    
    # Common arguments
    parser.add_argument("--dataset", required=True, help="Path to replay dataset")
    parser.add_argument("--model-name", default="microsoft/DialoGPT-medium", help="Base model name")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--batch-size", type=int, default=4, help="Batch size")
    
    # Mode selection
    subparsers = parser.add_subparsers(dest="mode", help="Fine-tuning mode")
    
    # PASS 1 mode
    pass1_parser = subparsers.add_parser("pass-1", help="PASS 1: BAD-only correction")
    
    # PASS 2 mode
    pass2_parser = subparsers.add_parser("pass-2", help="PASS 2: Mixed stabilization")
    
    # Both passes mode
    both_parser = subparsers.add_parser("both", help="Run both PASS 1 and PASS 2")
    
    args = parser.parse_args()
    
    try:
        if args.mode == "pass-1":
            result = run_pass_1(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=args.output_dir,
                batch_size=args.batch_size
            )
            print(f"PASS 1 completed: model saved to {result['model_output']}")
            
        elif args.mode == "pass-2":
            result = run_pass_2(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=args.output_dir,
                batch_size=args.batch_size
            )
            print(f"PASS 2 completed: model saved to {result['model_output']}")
            
        elif args.mode == "both":
            result = run_both_passes(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=args.output_dir,
                batch_size=args.batch_size
            )
            print(f"Both passes completed: models saved to {result['pass_1']['model_output']} and {result['pass_2']['model_output']}")
            
        else:
            logger.error(f"Unknown mode: {args.mode}")
            logger.error("Available modes: pass-1, pass-2, both")
            return 1
            
    except Exception as e:
        logger.error(f"Error during fine-tuning: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
