from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExecutionGuardResult:
    allowed: bool
    reason: str | None = None


class ExecutionGuard:
    """
    Prevents bad execution decisions:
    - duplicate direction
    - too many open trades
    - symbol exposure limits
    """

    def __init__(
        self,
        max_open_positions: int = 5,
        max_symbol_positions: int = 2,
    ):
        self.max_open_positions = max_open_positions
        self.max_symbol_positions = max_symbol_positions

    def check(
        self,
        *,
        symbol: str,
        direction: str,
        open_positions: list[dict],
    ) -> ExecutionGuardResult:

        # Total positions limit
        if len(open_positions) >= self.max_open_positions:
            return ExecutionGuardResult(False, "MAX_OPEN_POSITIONS")

        # Same symbol limit
        symbol_positions = [
            p for p in open_positions
            if p["symbol"] == symbol
        ]

        if len(symbol_positions) >= self.max_symbol_positions:
            return ExecutionGuardResult(False, "MAX_SYMBOL_POSITIONS")

        # Duplicate direction
        for p in symbol_positions:
            if p["direction"] == direction:
                return ExecutionGuardResult(False, "DUPLICATE_DIRECTION")

        return ExecutionGuardResult(True)
