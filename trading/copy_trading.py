from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from monitoring.alerts import write_alert
from monitoring.events import append_event
from monitoring.metrics import write_metrics
from trading.paper_broker import PaperFill, PaperState, execute_to_target, load_state, save_state


@dataclass(frozen=True)
class CopySignal:
    mid_price: float
    target_position: float
    ts: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class CopyTradeOnceResult:
    ok: bool
    executed: bool
    mid_price: float
    expert_target_position: float
    follower_target_position: float
    fill: PaperFill | None
    reasons: list[str]
    state_path: str
    report_path: str


def _read_copy_signal(path: str | Path) -> CopySignal:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    return CopySignal(
        mid_price=float(raw.get("mid_price", 0.0)),
        target_position=float(raw.get("target_position", 0.0)),
        ts=raw.get("ts"),
        source=raw.get("source"),
    )


def copy_trade_once(
    *,
    signal_path: str | Path,
    state_path: str | Path = Path("ai_data") / "copy_paper" / "state.json",
    report_path: str | Path = Path("ai_data") / "copy_paper" / "last_trade.json",
    allocation: float = 1.0,
    max_leverage: float = 1.0,
    fee_bps: float = 1.0,
    slippage_bps: float = 1.0,
) -> CopyTradeOnceResult:
    reasons: list[str] = []

    sig = _read_copy_signal(signal_path)
    mid = float(sig.mid_price)
    if not (mid > 0):
        reasons.append("BAD_PRICE")

    alloc = float(allocation)
    if not bool(np.isfinite(alloc)) or alloc < 0:
        reasons.append("BAD_ALLOCATION")
        alloc = 0.0

    ml = float(max_leverage)
    if not bool(np.isfinite(ml)) or ml <= 0:
        reasons.append("BAD_MAX_LEVERAGE")
        ml = 1.0

    expert_pos = float(sig.target_position)
    if not bool(np.isfinite(expert_pos)):
        reasons.append("BAD_EXPERT_TARGET")
        expert_pos = 0.0

    follower_target = float(np.clip(expert_pos * alloc, -ml, ml))

    if abs(follower_target) > ml + 1e-12:
        reasons.append("MAX_LEVERAGE")
        follower_target = float(np.clip(follower_target, -ml, ml))

    executed = False
    fill: PaperFill | None = None

    if reasons:
        write_alert(
            level="warning",
            code="COPY_TRADE_BLOCK",
            message="Copy trade blocked by validation",
            payload={"reasons": list(reasons)},
        )

        res = CopyTradeOnceResult(
            ok=False,
            executed=False,
            mid_price=mid,
            expert_target_position=float(expert_pos),
            follower_target_position=float(follower_target),
            fill=None,
            reasons=list(reasons),
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        append_event("copy_trade_once", {"ok": False, "reasons": list(reasons)})
        return res

    state = load_state(state_path)
    new_state, fill = execute_to_target(
        state=state,
        target_position=float(follower_target),
        mid_price=mid,
        fee_bps=float(fee_bps),
        slippage_bps=float(slippage_bps),
    )
    save_state(state_path, new_state)
    executed = True

    write_metrics(
        {
            "copy_cash": float(new_state.cash),
            "copy_position_units": float(new_state.position_units),
            "copy_fees_paid": float(new_state.fees_paid),
            "copy_equity": float(new_state.cash + new_state.position_units * mid),
            "copy_mid_price": float(mid),
            "copy_expert_target_position": float(expert_pos),
            "copy_follower_target_position": float(follower_target),
            "copy_allocation": float(alloc),
        }
    )

    append_event(
        "copy_trade_once",
        {
            "ok": True,
            "executed": True,
            "mid_price": float(mid),
            "expert_target_position": float(expert_pos),
            "follower_target_position": float(follower_target),
            "allocation": float(alloc),
            "fill": None if fill is None else fill.__dict__,
        },
    )

    res = CopyTradeOnceResult(
        ok=True,
        executed=executed,
        mid_price=mid,
        expert_target_position=float(expert_pos),
        follower_target_position=float(follower_target),
        fill=fill,
        reasons=[],
        state_path=str(state_path),
        report_path=str(report_path),
    )
    _write_report(report_path, res)
    return res


def _write_report(path: str | Path, res: CopyTradeOnceResult) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = res.__dict__.copy()
    if res.fill is not None:
        payload["fill"] = res.fill.__dict__
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
