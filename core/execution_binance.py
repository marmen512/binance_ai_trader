"""
REAL BINANCE EXECUTION
Requires python-binance installed.
"""

from binance.client import Client
from core.execution_adapter import ExecutionAdapter


class BinanceExecutionAdapter(ExecutionAdapter):

    def __init__(self, api_key, api_secret, testnet=True):

        if testnet:
            self.client = Client(api_key, api_secret, testnet=True)
        else:
            self.client = Client(api_key, api_secret)

    # -----------------

    def open_position(self, symbol, side, qty):

        self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=qty,
        )

    def close_position(self, symbol):

        # Simplified: assumes opposite market order
        # In real version you query current position size

        pass

    def adjust_position(self, symbol, delta_qty):

        if delta_qty == 0:
            return

        side = "BUY" if delta_qty > 0 else "SELL"

        self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=abs(delta_qty),
        )
