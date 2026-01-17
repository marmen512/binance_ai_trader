from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class VerifyBacktest5mResult:
    ok: bool
    windows: int
    total_trades: int


def verify_backtest_5m(
    *,
    backtest_path: str | Path = Path("ai_data") / "backtests" / "backtest_5m.json",
    equity_path: str | Path = Path("ai_data") / "backtests" / "equity_5m.parquet",
    executions_path: str | Path = Path("ai_data") / "executions" / "executions_5m.parquet",
    test_days: int = 7,
) -> VerifyBacktest5mResult:
    backtest_path = Path(backtest_path)
    equity_path = Path(equity_path)
    executions_path = Path(executions_path)

    if not backtest_path.exists():
        raise BinanceAITraderError(f"Missing backtest json: {backtest_path}")
    if not equity_path.exists():
        raise BinanceAITraderError(f"Missing equity parquet: {equity_path}")
    if not executions_path.exists():
        raise BinanceAITraderError(f"Missing executions parquet: {executions_path}")

    payload = json.loads(backtest_path.read_text(encoding="utf-8"))
    windows = payload.get("windows")
    summary = payload.get("summary")

    if not isinstance(windows, list) or not isinstance(summary, dict):
        raise BinanceAITraderError("Invalid backtest json schema")

    eq = pd.read_parquet(equity_path)
    if "timestamp" not in eq.columns or "equity" not in eq.columns:
        raise BinanceAITraderError("equity parquet must contain timestamp and equity")

    ts = pd.to_datetime(eq["timestamp"], utc=True, errors="coerce")
    if ts.isna().any():
        raise BinanceAITraderError("equity contains invalid timestamps")

    if not ts.is_monotonic_increasing:
        raise BinanceAITraderError("equity timestamps must be monotonic")

    ev = pd.to_numeric(eq["equity"], errors="coerce").to_numpy(dtype=np.float64)
    if not np.isfinite(ev).all():
        raise BinanceAITraderError("equity contains non-finite values")

    # max DD <= 100%
    peak = np.maximum.accumulate(ev)
    dd = (peak - ev) / np.maximum(peak, 1e-12)
    if float(np.max(dd)) > 1.0 + 1e-9:
        raise BinanceAITraderError("max drawdown must be <= 100%")

    execs = pd.read_parquet(executions_path)
    if execs.empty:
        return VerifyBacktest5mResult(ok=True, windows=len(windows), total_trades=0)

    if "entry_ts" not in execs.columns or "exit_ts" not in execs.columns:
        raise BinanceAITraderError("executions must contain entry_ts and exit_ts")

    execs2 = execs.copy()
    execs2["entry_ts"] = pd.to_datetime(execs2["entry_ts"], utc=True, errors="coerce")
    execs2["exit_ts"] = pd.to_datetime(execs2["exit_ts"], utc=True, errors="coerce")
    if execs2[["entry_ts", "exit_ts"]].isna().any().any():
        raise BinanceAITraderError("executions contain invalid timestamps")

    execs2 = execs2.sort_values("exit_ts").reset_index(drop=True)

    # executions sorted
    if not execs2["exit_ts"].is_monotonic_increasing:
        raise BinanceAITraderError("executions must be sorted by time")

    # each execution used once: verify uniqueness by (entry_ts, exit_ts, side)
    key_cols = ["entry_ts", "exit_ts"] + (["side"] if "side" in execs2.columns else [])
    if execs2.duplicated(subset=key_cols).any():
        raise BinanceAITraderError("Duplicate executions detected (violates one-pass rule)")

    total_trades = int(summary.get("total_trades", 0))
    if total_trades != int(execs2.shape[0]):
        raise BinanceAITraderError("summary.total_trades must equal executions rows")

    # trades/day sanity (based on total test days)
    td = float(len(windows) * int(test_days))
    tpd = float(total_trades / td) if td > 0 else 0.0
    if tpd < 1.0 or tpd > 50.0:
        raise BinanceAITraderError(f"trades/day out of range [1,50]: {tpd:.3f}")

    return VerifyBacktest5mResult(ok=True, windows=len(windows), total_trades=total_trades)
