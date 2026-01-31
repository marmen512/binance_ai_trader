from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExposureResult:
    allowed: bool
    reason: str | None = None


class ExposureManager:
    """
    Account-level exposure control.
    """

    def __init__(
        self,
        max_symbol_exposure_pct: float = 30.0,
        max_total_long_pct: float = 70.0,
        max_total_short_pct: float = 70.0,
    ):
        self.max_symbol_exposure_pct = max_symbol_exposure_pct
        self.max_total_long_pct = max_total_long_pct
        self.max_total_short_pct = max_total_short_pct

    def check(
        self,
        *,
        symbol: str,
        side: str,  # BUY or SELL
        new_position_pct: float,
        current_symbol_pct: float,
        total_long_pct: float,
        total_short_pct: float,
    ) -> ExposureResult:

        # Symbol cap
        if current_symbol_pct + new_position_pct > self.max_symbol_exposure_pct:
            return ExposureResult(False, "MAX_SYMBOL_EXPOSURE")

        # Side caps
        if side == "BUY":
            if total_long_pct + new_position_pct > self.max_total_long_pct:
                return ExposureResult(False, "MAX_LONG_EXPOSURE")

        if side == "SELL":
            if total_short_pct + new_position_pct > self.max_total_short_pct:
                return ExposureResult(False, "MAX_SHORT_EXPOSURE")

        return ExposureResult(True)
