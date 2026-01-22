from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class OrderSchema(BaseModel):
    type: str
    price: Optional[float] = None
    qty: float
    side: str
    fee: Optional[float] = 0.0
    timestamp: datetime

class SignalIn(BaseModel):
    trader_id: str
    source: str
    external_id: str
    timestamp: datetime
    symbol: str
    side: str
    price: Optional[float] = None
    quantity: float
    leverage: Optional[float] = 1.0
    pnl: Optional[float] = None
    orders: Optional[List[Order > app/services/finance_utils.py <<'PY'
def compute_pnl_from_orders(orders):
    """
    Простий FIFO-based realized PnL для послідовності ордерів.
    Працює як базова версія — розширити при необхідності.
    """
    pos = 0.0
    cost = 0.0
    realized = 0.0
    fees = 0.0
    for o in orders:
        qty = float(o.get("qty", 0))
        price = float(o.get("price") or 0)
        fee = float(o.get("fee", 0) or 0)
        side = o.get("side", "").lower()
        fees += fee
        if side == "buy":
            cost += qty * price
            pos += qty
        elif side == "sell":
            proceeds = qty * price
            if pos > 0:
                avg_cost = cost / pos if pos != 0 else 0
                realized += proceeds - (avg_cost * qty)
                cost -= avg_cost * qty
                pos -= qty
            else:
                # якщо немає позиції — трактуємо як відкриття шорт/нетипову ситуацію
                realized += proceeds
    pnl = realized - fees
    return pnl
