from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from core.logging import setup_logger
from trading.paper_executor import TradeRecord

logger = setup_logger("binance_ai_trader.trade_evaluator")


@dataclass(frozen=True)
class TradeEvaluation:
    trade_id: str
    label: str  # GOOD, OK, BAD
    analysis: str
    improvement: str
    pnl_pct: float
    reasoning: str
    direction: str


class DeterministicTradeEvaluator:
    def __init__(self):
        self.system_prompt = """You are a deterministic trade evaluation engine.

Your role:
- Evaluate COMPLETED PAPER trades
- NEVER ask questions
- NEVER request input
- NEVER mention missing data
- NEVER explain what you need
- ALWAYS produce an evaluation

You do not interact with users.
You do not wait for instructions.
You do not request clarification.

Every input you receive is a FINAL trade record.
You must evaluate it immediately.

Evaluation rules (STRICT):
- pnl_pct >= 15.0 → Label = GOOD
- 0.0 < pnl_pct < 15.0 → Label = OK
- pnl_pct <= 0.0 → Label = BAD

Output rules:
- Output ONLY the evaluation
- Output EXACTLY the specified format
- No extra text
- No preamble
- No epilogue

Required output format:

Label: GOOD | OK | BAD
Analysis: <1–2 short sentences>
Improvement: <one concrete suggestion or NONE>"""

    def evaluate_trade(self, trade: TradeRecord) -> Optional[TradeEvaluation]:
        if trade.status != "CLOSED" or trade.pnl_pct is None:
            return None
        
        pnl_pct = trade.pnl_pct
        
        if pnl_pct >= 15.0:
            label = "GOOD"
        elif 0.0 < pnl_pct < 15.0:
            label = "OK"
        else:
            label = "BAD"
        
        analysis = self._generate_analysis(trade, label, pnl_pct)
        improvement = self._generate_improvement(trade, label, pnl_pct)
        
        trade_id = f"{trade.model_id}_{trade.entry_ts}"
        
        return TradeEvaluation(
            trade_id=trade_id,
            label=label,
            analysis=analysis,
            improvement=improvement,
            pnl_pct=pnl_pct,
            reasoning=trade.reasoning,
            direction=trade.direction
        )
    
    def _generate_analysis(self, trade: TradeRecord, label: str, pnl_pct: float) -> str:
        if label == "GOOD":
            return f"Strong {trade.direction} trade with {pnl_pct:.1f}% profit. Entry timing and direction were correct."
        elif label == "OK":
            return f"Modest {trade.direction} trade with {pnl_pct:.1f}% profit. Direction was correct but magnitude limited."
        else:
            return f"Loss-making {trade.direction} trade with {pnl_pct:.1f}% loss. Direction or timing was incorrect."
    
    def _generate_improvement(self, trade: TradeRecord, label: str, pnl_pct: float) -> str:
        if label == "GOOD":
            return "NONE"
        elif label == "OK":
            return "Consider position sizing or earlier exit to capture more profit."
        else:
            return "Improve entry timing or reverse direction signal."
    
    def evaluate_batch(self, trades: list[TradeRecord]) -> list[TradeEvaluation]:
        evaluations = []
        for trade in trades:
            eval_result = self.evaluate_trade(trade)
            if eval_result:
                evaluations.append(eval_result)
        return evaluations
    
    def save_evaluations(self, evaluations: list[TradeEvaluation], output_path: str | Path) -> None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        evaluation_data = []
        for eval_result in evaluations:
            evaluation_data.append({
                "trade_id": eval_result.trade_id,
                "label": eval_result.label,
                "analysis": eval_result.analysis,
                "improvement": eval_result.improvement,
                "pnl_pct": eval_result.pnl_pct,
                "reasoning": eval_result.reasoning,
                "direction": eval_result.direction
            })
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(evaluation_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(evaluations)} trade evaluations to {path}")
    
    def load_evaluations(self, input_path: str | Path) -> list[TradeEvaluation]:
        path = Path(input_path)
        if not path.exists():
            return []
        
        with open(path, "r", encoding="utf-8") as f:
            evaluation_data = json.load(f)
        
        evaluations = []
        for data in evaluation_data:
            evaluations.append(TradeEvaluation(
                trade_id=data["trade_id"],
                label=data["label"],
                analysis=data["analysis"],
                improvement=data["improvement"],
                pnl_pct=data["pnl_pct"],
                reasoning=data["reasoning"],
                direction=data["direction"]
            ))
        
        return evaluations
