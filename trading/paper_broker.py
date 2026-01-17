from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class PaperState:
    cash: float
    position_units: float
    fees_paid: float

    @staticmethod
    def default() -> "PaperState":
        return PaperState(cash=10_000.0, position_units=0.0, fees_paid=0.0)


@dataclass(frozen=True)
class PaperFill:
    ok: bool
    price: float
    delta_units: float
    fee: float
    cash_after: float
    position_units_after: float
    equity_after: float


def load_state(path: str | Path) -> PaperState:
    p = Path(path)
    if not p.exists():
        return PaperState.default()
    raw = json.loads(p.read_text(encoding="utf-8"))
    return PaperState(
        cash=float(raw.get("cash", 10_000.0)),
        position_units=float(raw.get("position_units", 0.0)),
        fees_paid=float(raw.get("fees_paid", 0.0)),
    )


def save_state(path: str | Path, state: PaperState) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state.__dict__, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def equity(state: PaperState, *, price: float) -> float:
    return float(state.cash + state.position_units * float(price))


def target_units_from_position(
    *,
    target_position: float,
    equity_value: float,
    price: float,
) -> float:
    price = float(price)
    if price <= 0:
        return 0.0
    return float(target_position) * float(equity_value) / price


def execute_to_target(
    *,
    state: PaperState,
    target_position: float,
    mid_price: float,
    fee_bps: float = 1.0,
    slippage_bps: float = 1.0,
) -> tuple[PaperState, PaperFill]:
    mid = float(mid_price)
    if mid <= 0:
        f = PaperFill(
            ok=False,
            price=mid,
            delta_units=0.0,
            fee=0.0,
            cash_after=state.cash,
            position_units_after=state.position_units,
            equity_after=equity(state, price=mid if mid > 0 else 1.0),
        )
        return state, f

    eq = equity(state, price=mid)
    tgt_units = target_units_from_position(target_position=target_position, equity_value=eq, price=mid)
    delta_units = float(tgt_units - state.position_units)

    if abs(delta_units) <= 1e-12:
        f = PaperFill(
            ok=True,
            price=mid,
            delta_units=0.0,
            fee=0.0,
            cash_after=state.cash,
            position_units_after=state.position_units,
            equity_after=equity(state, price=mid),
        )
        return state, f

    slip = float(slippage_bps) / 10_000.0
    exec_price = mid * (1.0 + slip * (1.0 if delta_units > 0 else -1.0))

    fee_rate = float(fee_bps) / 10_000.0

    # Prevent negative cash for buys (paper trading without margin).
    # Total cost for a buy: delta * exec_price * (1 + fee_rate)
    if delta_units > 0:
        denom = exec_price * (1.0 + fee_rate)
        if denom > 0:
            max_delta = float(max(0.0, state.cash / denom))
            if delta_units > max_delta:
                delta_units = max_delta
                tgt_units = float(state.position_units + delta_units)

    notional = abs(delta_units) * exec_price
    fee = notional * fee_rate

    cash_after = float(state.cash - delta_units * exec_price - fee)
    pos_after = float(tgt_units)

    new_state = PaperState(
        cash=cash_after,
        position_units=pos_after,
        fees_paid=float(state.fees_paid + fee),
    )

    f = PaperFill(
        ok=True,
        price=float(exec_price),
        delta_units=float(delta_units),
        fee=float(fee),
        cash_after=new_state.cash,
        position_units_after=new_state.position_units,
        equity_after=equity(new_state, price=mid),
    )
    return new_state, f
