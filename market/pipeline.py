from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_pipeline.merge import merge_datasets
from data_pipeline.normalization import normalize_columns
from data_pipeline.parquet_loader import load_parquets
from data_pipeline.validation import validate_ohlcv
from market.regime_detector import detect_regime


@dataclass(frozen=True)
class DetectRegimeResult:
    ok: bool
    rows_in: int
    rows_out: int
    output_path: str
    counts: dict[str, int]


def detect_regime_pipeline(
    paths: list[str | Path],
    *,
    output_path: str | Path,
    vol_high_q: float = 0.80,
    bb_width_high_q: float = 0.80,
    liq_low_q: float = 0.10,
    trend_strength_q: float = 0.70,
) -> DetectRegimeResult:
    dfs = load_parquets(paths)
    dfs = [normalize_columns(df) for df in dfs]

    merged = merge_datasets(dfs).df
    report = validate_ohlcv(merged)
    if not report.ok:
        return DetectRegimeResult(
            ok=False,
            rows_in=int(merged.shape[0]),
            rows_out=0,
            output_path=str(output_path),
            counts={},
        )

    out = detect_regime(
        merged,
        vol_high_q=vol_high_q,
        bb_width_high_q=bb_width_high_q,
        liq_low_q=liq_low_q,
        trend_strength_q=trend_strength_q,
    )

    if "market_regime" not in out.columns:
        return DetectRegimeResult(
            ok=False,
            rows_in=int(out.shape[0]),
            rows_out=0,
            output_path=str(output_path),
            counts={},
        )

    out2 = out.dropna(subset=["market_regime"]).reset_index(drop=True)
    counts = out2["market_regime"].value_counts(dropna=False).to_dict()

    if out2.empty:
        return DetectRegimeResult(
            ok=False,
            rows_in=int(out.shape[0]),
            rows_out=0,
            output_path=str(output_path),
            counts={k: int(v) for k, v in counts.items()},
        )

    op = Path(output_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    out2.to_parquet(op, index=False)

    return DetectRegimeResult(
        ok=True,
        rows_in=int(out.shape[0]),
        rows_out=int(out2.shape[0]),
        output_path=str(op),
        counts={k: int(v) for k, v in counts.items()},
    )
