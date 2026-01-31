"""
Unit tests for finance utilities.
"""
import pytest
from datetime import datetime
from app.services.finance_utils import compute_pnl_from_orders


class TestFinanceUtils:
    """Tests for finance utility functions."""

    def test_compute_pnl_simple_buy_sell(self):
        """Test simple buy-sell PnL calculation."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.1},
            {"qty": 1.0, "price": 110.0, "side": "sell", "fee": 0.1},
        ]
        pnl = compute_pnl_from_orders(orders)
        expected = (110.0 - 100.0) - (0.1 + 0.1)  # profit minus fees
        assert round(pnl, 2) == round(expected, 2)

    def test_compute_pnl_loss(self):
        """Test PnL calculation with a loss."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.1},
            {"qty": 1.0, "price": 90.0, "side": "sell", "fee": 0.1},
        ]
        pnl = compute_pnl_from_orders(orders)
        expected = (90.0 - 100.0) - (0.1 + 0.1)  # loss minus fees
        assert round(pnl, 2) == round(expected, 2)

    def test_compute_pnl_multiple_trades(self):
        """Test PnL with multiple trades."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.1},
            {"qty": 0.5, "price": 110.0, "side": "sell", "fee": 0.05},
            {"qty": 0.5, "price": 105.0, "side": "sell", "fee": 0.05},
        ]
        pnl = compute_pnl_from_orders(orders)
        # First sell: 0.5 * (110 - 100) = 5
        # Second sell: 0.5 * (105 - 100) = 2.5
        # Total profit: 7.5 - 0.2 (fees) = 7.3
        assert round(pnl, 2) == 7.3

    def test_compute_pnl_no_position(self):
        """Test PnL when selling without position (edge case)."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "sell", "fee": 0.1},
        ]
        pnl = compute_pnl_from_orders(orders)
        # Selling without position: proceeds - fee
        expected = 100.0 - 0.1
        assert round(pnl, 2) == round(expected, 2)

    def test_compute_pnl_zero_fees(self):
        """Test PnL calculation with zero fees."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "buy", "fee": 0.0},
            {"qty": 1.0, "price": 110.0, "side": "sell", "fee": 0.0},
        ]
        pnl = compute_pnl_from_orders(orders)
        assert round(pnl, 2) == 10.0

    def test_compute_pnl_missing_fee(self):
        """Test that missing fee defaults to 0."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "buy"},  # No fee field
            {"qty": 1.0, "price": 110.0, "side": "sell"},
        ]
        pnl = compute_pnl_from_orders(orders)
        assert round(pnl, 2) == 10.0

    def test_compute_pnl_case_insensitive_side(self):
        """Test that side is case-insensitive."""
        orders = [
            {"qty": 1.0, "price": 100.0, "side": "BUY", "fee": 0.1},
            {"qty": 1.0, "price": 110.0, "side": "SELL", "fee": 0.1},
        ]
        pnl = compute_pnl_from_orders(orders)
        assert round(pnl, 2) == 9.8

    def test_compute_pnl_empty_orders(self):
        """Test PnL with empty order list."""
        orders = []
        pnl = compute_pnl_from_orders(orders)
        assert pnl == 0.0

    def test_compute_pnl_with_timestamp(self):
        """Test that timestamp field doesn't affect calculation."""
        orders = [
            {
                "qty": 1.0,
                "price": 100.0,
                "side": "buy",
                "fee": 0.1,
                "timestamp": datetime.now().isoformat(),
            },
            {
                "qty": 1.0,
                "price": 110.0,
                "side": "sell",
                "fee": 0.1,
                "timestamp": datetime.now().isoformat(),
            },
        ]
        pnl = compute_pnl_from_orders(orders)
        assert round(pnl, 2) == 9.8
