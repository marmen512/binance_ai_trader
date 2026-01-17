from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskGateDecision:
    ok: bool
    reason: str | None


def allow_trade(state, prediction, confidence, config) -> bool:
    """Returns True if trade is allowed."""

    dec = allow_trade_with_reason(state=state, prediction=prediction, confidence=confidence, config=config)
    return bool(dec.ok)


def allow_trade_with_reason(*, state, prediction, confidence, config) -> RiskGateDecision:
    try:
        pos_units = float(getattr(state, "position_units", 0.0) or 0.0)
    except Exception:
        pos_units = 0.0

    if abs(pos_units) > 1e-12:
        return RiskGateDecision(ok=False, reason="already_in_position")

    try:
        thr = float(config.get("classifier_min_conf"))
    except Exception:
        thr = 0.0

    if float(confidence) < float(thr):
        return RiskGateDecision(ok=False, reason="low_confidence")

    try:
        cooldown_candles = int(config.get("cooldown_candles") or 0)
    except Exception:
        cooldown_candles = 0

    if cooldown_candles > 0:
        last_trade_close_time_ms = config.get("last_trade_close_time_ms")
        current_close_time_ms = config.get("current_close_time_ms")
        if last_trade_close_time_ms is not None and current_close_time_ms is not None:
            try:
                hours_ms = int(cooldown_candles) * 60 * 60 * 1000
                if int(current_close_time_ms) <= int(last_trade_close_time_ms) + int(hours_ms):
                    return RiskGateDecision(ok=False, reason="cooldown")
            except Exception:
                pass

    return RiskGateDecision(ok=True, reason=None)
