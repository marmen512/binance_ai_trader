"""
RISK MANAGER — COPY TRADING PROTECTION LAYER
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class RiskConfig:
    max_risk_per_trade_pct: float = 1.0
    max_daily_loss_pct: float = 5.0
    max_open_trades: int = 5


class RiskManager:

    def __init__(self, balance: float, config: RiskConfig | None = None):
        self.balance = balance
        self.config = config or RiskConfig()

        self.daily_loss = 0.0
        self.open_trades = 0
        self.current_day = datetime.utcnow().date()

    # ---------------------

    def _roll_day(self):
        today = datetime.utcnow().date()
        if today != self.current_day:
            self.daily_loss = 0.0
            self.current_day = today

    # ---------------------

    def can_open_trade(self, trade_risk_usd: float) -> tuple[bool, str]:

        self._roll_day()

        # max open trades
        if self.open_trades >= self.config.max_open_trades:
            return False, "MAX_OPEN_TRADES"

        # risk per trade
        risk_pct = (trade_risk_usd / self.balance) * 100
        if risk_pct > self.config.max_risk_per_trade_pct:
            return False, "TRADE_RISK_TOO_HIGH"

        # daily loss limit
        daily_loss_pct = (self.daily_loss / self.balance) * 100
        if daily_loss_pct >= self.config.max_daily_loss_pct:
            return False, "DAILY_LOSS_LIMIT"

        return True, "OK"

    # ---------------------

    def register_open_trade(self):
        self.open_trades += 1

    def register_close_trade(self, pnl_usd: float):
        self.open_trades = max(0, self.open_trades - 1)

        if pnl_usd < 0:
            self.daily_loss += abs(pnl_usd)

