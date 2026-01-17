#!/usr/bin/env python3
"""
Advanced dataset weighting system for balanced trading model training.
"""

from __future__ import annotations

import json
from typing import Dict, Any, List
from dataclasses import dataclass


@dataclass(frozen=True)
class WeightingConfig:
    # Base weights by label - MANDATORY VALUES (NON-OVERRIDEABLE)
    BAD_BASE_WEIGHT: float = 1.50
    OK_BASE_WEIGHT: float = 1.00
    GOOD_BASE_WEIGHT: float = 0.60
    
    # Prompt type multipliers - MANDATORY VALUES (NON-OVERRIDEABLE)
    POLICY_CORRECTION_MULTIPLIER: float = 1.20  # BAD trades
    ANTI_HOLD_COLLAPSE_MULTIPLIER: float = 0.90  # Anti-HOLD prompts
    GOOD_TRADE_REINFORCEMENT_MULTIPLIER: float = 0.70  # GOOD reinforcement
    
    # Penalties - MANDATORY VALUES (NON-OVERRIDEABLE)
    HOLD_COLLAPSE_PENALTY: float = 0.40  # When HOLD is corrected
    OVERTRADING_PENALTY_MULTIPLIER: float = 0.75  # When trades_per_day > 20
    
    # Thresholds - MANDATORY VALUES (HARD LOCKED)
    MAX_TRADES_PER_DAY: float = 20.0
    MAX_GOOD_RATIO: float = 0.45  # ENFORCED: <= 0.45
    MIN_BAD_TO_GOOD_RATIO: float = 4.0  # ENFORCED: >= 4.0
    
    def __post_init__(self):
        """Enforce hard invariants."""
        # HARD CONSTRAINTS - FAIL FAST IF VIOLATED
        good_final_weight = self.GOOD_BASE_WEIGHT * self.GOOD_TRADE_REINFORCEMENT_MULTIPLIER
        bad_final_weight = self.BAD_BASE_WEIGHT * self.POLICY_CORRECTION_MULTIPLIER
        bad_to_good_ratio = bad_final_weight / good_final_weight
        
        if good_final_weight > 0.45:
            raise ValueError(f"GOOD_FINAL_WEIGHT {good_final_weight} > 0.45 (HARD CONSTRAINT)")
        if bad_to_good_ratio < 4.0:
            raise ValueError(f"BAD_TO_GOOD_RATIO {bad_to_good_ratio} < 4.0 (HARD CONSTRAINT)")


class AdvancedWeightingSystem:
    def __init__(self, config: WeightingConfig | None = None):
        self.config = config or WeightingConfig()  # This will trigger __post_init__ validation
        
    def calculate_sample_weight(
        self,
        label: str,
        prompt_type: str,
        original_action: str,
        correct_action: str,
        trades_per_day: float | None = None
    ) -> float:
        """
        Calculate final sample weight using the formula:
        
        sample_weight = base_weight[label] * prompt_multiplier[type] + hold_collapse_penalty * overtrading_penalty
        """
        
        # 1. Base weight by label
        base_weights = {
            "BAD": self.config.BAD_BASE_WEIGHT,
            "OK": self.config.OK_BASE_WEIGHT,
            "GOOD": self.config.GOOD_BASE_WEIGHT
        }
        base_weight = base_weights.get(label, 1.0)
        
        # 2. Prompt type multiplier
        prompt_multipliers = {
            "POLICY_CORRECTION": self.config.POLICY_CORRECTION_MULTIPLIER,
            "ANTI_HOLD_COLLAPSE": self.config.ANTI_HOLD_COLLAPSE_MULTIPLIER,
            "GOOD_TRADE_REINFORCEMENT": self.config.GOOD_TRADE_REINFORCEMENT_MULTIPLIER
        }
        prompt_multiplier = prompt_multipliers.get(prompt_type, 1.0)
        
        # 3. HOLD collapse penalty
        hold_collapse_penalty = 0.0
        if (original_action == "HOLD" and 
            label in {"GOOD", "OK"} and 
            correct_action in {"BUY", "SELL"} and
            prompt_type == "ANTI_HOLD_COLLAPSE"):
            hold_collapse_penalty = self.config.HOLD_COLLAPSE_PENALTY
        
        # 4. Overtrading penalty
        overtrading_penalty = 1.0
        if (trades_per_day and 
            trades_per_day > self.config.MAX_TRADES_PER_DAY):
            overtrading_penalty = self.config.OVERTRADING_PENALTY_MULTIPLIER
        
        # Final formula
        final_weight = (
            base_weight * prompt_multiplier + hold_collapse_penalty
        ) * overtrading_penalty
        
        return final_weight
    
    def analyze_dataset_balance(self, samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the balance of the weighted dataset."""
        
        total_weight = 0.0
        label_weights = {"BAD": 0.0, "OK": 0.0, "GOOD": 0.0}
        prompt_type_weights = {}
        
        for sample in samples:
            weight = sample.get("calculated_weight", 1.0)
            label = sample.get("label", "UNKNOWN")
            prompt_type = sample.get("prompt_type", "UNKNOWN")
            
            total_weight += weight
            label_weights[label] = label_weights.get(label, 0.0) + weight
            prompt_type_weights[prompt_type] = prompt_type_weights.get(prompt_type, 0.0) + weight
        
        # Calculate percentages
        label_percentages = {
            label: (weight / total_weight * 100) if total_weight > 0 else 0
            for label, weight in label_weights.items()
        }
        
        prompt_type_percentages = {
            ptype: (weight / total_weight * 100) if total_weight > 0 else 0
            for ptype, weight in prompt_type_weights.items()
        }
        
        # Health checks
        good_ratio = label_percentages.get("GOOD", 0) / 100
        bad_ratio = label_percentages.get("BAD", 0) / 100
        health_warnings = []
        
        # ENFORCED: GOOD_FINAL_WEIGHT <= 0.45
        if good_ratio > self.config.MAX_GOOD_RATIO:
            health_warnings.append(f"GOOD ratio {good_ratio:.1%} exceeds maximum {self.config.MAX_GOOD_RATIO:.1%}")
        
        # ENFORCED: BAD_TO_GOOD_RATIO >= 4.0
        if good_ratio > 0:
            bad_to_good_ratio = bad_ratio / good_ratio
            if bad_to_good_ratio < self.config.MIN_BAD_TO_GOOD_RATIO:
                health_warnings.append(f"BAD:GOOD ratio {bad_to_good_ratio:.1f} below minimum {self.config.MIN_BAD_TO_GOOD_RATIO:.1f}")
        
        expected_ranges = {
            "BAD": (45, 55),
            "OK": (30, 40),
            "GOOD": (10, 20)
        }
        
        for label, (min_pct, max_pct) in expected_ranges.items():
            actual_pct = label_percentages.get(label, 0)
            if not (min_pct <= actual_pct <= max_pct):
                health_warnings.append(f"{label} ratio {actual_pct:.1f}% outside expected range {min_pct}-{max_pct}%")
        
        return {
            "total_samples": len(samples),
            "total_weight": total_weight,
            "label_weights": label_weights,
            "label_percentages": label_percentages,
            "prompt_type_weights": prompt_type_weights,
            "prompt_type_percentages": prompt_type_percentages,
            "health_warnings": health_warnings,
            "is_healthy": len(health_warnings) == 0
        }
    
    def validate_weighting_examples(self) -> Dict[str, float]:
        """Validate the weighting system with example calculations."""
        
        examples = {
            "BAD_policy_correction": self.calculate_sample_weight(
                label="BAD",
                prompt_type="POLICY_CORRECTION",
                original_action="BUY",
                correct_action="HOLD"
            ),
            "OK_anti_hold_collapse": self.calculate_sample_weight(
                label="OK",
                prompt_type="ANTI_HOLD_COLLAPSE",
                original_action="HOLD",
                correct_action="BUY"
            ),
            "GOOD_reinforcement": self.calculate_sample_weight(
                label="GOOD",
                prompt_type="GOOD_TRADE_REINFORCEMENT",
                original_action="BUY",
                correct_action="BUY"
            )
        }
        
        # Calculate BAD to GOOD ratio
        bad_weight = examples["BAD_policy_correction"]
        good_weight = examples["GOOD_reinforcement"]
        bad_to_good_ratio = bad_weight / good_weight if good_weight > 0 else float('inf')
        
        examples["BAD_to_GOOD_ratio"] = bad_to_good_ratio
        
        return examples
    
    def generate_weighting_report(self) -> str:
        """Generate a detailed weighting system report."""
        
        examples = self.validate_weighting_examples()
        
        report = f"""
🧮 Dataset Weighting System Report

📊 Base Weights by Label:
- BAD: {self.config.BAD_BASE_WEIGHT:.2f}
- OK: {self.config.OK_BASE_WEIGHT:.2f}  
- GOOD: {self.config.GOOD_BASE_WEIGHT:.2f}

🎛️ Prompt Type Multipliers:
- POLICY_CORRECTION: {self.config.POLICY_CORRECTION_MULTIPLIER:.2f}
- ANTI_HOLD_COLLAPSE: {self.config.ANTI_HOLD_COLLAPSE_MULTIPLIER:.2f}
- GOOD_TRADE_REINFORCEMENT: {self.config.GOOD_TRADE_REINFORCEMENT_MULTIPLIER:.2f}

⚠️ Penalties:
- HOLD_COLLAPSE: +{self.config.HOLD_COLLAPSE_PENALTY:.2f}
- OVERTRADING: ×{self.config.OVERTRADING_PENALTY_MULTIPLIER:.2f} (if trades/day > {self.config.MAX_TRADES_PER_DAY})

🧮 Example Calculations:
- BAD (policy correction): {examples['BAD_policy_correction']:.2f}
- OK + anti-HOLD: {examples['OK_anti_hold_collapse']:.2f}
- GOOD (reinforcement): {examples['GOOD_reinforcement']:.2f}
- BAD to GOOD ratio: {examples['BAD_to_GOOD_ratio']:.1f}x

📋 Expected Dataset Balance:
- BAD: 45-55%
- OK: 30-40%
- GOOD: 10-20%

🚨 Health Thresholds:
- Maximum GOOD ratio: {self.config.MAX_GOOD_RATIO:.1%}
- Maximum trades/day: {self.config.MAX_TRADES_PER_DAY}
"""
        
        return report.strip()
