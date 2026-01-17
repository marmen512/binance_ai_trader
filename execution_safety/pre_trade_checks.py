from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from execution_safety.emergency_stop import is_emergency_stop_active


@dataclass(frozen=True)
class PreTradeCheckResult:
    ok: bool
    reasons: list[str]


def run_pre_trade_checks(
    row: pd.Series,
    *,
    target_position: float,
    max_leverage: float,
    enforce_trade_validity: bool = True,
) -> PreTradeCheckResult:
    reasons: list[str] = []

    if is_emergency_stop_active():
        reasons.append("EMERGENCY_STOP")

    if abs(float(target_position)) > float(max_leverage):
        reasons.append("MAX_LEVERAGE_EXCEEDED")

    if "low_liquidity_flag" in row.index and bool(row.get("low_liquidity_flag", False)):
        reasons.append("LOW_LIQUIDITY")

    if enforce_trade_validity:
        if "trade_validity_target" in row.index and str(row.get("trade_validity_target")) == "SKIP":
            reasons.append("TRADE_VALIDITY_SKIP")

    ok = len(reasons) == 0
    return PreTradeCheckResult(ok=ok, reasons=reasons)
