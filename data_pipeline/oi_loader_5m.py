from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.binance_client import BinanceFuturesClient
from data_pipeline.registry import write_registry_card
from data_pipeline.validators import validate_open_interest_5m


def _to_ms(ts: pd.Timestamp) -> int:
    return int(ts.value // 1_000_000)


def download_open_interest_5m(
    *,
    symbol: str = "BTCUSDT",
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    out_path: str | Path = Path("ai_data") / "derivatives" / "open_interest_5m.parquet",
    registry_path: str | Path = Path("ai_data") / "dataset_registry" / "open_interest_5m.json",
    require_freshness: bool = False,
) -> dict:
    if start_ts.tzinfo is None or end_ts.tzinfo is None:
        raise BinanceAITraderError("open_interest_5m: timestamps must be tz-aware UTC")
    if end_ts <= start_ts:
        raise BinanceAITraderError("open_interest_5m: end_ts must be > start_ts")

    op = Path(out_path)
    if op.exists():
        raise BinanceAITraderError(f"Refusing to overwrite open interest dataset: {op}")
    op.parent.mkdir(parents=True, exist_ok=True)

    rp = Path(registry_path)
    if rp.exists():
        raise BinanceAITraderError(f"Refusing to overwrite open interest registry card: {rp}")
    rp.parent.mkdir(parents=True, exist_ok=True)

    client = BinanceFuturesClient()

    # NOTE: Binance /futures/data/openInterestHist (period=5m) does not support startTime.
    # We must paginate backwards using endTime + limit.
    rows: list[dict] = []
    start_ms = _to_ms(start_ts)
    end_ms = _to_ms(end_ts)
    end_cursor_ms = end_ms

    max_iters = 20_000
    it = 0
    while end_cursor_ms > start_ms:
        it += 1
        if it > max_iters:
            raise BinanceAITraderError("open_interest_5m: exceeded max pagination iterations")

        payload = client.get_json(
            "/futures/data/openInterestHist",
            {
                "symbol": symbol,
                "period": "5m",
                "endTime": int(end_cursor_ms),
                "limit": 500,
            },
        )

        if not isinstance(payload, list) or not payload:
            break

        rows.extend(payload)

        try:
            batch_ts = [int(x["timestamp"]) for x in payload]
        except Exception as e:
            raise BinanceAITraderError(f"open_interest_5m: invalid timestamp in API response: {e}")

        batch_min = int(min(batch_ts))
        new_end_cursor = batch_min - 1
        if new_end_cursor >= end_cursor_ms:
            raise BinanceAITraderError("open_interest_5m: pagination did not progress")
        end_cursor_ms = new_end_cursor

        if batch_min <= start_ms:
            break

    if not rows:
        raise BinanceAITraderError("open_interest_5m: no rows downloaded")

    raw = pd.DataFrame(rows)
    raw["timestamp"] = pd.to_datetime(pd.to_numeric(raw["timestamp"], errors="coerce"), unit="ms", utc=True)

    # Binance returns both sumOpenInterest and sumOpenInterestValue. Use sumOpenInterest.
    oi_col = "sumOpenInterest" if "sumOpenInterest" in raw.columns else "openInterest"
    if oi_col not in raw.columns:
        raise BinanceAITraderError("open_interest_5m: missing open interest column in API response")

    raw["open_interest"] = pd.to_numeric(raw[oi_col], errors="coerce")
    raw = raw.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    # Keep only requested window (no interpolation/resampling).
    raw = raw[(raw["timestamp"] >= start_ts) & (raw["timestamp"] <= end_ts)].reset_index(drop=True)

    out = raw[["timestamp", "open_interest"]].copy()

    if out.empty:
        raise BinanceAITraderError("open_interest_5m: no rows in requested window")

    out.to_parquet(op, index=False)

    # Mandatory: reload from disk and validate using existing validator.
    reloaded = pd.read_parquet(op)
    validate_open_interest_5m(reloaded, nan_max_ratio=0.01, require_freshness=bool(require_freshness))

    card = write_registry_card(
        out_path=rp,
        name="binance_usdtm_futures_open_interest_5m",
        source="binance_futures",
        data_path=op,
        frequency="5m",
        columns=list(out.columns),
        start_ts=pd.to_datetime(out["timestamp"], utc=True).min(),
        end_ts=pd.to_datetime(out["timestamp"], utc=True).max(),
    )

    return {
        "ok": True,
        "rows": int(out.shape[0]),
        "start_ts": pd.to_datetime(out["timestamp"], utc=True).min().isoformat(),
        "end_ts": pd.to_datetime(out["timestamp"], utc=True).max().isoformat(),
        "out_path": str(op),
        "registry_path": str(rp),
        "registry_hash": card.hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
