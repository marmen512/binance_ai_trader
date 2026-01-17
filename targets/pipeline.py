from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_pipeline.normalization import normalize_columns
from data_pipeline.parquet_loader import load_parquets
from data_pipeline.merge import merge_datasets
from data_pipeline.validation import validate_ohlcv
from targets.direction_target import build_direction_target
from targets.trade_validity_target import build_trade_validity_target


@dataclass(frozen=True)
class BuildTargetsResult:
    ok: bool
    rows_in: int
    rows_out: int
    output_path: str


def build_targets(
    paths: list[str | Path],
    *,
    output_path: str | Path,
    horizon: int = 1,
    lower_q: float = 0.33,
    upper_q: float = 0.66,
    atr_min_pct: float = 0.0005,
    bb_width_min: float = 0.002,
    rsi_low: float = 30.0,
    rsi_high: float = 70.0,
    volume_z_min: float = -1.0,
) -> BuildTargetsResult:
    dfs = load_parquets(paths)
    dfs = [normalize_columns(df) for df in dfs]

    merged = merge_datasets(dfs).df
    report = validate_ohlcv(merged)
    if not report.ok:
        return BuildTargetsResult(
            ok=False,
            rows_in=int(merged.shape[0]),
            rows_out=0,
            output_path=str(output_path),
        )

    out = merged.copy()

    out = build_direction_target(out, horizon=horizon, lower_q=lower_q, upper_q=upper_q)
    out = build_trade_validity_target(
        out,
        atr_min_pct=atr_min_pct,
        bb_width_min=bb_width_min,
        rsi_low=rsi_low,
        rsi_high=rsi_high,
        volume_z_min=volume_z_min,
    )

    out2 = out.dropna(subset=["direction_target", "trade_validity_target", "future_log_return"]).reset_index(
        drop=True
    )

    if out2.empty:
        return BuildTargetsResult(
            ok=False,
            rows_in=int(out.shape[0]),
            rows_out=0,
            output_path=str(output_path),
        )

    op = Path(output_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    out2.to_parquet(op, index=False)

    return BuildTargetsResult(
        ok=True,
        rows_in=int(out.shape[0]),
        rows_out=int(out2.shape[0]),
        output_path=str(op),
    )
