#!/usr/bin/env python3
"""
GOOD-trade reinforcement prompt handler for stabilizing correct decision logic.
"""

from __future__ import annotations

import json
from typing import Dict, Any

from trading.paper_executor import TradeRecord


class GoodTradeReinforcementHandler:
    def __init__(self):
        self.template = """🔧 2. GOOD-trade reinforcement prompt (ФІНАЛЬНИЙ)
🎯 Призначення

Цей prompt закріплює правильне мислення, а не результат.
Він не заохочує більше трейдів, а фіксує чому саме рішення було коректним.

Критично:

GOOD ≠ "пощастило"
GOOD = логіка була правильною ДО руху ціни

✅ PROMPT: GOOD-TRADE REINFORCEMENT (COPY-PASTE READY)
SYSTEM:
You are a deterministic trading reasoning reinforcement engine.
You operate in PAPER TRADING mode ONLY.
You NEVER ask questions.
You NEVER request clarification.
You NEVER mention missing information.
You NEVER optimize for higher risk.

Your role:
- Reinforce correct decision logic
- Stabilize future behavior
- Prevent overreaction to short-term success

You are given a COMPLETED paper trade with a GOOD outcome.
All data is final.

RULES (STRICT):
- Assume same information available at decision time.
- Do NOT use hindsight reasoning.
- Do NOT praise profit itself.
- Focus ONLY on decision quality.
- HOLD remains the default unless justified.

---

USER:
Trade record (raw JSON):
{trade_json}

Evaluation label:
GOOD

Original action:
{original_action}

Original reasoning:
{original_reasoning}

---

TASK:

1. Identify the SINGLE strongest reason decision was correct.
2. Explain why this logic aligns with capital preservation.
3. State why taking this action did NOT rely on luck.

---

OUTPUT FORMAT (STRICT):

Correct_Action: BUY | SELL | HOLD
Reinforcement_Type: CONFIRM
Reasoning:
- 3–4 sentences
- No hype
- No hindsight
- Explicitly mention risk control or asymmetry"""

    def format_prompt(self, trade: TradeRecord) -> str:
        trade_json = json.dumps({
            "direction": getattr(trade, 'direction', 'HOLD'),
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl_pct": trade.pnl_pct,
            "reasoning": trade.reasoning,
            "model_id": trade.model_id,
            "status": trade.status
        }, ensure_ascii=False, indent=2)
        
        original_action = getattr(trade, 'direction', 'HOLD')
        
        return self.template.format(
            trade_json=trade_json,
            original_action=original_action,
            original_reasoning=trade.reasoning
        )
    
    def should_apply(self, trade: TradeRecord, label: str) -> bool:
        """Determine if GOOD-trade reinforcement prompt should be applied."""
        # Only apply to GOOD trades
        if label != "GOOD":
            return False
        
        # Only apply to closed trades with PnL data
        if trade.status != "CLOSED" or trade.pnl_pct is None:
            return False
        
        return True
    
    def parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured response from the GOOD-trade reinforcement handler."""
        lines = response_text.strip().split('\n')
        
        result = {
            "correct_action": None,
            "reinforcement_type": None,
            "reasoning": None
        }
        
        reasoning_lines = []
        in_reasoning = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Correct_Action:"):
                result["correct_action"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reinforcement_Type:"):
                result["reinforcement_type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reasoning:"):
                in_reasoning = True
                reasoning_part = line.split(":", 1)[1].strip()
                if reasoning_part:
                    reasoning_lines.append(reasoning_part)
            elif in_reasoning and line.startswith("-"):
                reasoning_lines.append(line[1:].strip())
        
        result["reasoning"] = " ".join(reasoning_lines)
        return result
    
    def generate_good_trade_dataset(self, trades: list[TradeRecord], labels: list[str]) -> list[Dict[str, Any]]:
        """Generate instruction dataset for GOOD-trade reinforcement training."""
        dataset = []
        
        for trade, label in zip(trades, labels):
            if not self.should_apply(trade, label):
                continue
            
            prompt = self.format_prompt(trade)
            
            # Generate expected response based on trade analysis
            correct_action = getattr(trade, 'direction', 'HOLD')
            reasoning = self._generate_reasoning(trade)
            
            expected_response = f"""Correct_Action: {correct_action}
Reinforcement_Type: CONFIRM
Reasoning: - {reasoning}"""
            
            dataset.append({
                "instruction": "Reinforce the correct decision logic for this GOOD trade.",
                "input": prompt,
                "output": expected_response,
                "good_trade_metadata": {
                    "trade_id": f"{trade.model_id}_{trade.entry_ts}",
                    "original_action": correct_action,
                    "reinforcement_type": "CONFIRM",
                    "label": "GOOD",
                    "pnl_pct": trade.pnl_pct
                }
            })
        
        return dataset
    
    def _generate_reasoning(self, trade: TradeRecord) -> str:
        """Generate reasoning for GOOD-trade reinforcement."""
        action = getattr(trade, 'direction', 'HOLD')
        
        if action == "HOLD":
            return f"HOLD was correct as no clear asymmetric edge existed, preserving capital by avoiding uncertainty. The decision aligned with risk control by waiting for better conditions. This reasoning was sound as it prioritized capital preservation over unclear opportunities."
        elif action == "BUY":
            return f"BUY was correct based on clear bullish bias and favorable risk/reward asymmetry present at entry time. The decision did not rely on luck as costs were covered by expected move and directional bias was evident. This logic properly aligned with capital preservation through calculated risk-taking."
        elif action == "SELL":
            return f"SELL was correct as bearish signals and asymmetric downside risk justified the position. The reasoning was sound as it identified clear directional bias with adequate reward potential. This decision maintained capital preservation principles through controlled, calculated exposure."
        else:
            return "The decision logic was correct as it properly assessed available information and acted accordingly. Risk was controlled and the action was justified by market conditions at the time."
    
    def analyze_reasoning_quality(self, trade: TradeRecord) -> Dict[str, Any]:
        """Analyze the quality of the original reasoning."""
        reasoning = trade.reasoning.lower()
        
        quality_indicators = {
            "mentions_risk": any(word in reasoning for word in ["risk", "stop", "loss", "downside"]),
            "mentions_asymmetry": any(word in reasoning for word in ["asymmetr", "edge", "advantage", "favorable"]),
            "mentions_direction": any(word in reasoning for word in ["bullish", "bearish", "uptrend", "downtrend", "long", "short"]),
            "mentions_costs": any(word in reasoning for word in ["cost", "fee", "spread", "commission"]),
            "avoidance_of_hindsight": not any(word in reasoning for word in ["in hindsight", "looking back", "should have"]),
        }
        
        # Calculate quality score
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        
        return {
            "quality_score": quality_score,
            "indicators": quality_indicators,
            "reasoning_length": len(trade.reasoning.split()),
            "is_high_quality": quality_score >= 0.6
        }
