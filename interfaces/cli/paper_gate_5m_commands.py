from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.config import load_config
from core.logging import setup_logger
from paper_gate.gate_5m import paper_gate_5m


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    output: str


def paper_gate_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = paper_gate_5m()
    logger.info("paper-gate-5m: verdict=%s ok=%s", res.verdict, res.ok)
    code = 0 if res.ok else 2
    return CommandResult(exit_code=code, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def paper_status_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    # Status is a non-failing version of the gate
    try:
        res = paper_gate_5m()
        payload = {"ok": res.ok, "verdict": res.verdict, "checklist": res.checklist, "metrics": res.metrics}
        code = 0 if res.ok else 2
    except Exception as e:
        payload = {"ok": False, "verdict": "NO-GO", "error": str(e)}
        code = 2

    logger.info("paper-status-5m: OK")
    return CommandResult(exit_code=code, output=json.dumps(payload, ensure_ascii=False, indent=2))
