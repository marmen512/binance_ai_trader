#!/usr/bin/env python3
"""
CLI interface for two-pass offline fine-tuning system.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.logging import setup_logger
from training.offline_finetuning_two_pass import fine_tune_pass

logger = setup_logger("binance_ai_trader.two_pass_finetuning")


def main():
    parser = argparse.ArgumentParser(description="Two-pass offline fine-tuning CLI")
    
    # Dataset and model arguments
    parser.add_argument("--dataset", required=True, help="Path to instruction dataset")
    parser.add_argument("--model-name", default="microsoft/DialoGPT-medium", help="Base model name")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    
    # Pass configuration
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # PASS 1 command
    pass1_parser = subparsers.add_parser("pass-1", help="PASS 1: BAD-only correction")
    pass1_parser.add_argument("--lr", type=float, default=1e-5, help="Learning rate (default: 1e-5)")
    pass1_parser.add_argument("--epochs", type=int, default=1, help="Number of epochs (default: 1)")
    pass1_parser.add_argument("--batch-size", type=int, default=4, help="Batch size (default: 4)")
    pass1_parser.add_argument("--early-stopping", type=int, default=3, help="Early stopping patience (default: 3)")
    
    # PASS 2 command
    pass2_parser = subparsers.add_parser("pass-2", help="PASS 2: Mixed stabilization")
    pass2_parser.add_argument("--lr", type=float, default=1e-6, help="Learning rate (default: 1e-6)")
    pass2_parser.add_argument("--epochs", type=int, default=1, help="Number of epochs (default: 1)")
    pass2_parser.add_argument("--batch-size", type=int, default=4, help="Batch size (default: 4)")
    pass2_parser.add_argument("--early-stopping", type=int, default=2, help="Early stopping patience (default: 2)")
    
    # Combined command
    combined_parser = subparsers.add_parser("both-passes", help="Run both PASS 1 and PASS 2 sequentially")
    combined_parser.add_argument("--lr-1", type=float, default=1e-5, help="Learning rate for PASS 1 (default: 1e-5)")
    combined_parser.add_argument("--lr-2", type=float, default=1e-6, help="Learning rate for PASS 2 (default: 1e-6)")
    combined_parser.add_argument("--epochs-1", type=int, default=1, help="Epochs for PASS 1 (default: 1)")
    combined_parser.add_argument("--epochs-2", type=int, default=1, help="Epochs for PASS 2 (default: 1)")
    combined_parser.add_argument("--batch-size", type=int, default=4, help="Batch size (default: 4)")
    combined_parser.add_argument("--early-stopping-1", type=int, default=3, help="Early stopping patience for PASS 1 (default: 3)")
    combined_parser.add_argument("--early-stopping-2", type=int, default=2, help="Early stopping patience for PASS 2 (default: 2)")
    
    args = parser.parse_args()
    
    try:
        if args.command == "pass-1":
            logger.info("Starting PASS 1: BAD-only correction")
            fine_tune_pass(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=Path(args.output_dir) / "pass_1",
                learning_rate=args.lr,
                num_epochs=args.epochs,
                batch_size=args.batch_size,
                early_stopping_patience=args.early_stopping,
                save_total_limit=2,
            )
            logger.info("PASS 1 completed successfully")
            
        elif args.command == "pass-2":
            logger.info("Starting PASS 2: Mixed stabilization")
            fine_tune_pass(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=Path(args.output_dir) / "pass_2",
                learning_rate=args.lr,
                num_epochs=args.epochs,
                batch_size=args.batch_size,
                early_stopping_patience=args.early_stopping,
                save_total_limit=2,
            )
            logger.info("PASS 2 completed successfully")
            
        elif args.command == "both-passes":
            logger.info("Starting both PASS 1 and PASS 2 sequentially")
            
            # PASS 1
            logger.info("Step 1: PASS 1 - BAD-only correction")
            fine_tune_pass(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=Path(args.output_dir) / "pass_1",
                learning_rate=args.lr_1,
                num_epochs=args.epochs_1,
                batch_size=args.batch_size,
                early_stopping_patience=args.early_stopping_1,
                save_total_limit=2,
            )
            logger.info("PASS 1 completed")
            
            # PASS 2
            logger.info("Step 2: PASS 2 - Mixed stabilization")
            fine_tune_pass(
                dataset_path=args.dataset,
                model_name=args.model_name,
                output_dir=Path(args.output_dir) / "pass_2",
                learning_rate=args.lr_2,
                num_epochs=args.epochs_2,
                batch_size=args.batch_size,
                early_stopping_patience=args.early_stopping_2,
                save_total_limit=2,
            )
            logger.info("PASS 2 completed")
            logger.info("Both passes completed successfully")
            
        else:
            logger.error(f"Unknown command: {args.command}")
            logger.error("Available commands: pass-1, pass-2, both-passes")
            return 1
            
    except Exception as e:
        logger.error(f"Error during fine-tuning: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
