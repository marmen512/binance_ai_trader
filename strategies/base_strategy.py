from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class StrategyResult:
    name: str
    position: pd.Series


class BaseStrategy(Protocol):
    name: str

    def generate(self, df: pd.DataFrame) -> StrategyResult: ...
