from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


logger = logging.getLogger(__name__)


BINANCE_SPOT_REST = "https://api.binance.com"


@dataclass(frozen=True)
class KlinesFetchResult:
    ok: bool
    df: pd.DataFrame
    symbol: str
    interval: str
    raw_rows: int
    error: str | None


def _utc_now_ms() -> int:
    return int(time.time() * 1000)


def _ms_to_utc_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)


def fetch_binance_klines(
    *,
    symbol: str,
    interval: str = "1h",
    limit: int = 500,
    start_time_ms: int | None = None,
    end_time_ms: int | None = None,
    base_url: str = BINANCE_SPOT_REST,
    timeout_s: float = 10.0,
) -> KlinesFetchResult:
    """Fetch klines from Binance Spot REST.

    Notes:
    - Returns a DataFrame sorted by close_time, deduplicated.
    - Timestamps are UTC.
    - This function does NOT perform 1H close gating; it only fetches.
    """

    q: dict[str, Any] = {"symbol": str(symbol).upper(), "interval": str(interval), "limit": int(limit)}
    if start_time_ms is not None:
        q["startTime"] = int(start_time_ms)
    if end_time_ms is not None:
        q["endTime"] = int(end_time_ms)

    url = f"{base_url}/api/v3/klines?{urlencode(q)}"

    payload: Any | None = None
    last_err: str | None = None
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            req = Request(url=url, headers={"Accept": "application/json"}, method="GET")
            with urlopen(req, timeout=float(timeout_s)) as resp:
                raw = resp.read().decode("utf-8")
            payload = json.loads(raw)
            last_err = None
            break
        except HTTPError as e:
            try:
                body = e.read().decode("utf-8")
            except Exception:
                body = ""
            last_err = f"HTTPError status={getattr(e, 'code', None)} reason={getattr(e, 'reason', None)} body={body[:300]}"
            logger.warning("Binance klines fetch failed attempt=%s/%s url=%s err=%s", attempt, max_attempts, url, last_err)
        except URLError as e:
            last_err = f"URLError reason={getattr(e, 'reason', None)}"
            logger.warning("Binance klines fetch failed attempt=%s/%s url=%s err=%s", attempt, max_attempts, url, last_err)
        except Exception as e:
            last_err = str(e)
            logger.warning("Binance klines fetch failed attempt=%s/%s url=%s err=%s", attempt, max_attempts, url, last_err)

        if attempt < max_attempts:
            backoff_s = min(8.0, 0.5 * (2 ** (attempt - 1)))
            time.sleep(float(backoff_s))

    if payload is None:
        return KlinesFetchResult(
            ok=False,
            df=pd.DataFrame(),
            symbol=str(symbol),
            interval=str(interval),
            raw_rows=0,
            error=str(last_err or "FETCH_FAILED"),
        )

    if not isinstance(payload, list):
        return KlinesFetchResult(
            ok=False,
            df=pd.DataFrame(),
            symbol=str(symbol),
            interval=str(interval),
            raw_rows=0,
            error=f"Unexpected payload type: {type(payload)}",
        )

    rows = payload
    cols = [
        "open_time_ms",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time_ms",
        "quote_asset_volume",
        "trades",
        "taker_buy_base_vol",
        "taker_buy_quote_vol",
        "ignore",
    ]

    df = pd.DataFrame(rows, columns=cols)
    if df.empty:
        return KlinesFetchResult(
            ok=True,
            df=df,
            symbol=str(symbol),
            interval=str(interval),
            raw_rows=0,
            error=None,
        )

    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["open_time_ms"] = pd.to_numeric(df["open_time_ms"], errors="coerce").astype("Int64")
    df["close_time_ms"] = pd.to_numeric(df["close_time_ms"], errors="coerce").astype("Int64")

    df = df.dropna(subset=["close_time_ms", "close"]).copy()

    # Canonical schema used across the project.
    df["timestamp"] = df["open_time_ms"].astype("int64").map(lambda v: _ms_to_utc_dt(int(v)))
    df["close_time"] = df["close_time_ms"].astype("int64").map(lambda v: _ms_to_utc_dt(int(v)))

    df = df[["timestamp", "open", "high", "low", "close", "volume", "close_time", "open_time_ms", "close_time_ms"]]
    df = df.sort_values("close_time_ms").drop_duplicates(subset=["close_time_ms"], keep="last").reset_index(drop=True)

    return KlinesFetchResult(
        ok=True,
        df=df,
        symbol=str(symbol).upper(),
        interval=str(interval),
        raw_rows=int(len(rows)),
        error=None,
    )


def latest_closed_1h_klines(
    *,
    symbol: str,
    limit: int = 300,
    now_ms: int | None = None,
) -> KlinesFetchResult:
    """Convenience helper for 1H: fetch and drop the currently-forming candle.

    Binance typically includes the current (not-yet-closed) kline as the last row.
    We filter rows where close_time_ms <= now_ms.
    """

    n = int(now_ms) if now_ms is not None else _utc_now_ms()
    res = fetch_binance_klines(symbol=symbol, interval="1h", limit=int(limit))
    if not res.ok or res.df.empty:
        return res

    df = res.df.copy()
    df = df[pd.to_numeric(df["close_time_ms"], errors="coerce") <= int(n)].copy()
    df = df.reset_index(drop=True)

    return KlinesFetchResult(
        ok=True,
        df=df,
        symbol=res.symbol,
        interval=res.interval,
        raw_rows=res.raw_rows,
        error=None,
    )


def read_live_cursor(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_live_cursor(path: Path, *, last_processed_close_time_ms: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_processed_close_time_ms": int(last_processed_close_time_ms),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_live_cursor_v2(
    path: Path,
    *,
    last_processed_close_time_ms: int,
    last_trade_close_time_ms: int | None = None,
) -> None:
    """Backward-compatible cursor writer.

    live_cursor.json is a snapshot, not an append-only log.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_processed_close_time_ms": int(last_processed_close_time_ms),
        "last_trade_close_time_ms": int(last_trade_close_time_ms) if last_trade_close_time_ms is not None else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def last_processed_close_time_ms_from_cursor(cursor: dict | None) -> int | None:
    if not cursor:
        return None
    v = cursor.get("last_processed_close_time_ms")
    try:
        return int(v)
    except Exception:
        return None


def last_trade_close_time_ms_from_cursor(cursor: dict | None) -> int | None:
    if not cursor:
        return None
    v = cursor.get("last_trade_close_time_ms")
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def gate_new_closed_candles(
    *,
    df: pd.DataFrame,
    last_processed_close_time_ms: int | None,
    now_ms: int | None = None,
) -> tuple[pd.DataFrame, int | None]:
    """Return only candles that are closed and newer than the cursor.

    - If last_processed_close_time_ms is None: returns all closed candles.
    - Closed is defined as close_time_ms <= now_ms (if provided).
    - new_cursor is max(close_time_ms) of returned df, else unchanged.
    """

    if df.empty:
        return df.copy(), last_processed_close_time_ms

    out = df.copy()
    if "close_time_ms" not in out.columns:
        return out.iloc[0:0].copy(), last_processed_close_time_ms

    out["close_time_ms"] = pd.to_numeric(out["close_time_ms"], errors="coerce")
    out = out.dropna(subset=["close_time_ms"]).copy()

    if now_ms is not None:
        out = out[out["close_time_ms"] <= int(now_ms)].copy()

    if last_processed_close_time_ms is not None:
        out = out[out["close_time_ms"] > int(last_processed_close_time_ms)].copy()

    out = out.sort_values("close_time_ms").drop_duplicates(subset=["close_time_ms"], keep="last").reset_index(drop=True)

    if out.empty:
        return out, last_processed_close_time_ms

    new_cursor = int(pd.to_numeric(out["close_time_ms"], errors="coerce").max())
    return out, new_cursor
