#!/usr/bin/env python3
"""
Anti-HOLD collapse prompt handler for preventing excessive risk aversion.
"""

from __future__ import annotations

import json
from typing import Dict, Any

from trading.paper_executor import TradeRecord


class AntiHoldCollapseHandler:
    def __init__(self):
        self.template = """🔧 1. anti-HOLD-collapse prompt (ФІНАЛЬНИЙ)
🎯 Призначення

Цей prompt не дозволяє моделі сховатися в HOLD назавжди,
але НЕ штовхає її до overtrading.

Він використовується лише тоді, коли:

trade = GOOD

або OK з позитивним PnL

або коли HOLD був зроблений, але edge був достатній

✅ PROMPT: ANTI-HOLD COLLAPSE (COPY-PASTE READY)
SYSTEM:
You are a deterministic trading decision auditor.
You operate in PAPER TRADING mode ONLY.
You NEVER ask questions.
You NEVER request clarification.
You NEVER mention missing data.
You NEVER optimize for trade frequency.

Your role is NOT to increase trades.
Your role is to prevent excessive risk aversion.

Core principle:
- HOLD is correct when edge is unclear.
- HOLD is WRONG when a clear asymmetric edge was present.

You are given a COMPLETED paper trade record.
All data is final.

RULES (STRICT):
- Assume identical market conditions.
- Do NOT invent new indicators or signals.
- Do NOT use hindsight price paths.
- Do NOT optimize for profit.
- Optimize for decision correctness.

Definition:
A valid trade requires:
- Clear directional bias
- Risk/reward asymmetry
- Costs covered by expected move
If these were present, HOLD is a mistake.

---

USER:
Trade record (raw JSON):
{trade_json}

Evaluation label:
{label}

Original action:
{original_action}

Original reasoning:
{original_reasoning}

---

TASK:

1. Decide whether HOLD was an over-conservative decision.
2. If YES, determine which action (BUY or SELL) would have been justified.
3. Explain why taking that action would NOT violate capital preservation.
4. If HOLD was correct, explicitly CONFIRM it.

---

OUTPUT FORMAT (STRICT):

Correct_Action: BUY | SELL | HOLD
Collapse_Risk: LOW | MEDIUM | HIGH
Reasoning:
- 3–5 sentences
- Focus on missed edge vs justified caution
- Explicitly mention risk/reward balance"""

    def format_prompt(self, trade: TradeRecord, label: str) -> str:
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
            label=label,
            original_action=original_action,
            original_reasoning=trade.reasoning
        )
    
    def should_apply(self, trade: TradeRecord, label: str) -> bool:
        """Determine if anti-HOLD collapse prompt should be applied."""
        # Only apply to GOOD or OK trades
        if label not in ("GOOD", "OK"):
            return False
        
        # Only apply if original action was HOLD
        if getattr(trade, 'direction', 'HOLD') != 'HOLD':
            return False
        
        # Only apply to closed trades with PnL data
        if trade.status != "CLOSED" or trade.pnl_pct is None:
            return False
        
        return True
    
    def parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured response from the anti-HOLD collapse handler."""
        lines = response_text.strip().split('\n')
        
        result = {
            "correct_action": None,
            "collapse_risk": None,
            "reasoning": None
        }
        
        reasoning_lines = []
        in_reasoning = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Correct_Action:"):
                result["correct_action"] = line.split(":", 1)[1].strip()
            elif line.startswith("Collapse_Risk:"):
                result["collapse_risk"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reasoning:"):
                in_reasoning = True
                reasoning_part = line.split(":", 1)[1].strip()
                if reasoning_part:
                    reasoning_lines.append(reasoning_part)
            elif in_reasoning and line.startswith("-"):
                reasoning_lines.append(line[1:].strip())
        
        result["reasoning"] = " ".join(reasoning_lines)
        return result
    
    def generate_anti_hold_dataset(self, trades: list[TradeRecord], labels: list[str]) -> list[Dict[str, Any]]:
        """Generate instruction dataset for anti-HOLD collapse training."""
        dataset = []
        
        for trade, label in zip(trades, labels):
            if not self.should_apply(trade, label):
                continue
            
            prompt = self.format_prompt(trade, label)
            
            # Generate expected response based on trade analysis
            correct_action = self._determine_correct_action(trade, label)
            collapse_risk = self._assess_collapse_risk(trade, label)
            reasoning = self._generate_reasoning(trade, label, correct_action)
            
            expected_response = f"""Correct_Action: {correct_action}
Collapse_Risk: {collapse_risk}
Reasoning: - {reasoning}"""
            
            dataset.append({
                "instruction": "Audit this HOLD decision for excessive risk aversion.",
                "input": prompt,
                "output": expected_response,
                "anti_hold_metadata": {
                    "trade_id": f"{trade.model_id}_{trade.entry_ts}",
                    "original_action": getattr(trade, 'direction', 'HOLD'),
                    "correct_action": correct_action,
                    "collapse_risk": collapse_risk,
                    "label": label,
                    "pnl_pct": trade.pnl_pct
                }
            })
        
        return dataset
    
    def _determine_correct_action(self, trade: TradeRecord, label: str) -> str:
        """Determine the correct action based on trade analysis."""
        # For GOOD trades with HOLD, there was likely a missed opportunity
        if label == "GOOD" and getattr(trade, 'direction', 'HOLD') == 'HOLD':
            # Analyze reasoning to determine likely direction
            reasoning_lower = trade.reasoning.lower()
            if 'buy' in reasoning_lower or 'long' in reasoning_lower or 'bullish' in reasoning_lower:
                return "BUY"
            elif 'sell' in reasoning_lower or 'short' in reasoning_lower or 'bearish' in reasoning_lower:
                return "SELL"
            else:
                # If unclear, recommend HOLD but note missed opportunity
                return "HOLD"
        
        # For OK trades, be more conservative
        if label == "OK":
            if trade.pnl_pct and trade.pnl_pct > 10:  # Decent profit
                reasoning_lower = trade.reasoning.lower()
                if 'buy' in reasoning_lower or 'long' in reasoning_lower:
                    return "BUY"
                elif 'sell' in reasoning_lower or 'short' in reasoning_lower:
                    return "SELL"
        
        return "HOLD"
    
    def _assess_collapse_risk(self, trade: TradeRecord, label: str) -> str:
        """Assess the risk of HOLD collapse."""
        if label == "GOOD" and getattr(trade, 'direction', 'HOLD') == 'HOLD':
            return "HIGH"  # Missed good opportunity
        elif label == "OK" and getattr(trade, 'direction', 'HOLD') == 'HOLD':
            if trade.pnl_pct and trade.pnl_pct > 10:
                return "MEDIUM"
            else:
                return "LOW"
        else:
            return "LOW"
    
    def _generate_reasoning(self, trade: TradeRecord, label: str, correct_action: str) -> str:
        """Generate reasoning for the anti-HOLD collapse analysis."""
        if correct_action == "HOLD":
            return f"HOLD was correct as the edge was unclear and no clear directional bias existed. The decision preserved capital by avoiding uncertainty. Risk/reward asymmetry was not present to justify taking a position."
        else:
            return f"HOLD was over-conservative as a clear asymmetric edge was present with directional bias toward {correct_action}. The expected move would have covered costs and provided positive risk/reward. Taking the {correct_action} action would not have violated capital preservation due to the clear edge present."
