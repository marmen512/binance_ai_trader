"""
COPY TRADING ENGINE — SKELETON
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CopyTrade:
    leader_id: str
    symbol: str
    side: str
    entry_price: float
    qty: float
    trade_id: str


class CopyExecutionEngine:

    def __init__(self, risk_factor=0.2):
        self.risk_factor = risk_factor

    def scale_qty(self, leader_qty: float) -> float:
        return leader_qty * self.risk_factor

    def build_copy_trade(self, leader_trade: dict) -> CopyTrade:

        my_qty = self.scale_qty(leader_trade["qty"])

        return CopyTrade(
            leader_id=leader_trade["leader_id"],
            symbol=leader_trade["symbol"],
            side=leader_trade["side"],
            entry_price=leader_trade["entry_price"],
            qty=my_qty,
            trade_id=leader_trade["trade_id"],
        )

    def execute_copy(self, leader_trade: dict):

        trade = self.build_copy_trade(leader_trade)

        print(f"[COPY] {trade.symbol} {trade.side} qty={trade.qty}")

        return trade
