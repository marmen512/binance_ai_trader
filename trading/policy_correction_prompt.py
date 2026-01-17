#!/usr/bin/env python3
"""
Policy correction prompt handler for deterministic trading logic improvement.
"""

from __future__ import annotations

import json
from typing import Dict, Any

from trading.policy_corrector import PolicyCorrection


class PolicyCorrectionPromptHandler:
    def __init__(self):
        self.template = """✅ FINAL PROMPT: PAPER TRADE POLICY CORRECTION
SYSTEM:
You are a deterministic trading policy correction engine.
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
4. HOLD is default safe action

---

USER:
You are given following COMPLETED PAPER trade record (raw JSON):

{trade_json}

The trade has already been evaluated with the following label:
{label}

Original model reasoning:
{original_reasoning}

---

TASK (MANDATORY):

1. Decide whether ORIGINAL reasoning was logically correct GIVEN the outcome.
2. Identify the MAIN logical flaw or strength.
3. Determine the CORRECT action that SHOULD have been taken under the SAME conditions.
4. Explain WHY that action is safer or more correct.

---

OUTPUT FORMAT (STRICT — NO EXTRA TEXT):

Correct_Action: BUY | SELL | HOLD
Correction_Type: CONFIRM | REJECT | REFINE
Reasoning:
- One concise paragraph (3–5 sentences max)
- Focus on logic, not hindsight
- Explicitly mention risk, uncertainty, or lack of edge
- If rejecting, explain why HOLD would have preserved capital"""

    def format_prompt(self, correction: PolicyCorrection) -> str:
        trade_json = json.dumps({
            "direction": correction.original_action,
            "entry_price": 0.0,  # Not needed for policy correction
            "exit_price": 0.0,
            "pnl_pct": correction.pnl_pct,
            "reasoning": correction.original_reasoning,
            "model_id": correction.trade_id.split("_")[0] if "_" in correction.trade_id else "unknown"
        }, ensure_ascii=False, indent=2)
        
        return self.template.format(
            trade_json=trade_json,
            label=correction.label,
            original_reasoning=correction.original_reasoning
        )
    
    def parse_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the structured response from the policy correction engine."""
        lines = response_text.strip().split('\n')
        
        result = {
            "correct_action": None,
            "correction_type": None,
            "reasoning": None
        }
        
        reasoning_lines = []
        in_reasoning = False
        
        for line in lines:
            line = line.strip()
            if line.startswith("Correct_Action:"):
                result["correct_action"] = line.split(":", 1)[1].strip()
            elif line.startswith("Correction_Type:"):
                result["correction_type"] = line.split(":", 1)[1].strip()
            elif line.startswith("Reasoning:"):
                in_reasoning = True
                reasoning_part = line.split(":", 1)[1].strip()
                if reasoning_part:
                    reasoning_lines.append(reasoning_part)
            elif in_reasoning and line.startswith("-"):
                reasoning_lines.append(line[1:].strip())
        
        result["reasoning"] = " ".join(reasoning_lines)
        return result
    
    def generate_correction_dataset(self, corrections: list[PolicyCorrection]) -> list[Dict[str, Any]]:
        """Generate instruction dataset from policy corrections."""
        dataset = []
        
        for correction in corrections:
            prompt = self.format_prompt(correction)
            
            # Generate expected response based on correction
            if correction.correction_type == "CONFIRM":
                expected_response = f"""Correct_Action: {correction.original_action}
Correction_Type: CONFIRM
Reasoning: - {correction.reasoning}"""
            elif correction.correction_type == "REJECT":
                expected_response = f"""Correct_Action: HOLD
Correction_Type: REJECT
Reasoning: - {correction.reasoning}"""
            else:  # REFINE
                expected_response = f"""Correct_Action: {correction.correct_action}
Correction_Type: REFINE
Reasoning: - {correction.reasoning}"""
            
            dataset.append({
                "instruction": "Evaluate this completed paper trade and correct the decision logic.",
                "input": prompt,
                "output": expected_response,
                "correction_metadata": {
                    "trade_id": correction.trade_id,
                    "original_action": correction.original_action,
                    "correct_action": correction.correct_action,
                    "correction_type": correction.correction_type,
                    "label": correction.label,
                    "pnl_pct": correction.pnl_pct
                }
            })
        
        return dataset
