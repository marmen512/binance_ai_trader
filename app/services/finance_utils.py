"""
Finance utilities for computing PnL and other financial metrics.

This module provides utilities for financial calculations including:
- Profit and Loss (PnL) computation from trading orders
- Position tracking and cost basis calculation
- Fee and slippage accounting
"""

from __future__ import annotations
from typing import Any

def compute_pnl_from_orders(orders: list[dict[str, Any]]) -> float:
    """
    Compute realized PnL from a sequence of orders using FIFO accounting.
    
    This function calculates the realized profit and loss from a series of
    trading orders by tracking position size, cost basis, and fees. It uses
    First-In-First-Out (FIFO) accounting for position management.
    
    The calculation:
    - Tracks long position (positive) and cost basis
    - For BUY orders: increases position and cost
    - For SELL orders: realizes PnL based on average cost, decreases position
    - Subtracts all fees from realized PnL
    
    Args:
        orders: List of order dictionaries, each containing:
            - qty (float): Order quantity
            - price (float): Order execution price
            - side (str): Order side, either "buy" or "sell" (case-insensitive)
            - fee (float, optional): Transaction fee, defaults to 0
            - timestamp (str, optional): Order timestamp (not used in calculation)
            - type (str, optional): Order type (not used in calculation)
        
    Returns:
        float: Realized PnL after fees. Positive values indicate profit,
               negative values indicate loss.
    
    Example:
        >>> orders = [
        ...     {"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.1},
        ...     {"qty": 1.0, "price": 110.0, "side": "sell", "fee": 0.1},
        ... ]
        >>> pnl = compute_pnl_from_orders(orders)
        >>> round(pnl, 2)
        9.8
    
    Note:
        This is a baseline implementation. Extend as needed for:
        - Short positions
        - Multiple position exits
        - Complex order types
        - Unrealized PnL tracking
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
                avg_cost = cost / pos
                realized += proceeds - (avg_cost * qty)
                cost -= avg_cost * qty
                pos -= qty
            else:
                # If no position — treat as opening short/atypical situation
                realized += proceeds
    
    pnl = realized - fees
    return pnl
