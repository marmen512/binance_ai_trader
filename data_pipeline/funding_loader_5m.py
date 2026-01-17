from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.binance_client import BinanceFuturesClient
from data_pipeline.registry import write_registry_card
from data_pipeline.validators import validate_funding_rate_5m


def _to_ms(ts: pd.Timestamp) -> int:
    return int(ts.value // 1_000_000)


def download_funding_rate_5m(
    *,
    symbol: str = "BTCUSDT",
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    out_path: str | Path = Path("ai_data") / "derivatives" / "funding_rate_5m.parquet",
    registry_path: str | Path = Path("ai_data") / "dataset_registry" / "funding_rate_5m.json",
    require_freshness: bool = False,
) -> dict:
    if start_ts.tzinfo is None or end_ts.tzinfo is None:
        raise BinanceAITraderError("funding_rate_5m: timestamps must be tz-aware UTC")
    if end_ts <= start_ts:
        raise BinanceAITraderError("funding_rate_5m: end_ts must be > start_ts")

    op = Path(out_path)
    if op.exists():
        raise BinanceAITraderError(f"Refusing to overwrite funding dataset: {op}")
    op.parent.mkdir(parents=True, exist_ok=True)

    client = BinanceFuturesClient()

    rows: list[dict] = []
    cur = start_ts
    end_ms = _to_ms(end_ts)

    # Funding endpoint returns 8h events; limit max is 1000.
    while True:
        payload = client.get_json(
            "/fapi/v1/fundingRate",
            {
                "symbol": symbol,
                "startTime": _to_ms(cur),
                "endTime": end_ms,
                "limit": 1000,
            },
        )
        if not isinstance(payload, list) or not payload:
            break

        rows.extend(payload)
        last_ms = int(payload[-1]["fundingTime"])
        cur = pd.to_datetime(last_ms + 1, unit="ms", utc=True)
        if cur.value // 1_000_000 >= end_ms:
            break
        if len(payload) < 1000:
            break

    if not rows:
        raise BinanceAITraderError("funding_rate_5m: no rows downloaded")

    raw = pd.DataFrame(rows)
    raw["timestamp"] = pd.to_datetime(pd.to_numeric(raw["fundingTime"], errors="coerce"), unit="ms", utc=True)
    raw["funding_rate"] = pd.to_numeric(raw["fundingRate"], errors="coerce")
    raw = raw.dropna(subset=["timestamp"]).sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    # Build 5m grid and forward-fill funding rate.
    grid = pd.DataFrame({"timestamp": pd.date_range(start=start_ts, end=end_ts, freq="5min", tz="UTC")})
    merged = pd.merge_asof(grid, raw[["timestamp", "funding_rate"]], on="timestamp", direction="backward")

    # If funding is missing anywhere, we keep NaNs; execution layer must treat missing as NO TRADE.
    out = merged[["timestamp", "funding_rate"]].copy()

    validate_funding_rate_5m(out, nan_max_ratio=0.01, require_freshness=bool(require_freshness))

    out.to_parquet(op, index=False)

    rp = Path(registry_path)
    card = write_registry_card(
        out_path=rp,
        name="binance_usdtm_futures_funding_rate_5m",
        source="binance",
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
