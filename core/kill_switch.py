from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KillSwitchState:
    trading_enabled: bool
    reason: str | None = None


class KillSwitchEngine:
    """
    Global trading safety layer.
    Decides if system is allowed to open NEW trades.
    """

    def __init__(
        self,
        max_daily_loss_pct: float = 5.0,
        max_drawdown_pct: float = 20.0,
        max_loss_streak: int = 6,
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_loss_streak = max_loss_streak

    def evaluate(
        self,
        *,
        daily_loss_pct: float,
        drawdown_pct: float,
        loss_streak: int,
    ) -> KillSwitchState:

        if drawdown_pct >= self.max_drawdown_pct:
            return KillSwitchState(
                trading_enabled=False,
                reason=f"MAX_DRAWDOWN_EXCEEDED ({drawdown_pct:.2f}%)"
            )

        if daily_loss_pct >= self.max_daily_loss_pct:
            return KillSwitchState(
                trading_enabled=False,
                reason=f"MAX_DAILY_LOSS_EXCEEDED ({daily_loss_pct:.2f}%)"
            )

        if loss_streak >= self.max_loss_streak:
            return KillSwitchState(
                trading_enabled=False,
                reason=f"LOSS_STREAK_EXCEEDED ({loss_streak})"
            )

        return KillSwitchState(trading_enabled=True)
