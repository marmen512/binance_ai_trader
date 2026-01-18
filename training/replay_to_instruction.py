#!/usr/bin/env python3
"""
OFFLINE POLICY REPLAY → INSTRUCTION DATASET CONVERTER

ARCHITECTURAL BOUNDARY:
- Reads POLICY replay only (BAD / OK / GOOD)
- Does NOT read execution trades
- Does NOT import trading / executor / inference code
- Safe for offline training only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from core.logging import setup_logger

logger = setup_logger("binance_ai_trader.replay_to_instruction")


# ---------- POLICY CONVERTER ----------

def convert_policy_record(record: Dict) -> Dict | None:
    """
    Convert a policy replay record into instruction format.
    """
    label = record.get("label")
    action = record.get("action")
    reasoning = record.get("reasoning")

    if label not in {"BAD", "OK", "GOOD"}:
        return None

    return {
        "instruction": f"Evaluate this trading decision: {action}",
        "input": "",
        "output": f"{label}: {reasoning}",
        "label": label,
    }


def load_policy_replay(path: Path) -> List[Dict]:
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


# ---------- MAIN ----------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replay-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    replay_path = Path(args.replay_path)
    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = load_policy_replay(replay_path)

    written = 0
    with open(output_path, "w", encoding="utf-8") as out:
        for rec in records:
            instr = convert_policy_record(rec)
            if instr:
                out.write(json.dumps(instr, ensure_ascii=False) + "\n")
                written += 1

    logger.info(
        f"Created instruction dataset with {written} samples at {output_path}"
    )


if __name__ == "__main__":
    main()
