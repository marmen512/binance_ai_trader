"""
Execution Adapter Interface
Allows switching between Paper / Binance / Simulator.
"""

from abc import ABC, abstractmethod


class ExecutionAdapter(ABC):

    @abstractmethod
    def open_position(self, symbol: str, side: str, qty: float):
        pass

    @abstractmethod
    def close_position(self, symbol: str):
        pass

    @abstractmethod
    def adjust_position(self, symbol: str, delta_qty: float):
        pass
