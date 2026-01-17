from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core.exceptions import BinanceAITraderError
from data_pipeline.binance_client import BinanceFuturesClient
from data_pipeline.registry import write_registry_card
from data_pipeline.validators import validate_price_5m


def _to_ms(ts: pd.Timestamp) -> int:
    return int(ts.value // 1_000_000)


def download_binance_futures_price_5m(
    *,
    symbol: str = "BTCUSDT",
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    out_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
    registry_path: str | Path = Path("ai_data") / "dataset_registry" / "price_binance_5m.json",
    require_freshness: bool = False,
) -> dict:
    if start_ts.tzinfo is None:
        raise BinanceAITraderError("price_5m: start_ts must be tz-aware UTC")
    if end_ts.tzinfo is None:
        raise BinanceAITraderError("price_5m: end_ts must be tz-aware UTC")
    if end_ts <= start_ts:
        raise BinanceAITraderError("price_5m: end_ts must be > start_ts")

    op = Path(out_path)
    if op.exists():
        raise BinanceAITraderError(f"Refusing to overwrite price dataset: {op}")
    op.parent.mkdir(parents=True, exist_ok=True)

    client = BinanceFuturesClient()

    rows: list[list] = []
    cur = start_ts
    end_ms = _to_ms(end_ts)

    # Binance limit for klines is 1500.
    # We page forward using startTime.
    while True:
        payload = client.get_json(
            "/fapi/v1/klines",
            {
                "symbol": symbol,
                "interval": "5m",
                "startTime": _to_ms(cur),
                "endTime": end_ms,
                "limit": 1500,
            },
        )

        if not isinstance(payload, list) or not payload:
            break

        rows.extend(payload)
        last_open_ms = int(payload[-1][0])

        # Advance by 1 ms to avoid duplicates.
        cur = pd.to_datetime(last_open_ms + 1, unit="ms", utc=True)
        if cur.value // 1_000_000 >= end_ms:
            break

        # Safety guard.
        if len(payload) < 1500:
            break

    if not rows:
        raise BinanceAITraderError("price_5m: no rows downloaded")

    df = pd.DataFrame(
        rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "number_of_trades",
            "taker_buy_base_asset_volume",
            "taker_buy_quote_asset_volume",
            "ignore",
        ],
    )

    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")

    out = out.dropna().sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    # Validate strictly before persisting.
    validate_price_5m(out, coverage_min=0.99, require_freshness=bool(require_freshness))

    out.to_parquet(op, index=False)

    # Registry card.
    rp = Path(registry_path)
    card = write_registry_card(
        out_path=rp,
        name="binance_usdtm_futures_btcusdt_5m",
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
