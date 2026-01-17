from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.registry import write_registry_card
from data_pipeline.validators import validate_sentiment_agg_5m


@dataclass(frozen=True)
class AggregateSentimentResult:
    ok: bool
    freq: str
    rows_in: int
    rows_out: int
    output_path: str


def _roll_window(freq: str) -> int:
    if freq == "5m":
        return 288
    if freq == "1h":
        return 24
    if freq == "4h":
        return 42
    if freq == "1d":
        return 30
    return 24


def aggregate_sentiment(
    *,
    raw_path: str | Path = Path("ai_data") / "sentiment" / "raw" / "sentiment_raw.parquet",
    out_dir: str | Path | None = Path("ai_data") / "sentiment" / "aggregated",
    out_path: str | Path | None = None,
    freq: str = "1h",
) -> AggregateSentimentResult:
    freq = str(freq).strip().lower()
    if freq not in {"5m", "1h", "4h", "1d"}:
        raise BinanceAITraderError("freq must be one of: 5m, 1h, 4h, 1d")

    rp = Path(raw_path)
    if not rp.exists():
        raise BinanceAITraderError(f"Sentiment raw dataset missing: {rp}")

    df = pd.read_parquet(rp)
    if "timestamp" not in df.columns or "sentiment" not in df.columns:
        raise BinanceAITraderError("Sentiment raw must have columns: timestamp, sentiment")

    ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    s = pd.to_numeric(df["sentiment"], errors="coerce")
    base = pd.DataFrame({"timestamp": ts, "sentiment": s}).dropna().copy()
    base = base.sort_values("timestamp").reset_index(drop=True)
    if base.empty:
        raise BinanceAITraderError("Sentiment raw is empty after normalization")

    base = base.set_index("timestamp")
    resample_rule = "5min" if freq == "5m" else freq
    g = base["sentiment"].resample(resample_rule, label="right", closed="right")

    mean = g.mean()
    std = g.std(ddof=0)
    count = g.count().astype("float64")

    out = pd.DataFrame(
        {
            "timestamp": mean.index,
            "sentiment_mean": mean.astype("float64"),
            "sentiment_std": std.astype("float64"),
            "sentiment_count": count.astype("float64"),
        }
    )

    out = out.reset_index(drop=True)

    w = int(_roll_window(freq))
    out["sentiment_trend"] = out["sentiment_mean"].diff().fillna(0.0).astype("float64")
    out["sentiment_volatility"] = (
        out["sentiment_mean"].rolling(w, min_periods=max(2, w // 4)).std(ddof=0).fillna(0.0).astype("float64")
    )
    out2 = out.reset_index(drop=True)
    out2["sentiment_mean"] = out2["sentiment_mean"].fillna(0.0).astype("float64")
    out2["sentiment_std"] = out2["sentiment_std"].fillna(0.0).astype("float64")
    out2["sentiment_count"] = out2["sentiment_count"].fillna(0.0).astype("float64")

    if out2.empty:
        raise BinanceAITraderError("Sentiment aggregation resulted in empty dataset")

    if out_path is not None:
        op = Path(out_path)
        op.parent.mkdir(parents=True, exist_ok=True)
        od = op.parent
    else:
        od = Path(out_dir) if out_dir is not None else Path("ai_data") / "sentiment" / "aggregated"
        od.mkdir(parents=True, exist_ok=True)
        op = od / f"sentiment_{freq}.parquet"

        if str(freq) == "1h":
            op = Path("ai_data") / "sentiment" / "sentiment_1h.parquet"
            op.parent.mkdir(parents=True, exist_ok=True)

        if str(freq) == "5m":
            op = Path("ai_data") / "sentiment" / "aggregated" / "sentiment_5m.parquet"
            op.parent.mkdir(parents=True, exist_ok=True)

    if op.exists():
        raise BinanceAITraderError(f"Refusing to overwrite existing sentiment aggregated: {op}")
    out2.to_parquet(op, index=False)

    if str(freq) == "5m":
        reg_path = Path("ai_data") / "dataset_registry" / "sentiment_5m.json"
        if reg_path.exists():
            raise BinanceAITraderError(f"Refusing to overwrite registry card: {reg_path}")

        # Validate AFTER save (contract).
        saved = pd.read_parquet(op)
        validate_sentiment_agg_5m(saved, nan_max_ratio=0.01)

        start_ts = pd.to_datetime(saved["timestamp"], utc=True).min()
        end_ts = pd.to_datetime(saved["timestamp"], utc=True).max()
        write_registry_card(
            out_path=reg_path,
            name="sentiment_aggregated_5m",
            source="derived",
            data_path=op,
            frequency="5m",
            columns=list(saved.columns),
            start_ts=start_ts,
            end_ts=end_ts,
        )

        return AggregateSentimentResult(
            ok=True,
            freq=freq,
            rows_in=int(base.shape[0]),
            rows_out=int(out2.shape[0]),
            output_path=str(op),
        )

    card_path = od / f"sentiment_{freq}_dataset_card.json"
    if card_path.exists():
        raise BinanceAITraderError(f"Refusing to overwrite existing sentiment card: {card_path}")
    start_ts = pd.to_datetime(out2["timestamp"], utc=True).min()
    end_ts = pd.to_datetime(out2["timestamp"], utc=True).max()
    sha = _sha256_file(op)

    payload = {
        "name": f"sentiment_aggregated_{freq}",
        "source": "derived",
        "hash": f"sha256:{sha}",
        "date_range": f"{start_ts.date().isoformat()} -> {end_ts.date().isoformat()}",
        "frequency": freq,
        "role": "sentiment_aggregated",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    card_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return AggregateSentimentResult(
        ok=True,
        freq=freq,
        rows_in=int(base.shape[0]),
        rows_out=int(out2.shape[0]),
        output_path=str(op),
    )


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
