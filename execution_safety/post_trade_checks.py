from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PostTradeCheckResult:
    ok: bool
    reasons: list[str]


def run_post_trade_checks(*, equity: float) -> PostTradeCheckResult:
    reasons: list[str] = []
    if not (equity == equity):
        reasons.append("EQUITY_NAN")
    if equity <= 0:
        reasons.append("EQUITY_NON_POSITIVE")
    return PostTradeCheckResult(ok=len(reasons) == 0, reasons=reasons)
