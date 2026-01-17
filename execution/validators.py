from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class VerifyExecutions5mResult:
    ok: bool
    trades: int


def verify_executions_5m(
    *,
    executions_path: str | Path = Path("ai_data") / "executions" / "executions_5m.parquet",
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
) -> VerifyExecutions5mResult:
    executions_path = Path(executions_path)
    price_path = Path(price_path)

    if not executions_path.exists():
        raise BinanceAITraderError(f"Missing executions_5m parquet: {executions_path}")
    if not price_path.exists():
        raise BinanceAITraderError(f"Missing price_5m parquet: {price_path}")

    df = pd.read_parquet(executions_path)
    price = pd.read_parquet(price_path)

    required = {
        "entry_ts",
        "exit_ts",
        "side",
        "entry_price",
        "exit_price",
        "exit_reason",
        "gross_pnl",
        "net_pnl",
        "fee",
        "slippage",
        "holding_candles",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise BinanceAITraderError(f"executions missing required columns: {missing}")

    if df.empty:
        return VerifyExecutions5mResult(ok=True, trades=0)

    df2 = df.copy()
    df2["entry_ts"] = pd.to_datetime(df2["entry_ts"], utc=True, errors="coerce")
    df2["exit_ts"] = pd.to_datetime(df2["exit_ts"], utc=True, errors="coerce")

    if df2[["entry_ts", "exit_ts"]].isna().any().any():
        raise BinanceAITraderError("executions contain invalid timestamps")

    if (df2["exit_ts"] <= df2["entry_ts"]).any():
        raise BinanceAITraderError("exit_ts must be > entry_ts")

    if df2[["entry_price", "exit_price", "gross_pnl", "net_pnl", "fee", "slippage"]].isna().any().any():
        raise BinanceAITraderError("executions contain NaNs")

    arr = df2[["entry_price", "exit_price", "gross_pnl", "net_pnl", "fee", "slippage"]].to_numpy(dtype=float)
    if not np.isfinite(arr).all():
        raise BinanceAITraderError("executions contain non-finite values")

    if not df2["holding_candles"].astype(int).between(1, 6).all():
        raise BinanceAITraderError("holding_candles must be within [1,6]")

    if not df2["side"].astype(str).isin(["LONG", "SHORT"]).all():
        raise BinanceAITraderError("side must be LONG or SHORT")

    if not df2["exit_reason"].astype(str).isin(["TP", "SL", "TIME"]).all():
        raise BinanceAITraderError("exit_reason must be one of TP/SL/TIME")

    # net_pnl identity
    calc = df2["gross_pnl"].astype(float) - df2["fee"].astype(float) - df2["slippage"].astype(float)
    if np.max(np.abs(calc.to_numpy() - df2["net_pnl"].astype(float).to_numpy())) > 1e-9:
        raise BinanceAITraderError("net_pnl must equal gross_pnl - fee - slippage")

    # Alignment with price timestamps
    if "timestamp" not in price.columns:
        raise BinanceAITraderError("price_5m missing timestamp")

    p_ts = pd.to_datetime(price["timestamp"], utc=True, errors="coerce")
    if p_ts.isna().any():
        raise BinanceAITraderError("price_5m contains invalid timestamps")

    pset = set(p_ts.tolist())
    if not df2["entry_ts"].isin(pset).all() or not df2["exit_ts"].isin(pset).all():
        raise BinanceAITraderError("entry_ts/exit_ts must be present in price_5m timestamps")

    # No overlapping positions (sequential trades)
    df2 = df2.sort_values("entry_ts").reset_index(drop=True)
    prev_exit = None
    for i in range(df2.shape[0]):
        et = df2.loc[i, "entry_ts"]
        xt = df2.loc[i, "exit_ts"]
        if prev_exit is not None and et <= prev_exit:
            raise BinanceAITraderError("Detected overlapping trades (more than 1 open position)")
        prev_exit = xt

    return VerifyExecutions5mResult(ok=True, trades=int(df2.shape[0]))
