from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.logging import setup_logger
from trading.paper_executor import TradeRecord

logger = setup_logger("binance_ai_trader.policy_corrector")


@dataclass(frozen=True)
class PolicyCorrection:
    trade_id: str
    correct_action: str  # BUY, SELL, HOLD
    correction_type: str  # CONFIRM, REJECT, REFINE
    reasoning: str
    original_action: str
    original_reasoning: str
    label: str
    pnl_pct: float


class DeterministicPolicyCorrector:
    def __init__(self):
        self.system_prompt = """You are a deterministic trading policy correction engine.
You operate in PAPER TRADING mode ONLY.
You NEVER ask questions.
You NEVER request clarification.
You NEVER explain what data you need.
You NEVER mention missing information.

You do NOT trade.
You do NOT predict markets.
You ONLY evaluate and correct decision logic.

Your purpose:
- Improve future decision quality
- Preserve capital
- Reduce bad trades
- Prefer HOLD over low-quality setups

You are given a COMPLETED paper trade record and its outcome.
All data is final.
Your task is to correct decision logic.

RULES (STRICT):
- You must assume same market conditions.
- You must not invent new indicators or data.
- You must not optimize for profit.
- You must optimize for decision correctness and risk avoidance.
- If trade outcome is BAD, you MUST propose a safer alternative.
- If trade outcome is OK, you MAY propose a refinement.
- If trade outcome is GOOD, you MUST explain why logic was correct.

ACTION SPACE:
- BUY
- SELL
- HOLD

PRIORITY ORDER:
1. Capital preservation
2. Risk avoidance
3. Trade only if asymmetric edge is clear
4. HOLD is the default safe action"""

    def correct_policy(self, trade: TradeRecord, label: str) -> Optional[PolicyCorrection]:
        if trade.status != "CLOSED" or trade.pnl_pct is None:
            return None
        
        # Determine correction type based on label
        if label == "GOOD":
            correction_type = "CONFIRM"
            correct_action = trade.direction
            reasoning = self._generate_good_reasoning(trade)
        elif label == "BAD":
            correction_type = "REJECT"
            correct_action = "HOLD"
            reasoning = self._generate_bad_reasoning(trade)
        else:  # OK
            correction_type = "REFINE"
            correct_action = self._determine_ok_correction(trade)
            reasoning = self._generate_ok_reasoning(trade, correct_action)
        
        trade_id = f"{trade.model_id}_{trade.entry_ts}"
        
        return PolicyCorrection(
            trade_id=trade_id,
            correct_action=correct_action,
            correction_type=correction_type,
            reasoning=reasoning,
            original_action=trade.direction,
            original_reasoning=trade.reasoning,
            label=label,
            pnl_pct=trade.pnl_pct
        )
    
    def _generate_good_reasoning(self, trade: TradeRecord) -> str:
        return f"The original {trade.direction} logic was correct as it identified a clear asymmetric edge with {trade.pnl_pct:.1f}% profit. The decision preserved capital while capturing upside, demonstrating proper risk-adjusted execution. The reasoning should be maintained as it consistently identifies high-probability setups."
    
    def _generate_bad_reasoning(self, trade: TradeRecord) -> str:
        return f"The original {trade.direction} logic was flawed as it resulted in {trade.pnl_pct:.1f}% loss, indicating poor risk assessment. HOLD would have preserved capital by avoiding this low-quality setup where no asymmetric edge existed. The decision logic failed to properly evaluate uncertainty and market conditions."
    
    def _generate_ok_reasoning(self, trade: TradeRecord, correct_action: str) -> str:
        if correct_action == trade.direction:
            return f"The {trade.direction} logic was partially correct with {trade.pnl_pct:.1f}% profit but could be refined for better risk management. While profitable, the setup lacked strong conviction and could have been optimized for better entry timing or position sizing."
        else:
            return f"The {trade.direction} logic was marginal with {trade.pnl_pct:.1f}% profit, suggesting weak edge identification. HOLD would have been safer by avoiding low-conviction trades where risk outweighed the small potential reward."
    
    def _determine_ok_correction(self, trade: TradeRecord) -> str:
        # For OK trades (0-15% profit), be more conservative
        if trade.pnl_pct < 5.0:
            return "HOLD"
        elif trade.pnl_pct < 10.0:
            return trade.direction  # Keep original but note weakness
        else:
            return trade.direction  # Keep original for decent profits
    
    def correct_batch(self, trades: list[TradeRecord], labels: list[str]) -> list[PolicyCorrection]:
        corrections = []
        
        for trade, label in zip(trades, labels):
            correction = self.correct_policy(trade, label)
            if correction:
                corrections.append(correction)
        
        return corrections
    
    def save_corrections(self, corrections: list[PolicyCorrection], output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        correction_data = []
        for correction in corrections:
            correction_data.append({
                "trade_id": correction.trade_id,
                "correct_action": correction.correct_action,
                "correction_type": correction.correction_type,
                "reasoning": correction.reasoning,
                "original_action": correction.original_action,
                "original_reasoning": correction.original_reasoning,
                "label": correction.label,
                "pnl_pct": correction.pnl_pct
            })
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(correction_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(corrections)} policy corrections to {path}")
    
    def load_corrections(self, input_path: str | Path) -> list[PolicyCorrection]:
        path = Path(input_path)
        if not path.exists():
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            correction_data = json.load(f)
        
        corrections = []
        for data in correction_data:
            corrections.append(PolicyCorrection(
                trade_id=data["trade_id"],
                correct_action=data["correct_action"],
                correction_type=data["correction_type"],
                reasoning=data["reasoning"],
                original_action=data["original_action"],
                original_reasoning=data["original_reasoning"],
                label=data["label"],
                pnl_pct=data["pnl_pct"]
            ))
        
        return corrections
