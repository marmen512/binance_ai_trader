from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class LeaderState:
    leader_id: str
    base_score: float
    last_trade_ts: str
    loss_streak: int


class LeaderDecayEngine:
    def __init__(
        self,
        inactivity_days_limit: int = 7,
        loss_streak_limit: int = 5,
    ):
        self.inactivity_days_limit = inactivity_days_limit
        self.loss_streak_limit = loss_streak_limit

    def _days_since(self, ts: str) -> float:
        dt = datetime.fromisoformat(ts)
        now = datetime.now(UTC)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)

        return (now - dt).days

    def inactivity_decay(self, state: LeaderState) -> float:
        days = self._days_since(state.last_trade_ts)

        if days <= 1:
            return 1.0
        if days >= self.inactivity_days_limit:
            return 0.3

        return 1.0 - (days / self.inactivity_days_limit) * 0.7

    def loss_decay(self, state: LeaderState) -> float:
        if state.loss_streak <= 1:
            return 1.0
        if state.loss_streak >= self.loss_streak_limit:
            return 0.2

        return 1.0 - (state.loss_streak / self.loss_streak_limit) * 0.8

    def effective_score(self, state: LeaderState) -> float:
        score = state.base_score
        score *= self.inactivity_decay(state)
        score *= self.loss_decay(state)
        return round(score, 4)
