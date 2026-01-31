"""
Finance utilities for computing PnL and other financial metrics.
"""

def compute_pnl_from_orders(orders):
    """
    Simple FIFO-based realized PnL for a sequence of orders.
    Works as a baseline version — extend as needed.
    
    Args:
        orders: List of order dictionaries with keys: qty, price, side, fee
        
    Returns:
        float: Realized PnL after fees
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
                # If no position — treat as opening short/atypical situation
                realized += proceeds
    
    pnl = realized - fees
    return pnl
