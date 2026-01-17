from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_parquet(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    return pd.read_parquet(p)


def load_parquets(paths: list[str | Path]) -> list[pd.DataFrame]:
    return [load_parquet(p) for p in paths]
