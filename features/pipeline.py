from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_pipeline.normalization import normalize_columns
from data_pipeline.parquet_loader import load_parquets
from data_pipeline.merge import merge_datasets
from data_pipeline.validation import validate_ohlcv
from features.copy_trader_stats import add_copy_trader_stats
from features.technical import add_technical_features
from features.time_features import add_time_features
from features.volatility import add_volatility_features
from features.volume import add_volume_features


@dataclass(frozen=True)
class BuildFeaturesResult:
    ok: bool
    rows_in: int
    rows_out: int
    features_added: list[str]
    output_path: str


def build_features(
    paths: list[str | Path],
    *,
    output_path: str | Path,
) -> BuildFeaturesResult:
    dfs = load_parquets(paths)
    dfs = [normalize_columns(df) for df in dfs]

    merged = merge_datasets(dfs).df
    report = validate_ohlcv(merged)
    if not report.ok:
        return BuildFeaturesResult(
            ok=False,
            rows_in=int(merged.shape[0]),
            rows_out=0,
            features_added=[],
            output_path=str(output_path),
        )

    out = merged.copy()
    base_cols = set(out.columns)

    out = add_technical_features(out)
    out = add_volatility_features(out)
    out = add_volume_features(out)
    out = add_time_features(out)
    out = add_copy_trader_stats(out)

    added = [c for c in out.columns if c not in base_cols]

    # Drop rows with any NaNs introduced by rolling windows
    out2 = out.dropna().reset_index(drop=True)

    if out2.empty:
        return BuildFeaturesResult(
            ok=False,
            rows_in=int(out.shape[0]),
            rows_out=0,
            features_added=sorted(added),
            output_path=str(output_path),
        )

    op = Path(output_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    out2.to_parquet(op, index=False)

    return BuildFeaturesResult(
        ok=True,
        rows_in=int(out.shape[0]),
        rows_out=int(out2.shape[0]),
        features_added=sorted(added),
        output_path=str(op),
    )
