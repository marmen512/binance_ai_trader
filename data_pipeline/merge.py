from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_pipeline.schema import OhlcvSchema


@dataclass(frozen=True)
class MergeResult:
    df: pd.DataFrame
    dropped_duplicates: int


def merge_datasets(dfs: list[pd.DataFrame], schema: OhlcvSchema | None = None) -> MergeResult:
    s = schema or OhlcvSchema()
    if not dfs:
        return MergeResult(df=pd.DataFrame(), dropped_duplicates=0)

    merged = pd.concat(dfs, ignore_index=True, copy=False)
    merged = merged.sort_values(s.timestamp)

    before = int(merged.shape[0])
    merged = merged.drop_duplicates(subset=[s.timestamp], keep="last")
    after = int(merged.shape[0])

    return MergeResult(df=merged.reset_index(drop=True), dropped_duplicates=before - after)
