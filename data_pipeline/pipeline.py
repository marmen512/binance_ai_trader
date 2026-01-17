from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from data_pipeline.dataset_registry import DatasetCard, write_dataset_card
from data_pipeline.merge import MergeResult, merge_datasets
from data_pipeline.normalization import normalize_columns
from data_pipeline.parquet_loader import load_parquets
from data_pipeline.validation import ValidationReport, validate_ohlcv


@dataclass(frozen=True)
class ValidateDataResult:
    report: ValidationReport
    merge: MergeResult
    card: DatasetCard | None


def validate_data(
    paths: list[str | Path],
    *,
    write_registry: bool = True,
    registry_dir: str | Path = Path("ai_data") / "data_registry",
) -> ValidateDataResult:
    dfs = load_parquets(paths)
    dfs = [normalize_columns(df) for df in dfs]

    merge_res = merge_datasets(dfs)
    report = validate_ohlcv(merge_res.df)

    card = None
    if write_registry and report.ok:
        card = write_dataset_card(
            registry_dir,
            [str(p) for p in paths],
            rows=report.rows,
            start_ts=report.start_ts,
            end_ts=report.end_ts,
        )

    return ValidateDataResult(report=report, merge=merge_res, card=card)
