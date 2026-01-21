from app.services.finance_utils import compute_pnl_from_orders
from datetime import datetime

def test_simple_buy_sell():
    orders = [
        {"type":"market","price":100.0,"qty":1.0,"side":"buy","fee":0.1,"timestamp":datetime.utcnow().isoformat()},
        {"type":"market","price":110.0,"qty":1.0,"side":"sell","fee":0.1,"timestamp":datetime.utcnow().isoformat()},
    ]
    pnl = compute_pnl_from_orders(orders)
    assert round(pnl, 2) == round((110.0 - 100.0) - (0.1 + 0.1), 2)
