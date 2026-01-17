#!/usr/bin/env python3
"""
CLI commands for paper trading evaluation and offline fine-tuning.
"""

from __future__ import annotations

from pathlib import Path

from core.logging import setup_logger
from interfaces.cli.output import CommandResult, render
from trading.paper_executor import PaperTradingExecutor
from trading.trade_evaluator import DeterministicTradeEvaluator
from trading.policy_corrector import DeterministicPolicyCorrector
from training.replay_to_instruction import ReplayToInstructionConverter
from training.offline_finetuning import OfflineFineTuner
from training.enhanced_replay_converter import EnhancedReplayConverter
from training.good_trade_reinforcement_converter import GoodTradeReinforcementConverter
from training.advanced_weighting import AdvancedWeightingSystem, WeightingConfig

logger = setup_logger("binance_ai_trader.cli")


def evaluate_paper_trades_command(replay_path: str, output_path: str) -> CommandResult:
    try:
        executor = PaperTradingExecutor(replay_path)
        evaluator = DeterministicTradeEvaluator()
        
        trades = executor.load_replay_buffer()
        if not trades:
            return CommandResult(
                ok=False,
                message="No trades found in replay buffer",
                data={"trades_count": 0}
            )
        
        evaluations = evaluator.evaluate_batch(trades)
        
        evaluator.save_evaluations(evaluations, output_path)
        
        good_trades = sum(1 for e in evaluations if e.label == "GOOD")
        ok_trades = sum(1 for e in evaluations if e.label == "OK")
        bad_trades = sum(1 for e in evaluations if e.label == "BAD")
        
        avg_pnl = sum(e.pnl_pct for e in evaluations) / len(evaluations) if evaluations else 0
        
        return CommandResult(
            ok=True,
            message=f"Evaluated {len(evaluations)} trades",
            data={
                "total_trades": len(evaluations),
                "good_trades": good_trades,
                "ok_trades": ok_trades,
                "bad_trades": bad_trades,
                "avg_pnl_pct": round(avg_pnl, 2),
                "output_path": output_path
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to evaluate paper trades: {e}")
        return CommandResult(
            ok=False,
            message=f"Evaluation failed: {str(e)}",
            data={}
        )


def convert_replay_to_instruction_command(
    replay_path: str,
    output_path: str,
    max_samples: int | None = None,
    stable_path: str | None = None,
    mix_ratio: float = 0.3
) -> CommandResult:
    try:
        converter = ReplayToInstructionConverter(replay_path)
        
        if stable_path:
            converter.create_mixed_dataset(
                stable_instruction_path=stable_path,
                output_path=output_path,
                replay_ratio=mix_ratio
            )
            method = "mixed"
        else:
            converter.convert_to_instruction_dataset(
                output_path=output_path,
                max_samples=max_samples
            )
            method = "replay_only"
        
        return CommandResult(
            ok=True,
            message=f"Created {method} instruction dataset",
            data={
                "method": method,
                "output_path": output_path,
                "max_samples": max_samples,
                "mix_ratio": mix_ratio if stable_path else None
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to convert replay to instruction dataset: {e}")
        return CommandResult(
            ok=False,
            message=f"Conversion failed: {str(e)}",
            data={}
        )


def offline_finetune_command(
    train_path: str,
    model_name: str = "microsoft/DialoGPT-medium",
    val_path: str | None = None,
    output_dir: str = "ai_data/models/llm_trader",
    learning_rate: float = 1e-5,
    batch_size: int = 4,
    num_epochs: int = 3
) -> CommandResult:
    try:
        tuner = OfflineFineTuner(
            model_name=model_name,
            output_dir=output_dir,
            learning_rate=learning_rate,
            batch_size=batch_size,
            num_epochs=num_epochs
        )
        
        tuner.fine_tune(
            train_path=train_path,
            val_path=val_path
        )
        
        return CommandResult(
            ok=True,
            message="Offline fine-tuning completed successfully",
            data={
                "model_name": model_name,
                "output_dir": output_dir,
                "learning_rate": learning_rate,
                "batch_size": batch_size,
                "num_epochs": num_epochs,
                "train_path": train_path,
                "val_path": val_path
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to offline fine-tune model: {e}")
        return CommandResult(
            ok=False,
            message=f"Fine-tuning failed: {str(e)}",
            data={}
        )


def correct_policy_command(
    replay_path: str,
    evaluations_path: str,
    output_path: str
) -> CommandResult:
    try:
        executor = PaperTradingExecutor(replay_path)
        evaluator = DeterministicTradeEvaluator()
        corrector = DeterministicPolicyCorrector()
        
        # Load trades and evaluations
        trades = executor.load_replay_buffer()
        evaluations = evaluator.load_evaluations(evaluations_path)
        
        if not trades or not evaluations:
            return CommandResult(
                ok=False,
                message="No trades or evaluations found",
                data={"trades_count": len(trades), "evaluations_count": len(evaluations)}
            )
        
        # Match trades with evaluations
        labels = []
        matched_trades = []
        
        for trade in trades:
            if trade.status == "CLOSED":
                # Find matching evaluation
                trade_id = f"{trade.model_id}_{trade.entry_ts}"
                eval_label = None
                
                for eval_result in evaluations:
                    if eval_result.trade_id == trade_id:
                        if eval_result.label == "GOOD":
                            eval_label = "GOOD"
                        elif eval_result.label == "OK":
                            eval_label = "OK"
                        else:
                            eval_label = "BAD"
                        break
                
                if eval_label:
                    labels.append(eval_label)
                    matched_trades.append(trade)
        
        # Generate policy corrections
        corrections = corrector.correct_batch(matched_trades, labels)
        corrector.save_corrections(corrections, output_path)
        
        # Statistics
        confirm_count = sum(1 for c in corrections if c.correction_type == "CONFIRM")
        reject_count = sum(1 for c in corrections if c.correction_type == "REJECT")
        refine_count = sum(1 for c in corrections if c.correction_type == "REFINE")
        
        return CommandResult(
            ok=True,
            message=f"Generated {len(corrections)} policy corrections",
            data={
                "total_corrections": len(corrections),
                "confirm": confirm_count,
                "reject": reject_count,
                "refine": refine_count,
                "output_path": output_path
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to correct policy: {e}")
        return CommandResult(
            ok=False,
            message=f"Policy correction failed: {str(e)}",
            data={}
        )


def create_policy_correction_dataset_command(
    replay_path: str,
    output_path: str,
    correction_ratio: float = 1.0,
    stable_path: str | None = None,
    policy_weight: float = 2.0,
    stable_weight: float = 1.0,
    anti_hold_weight: float = 1.5,
    comprehensive: bool = False
) -> CommandResult:
    try:
        converter = EnhancedReplayConverter(replay_path)
        
        if comprehensive:
            # Create comprehensive training dataset
            stats = converter.create_comprehensive_training_dataset(
                output_path=output_path,
                include_anti_hold=True,
                policy_weight=policy_weight,
                anti_hold_weight=anti_hold_weight,
                stable_weight=stable_weight
            )
            method = "comprehensive_training"
        elif stable_path:
            # Create weighted training dataset
            stats = converter.create_weighted_training_dataset(
                policy_correction_path=output_path,
                stable_instruction_path=stable_path,
                output_path=output_path.replace(".jsonl", "_weighted.jsonl"),
                policy_weight=policy_weight,
                stable_weight=stable_weight
            )
            method = "weighted_training"
        else:
            # Create policy correction dataset
            stats = converter.create_policy_correction_dataset(
                output_path=output_path,
                correction_ratio=correction_ratio
            )
            method = "policy_correction"
        
        return CommandResult(
            ok=True,
            message=f"Created {method} dataset",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to create policy correction dataset: {e}")
        return CommandResult(
            ok=False,
            message=f"Dataset creation failed: {str(e)}",
            data={}
        )


def create_good_trade_reinforcement_command(
    replay_path: str,
    output_path: str,
    sample_ratio: float = 1.0
) -> CommandResult:
    try:
        converter = GoodTradeReinforcementConverter(replay_path)
        stats = converter.create_good_trade_dataset(
            output_path=output_path,
            sample_ratio=sample_ratio
        )
        
        return CommandResult(
            ok=True,
            message="Created GOOD-trade reinforcement dataset",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"Failed to create GOOD-trade reinforcement dataset: {e}")
        return CommandResult(
            ok=False,
            message=f"GOOD-trade reinforcement failed: {str(e)}",
            data={}
        )


def analyze_weighting_system_command(
    replay_path: str
) -> CommandResult:
    try:
        weighting_system = AdvancedWeightingSystem()
        
        # Generate weighting report
        weighting_report = weighting_system.generate_weighting_report()
        
        # Validate with examples
        examples = weighting_system.validate_weighting_examples()
        
        return CommandResult(
            ok=True,
            message="Weighting system analysis completed",
            data={
                "weighting_report": weighting_report,
                "examples": examples,
                "config": {
                    "BAD_BASE_WEIGHT": WeightingConfig.BAD_BASE_WEIGHT,
                    "OK_BASE_WEIGHT": WeightingConfig.OK_BASE_WEIGHT,
                    "GOOD_BASE_WEIGHT": WeightingConfig.GOOD_BASE_WEIGHT,
                    "POLICY_CORRECTION_MULTIPLIER": WeightingConfig.POLICY_CORRECTION_MULTIPLIER,
                    "ANTI_HOLD_COLLAPSE_MULTIPLIER": WeightingConfig.ANTI_HOLD_COLLAPSE_MULTIPLIER,
                    "GOOD_TRADE_REINFORCEMENT_MULTIPLIER": WeightingConfig.GOOD_TRADE_REINFORCEMENT_MULTIPLIER,
                    "HOLD_COLLAPSE_PENALTY": WeightingConfig.HOLD_COLLAPSE_PENALTY,
                    "OVERTRADING_PENALTY_MULTIPLIER": WeightingConfig.OVERTRADING_PENALTY_MULTIPLIER,
                    "MAX_TRADES_PER_DAY": WeightingConfig.MAX_TRADES_PER_DAY,
                    "MAX_GOOD_RATIO": WeightingConfig.MAX_GOOD_RATIO
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze weighting system: {e}")
        return CommandResult(
            ok=False,
            message=f"Weighting analysis failed: {str(e)}",
            data={}
        )
