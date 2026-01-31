from dataclasses import dataclass
from typing import Optional


@dataclass
class Trade:
    trade_id: str
    source: str          # strategy | leader
    leader_id: Optional[str]

    symbol: str
    side: str            # BUY / SELL

    entry_price: float
    exit_price: Optional[float]

    qty: float

    pnl: Optional[float]

    opened_at: str
    closed_at: Optional[str]
