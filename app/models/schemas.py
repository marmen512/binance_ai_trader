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
    orders: Optional[List[OrderSchema]] = None
