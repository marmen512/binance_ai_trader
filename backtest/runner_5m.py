from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class RunBacktest5mResult:
    ok: bool
    windows: list[dict]
    summary: dict
    backtest_path: str
    equity_path: str


def _max_drawdown(equity: np.ndarray) -> float:
    if equity.size == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity) / np.maximum(peak, 1e-12)
    return float(np.max(dd))


_INITIAL_EQUITY_USD = 1_000_000.0


def run_backtest_5m(
    *,
    executions_path: str | Path = Path("ai_data") / "executions" / "executions_5m.parquet",
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
    out_dir: str | Path = Path("ai_data") / "backtests",
    train_days: int = 14,
    test_days: int = 7,
    step_days: int = 7,
) -> RunBacktest5mResult:
    if int(train_days) != 14 or int(test_days) != 7 or int(step_days) != 7:
        raise BinanceAITraderError("Backtest contract requires train=14d, test=7d, step=7d")

    executions_path = Path(executions_path)
    price_path = Path(price_path)
    out_dir = Path(out_dir)

    if not executions_path.exists():
        raise BinanceAITraderError(f"Missing executions_5m parquet: {executions_path}")
    if not price_path.exists():
        raise BinanceAITraderError(f"Missing price_5m parquet: {price_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    backtest_path = out_dir / "backtest_5m.json"
    equity_path = out_dir / "equity_5m.parquet"

    if backtest_path.exists() or equity_path.exists():
        raise BinanceAITraderError(f"Refusing to overwrite existing backtest outputs in: {out_dir}")

    execs = pd.read_parquet(executions_path)
    price = pd.read_parquet(price_path)

    if "timestamp" not in price.columns:
        raise BinanceAITraderError("price_5m parquet missing required column: timestamp")

    if execs.empty:
        ts = pd.to_datetime(price["timestamp"], utc=True, errors="coerce")
        if ts.isna().any():
            raise BinanceAITraderError("price_5m contains invalid timestamps")
        ts = ts.sort_values().drop_duplicates().reset_index(drop=True)

        eq = pd.DataFrame({"timestamp": ts, "equity": np.full((ts.shape[0],), _INITIAL_EQUITY_USD, dtype=np.float64)})
        eq.to_parquet(equity_path, index=False)
        payload = {"windows": [], "summary": {"total_trades": 0, "net_pnl": 0.0, "profit_factor": None, "max_dd": 0.0}}
        backtest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return RunBacktest5mResult(
            ok=True,
            windows=[],
            summary=payload["summary"],
            backtest_path=str(backtest_path),
            equity_path=str(equity_path),
        )

    required = {"entry_ts", "exit_ts", "net_pnl", "gross_pnl"}
    missing = sorted(required - set(execs.columns))
    if missing:
        raise BinanceAITraderError(f"executions missing required columns: {missing}")

    execs2 = execs.copy()
    execs2["entry_ts"] = pd.to_datetime(execs2["entry_ts"], utc=True, errors="coerce")
    execs2["exit_ts"] = pd.to_datetime(execs2["exit_ts"], utc=True, errors="coerce")
    if execs2[["entry_ts", "exit_ts"]].isna().any().any():
        raise BinanceAITraderError("executions contain invalid timestamps")

    execs2 = execs2.sort_values("exit_ts").reset_index(drop=True)

    if not execs2["exit_ts"].is_monotonic_increasing:
        raise BinanceAITraderError("executions must be sorted by time")

    # Price timestamps define the equity time index
    pts = pd.to_datetime(price["timestamp"], utc=True, errors="coerce")
    if pts.isna().any():
        raise BinanceAITraderError("price_5m contains invalid timestamps")
    pts = pts.sort_values().drop_duplicates().reset_index(drop=True)

    start_ts = pts.min()
    end_ts = pts.max()

    train_delta = pd.Timedelta(days=int(train_days))
    test_delta = pd.Timedelta(days=int(test_days))
    step_delta = pd.Timedelta(days=int(step_days))

    first_test_start = start_ts + train_delta

    if first_test_start >= end_ts:
        raise BinanceAITraderError(
            "Not enough price history to run backtest with contract train=30d, test=7d, step=7d: "
            f"price_range={start_ts.isoformat()} -> {end_ts.isoformat()}"
        )

    windows: list[dict] = []
    used_ids: set[tuple] = set()

    equity = np.full((pts.shape[0],), _INITIAL_EQUITY_USD, dtype=np.float64)
    eq_idx_by_ts = {t: i for i, t in enumerate(pts.tolist())}

    current_equity = float(_INITIAL_EQUITY_USD)

    test_start = first_test_start
    while test_start < end_ts:
        test_end = test_start + test_delta

        mask = (execs2["exit_ts"] >= test_start) & (execs2["exit_ts"] < test_end)
        w = execs2.loc[mask].copy()

        # One-pass rule: every execution used at most once
        for _, r in w.iterrows():
            eid = (pd.Timestamp(r["entry_ts"]).to_pydatetime(), pd.Timestamp(r["exit_ts"]).to_pydatetime(), str(r.get("side", "")))
            if eid in used_ids:
                raise BinanceAITraderError("Execution used more than once across windows")
            used_ids.add(eid)

        trades = int(w.shape[0])
        if trades:
            wins = int((w["net_pnl"].astype(float) > 0).sum())
            winrate = float(wins / trades)
            gross_pnl = float(w["gross_pnl"].astype(float).sum())
            net_pnl = float(w["net_pnl"].astype(float).sum())

            profits = w.loc[w["net_pnl"].astype(float) > 0, "net_pnl"].astype(float).sum()
            losses = w.loc[w["net_pnl"].astype(float) < 0, "net_pnl"].astype(float).sum()
            profit_factor = float(profits / abs(losses)) if float(losses) != 0.0 else None

            # Equity updates only at exits
            for _, r in w.iterrows():
                exit_ts = pd.Timestamp(r["exit_ts"])
                if exit_ts not in eq_idx_by_ts:
                    continue
                current_equity = float(current_equity + float(r["net_pnl"]))
                equity[eq_idx_by_ts[exit_ts] :] = current_equity
        else:
            winrate = None
            gross_pnl = 0.0
            net_pnl = 0.0
            profit_factor = None

        # Window drawdown computed on equity segment
        seg_mask = (pts >= test_start) & (pts < test_end)
        seg = equity[seg_mask.to_numpy()]
        max_dd = _max_drawdown(seg)

        windows.append(
            {
                "train_start": (test_start - train_delta).isoformat(),
                "train_end": test_start.isoformat(),
                "test_start": test_start.isoformat(),
                "test_end": test_end.isoformat(),
                "trades": trades,
                "winrate": winrate,
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "profit_factor": profit_factor,
                "max_dd": float(max_dd),
            }
        )

        test_start = test_start + step_delta

    if len(used_ids) != int(execs2.shape[0]):
        unused = int(execs2.shape[0]) - int(len(used_ids))
        raise BinanceAITraderError(
            f"One-pass violation: {unused} executions were not assigned to any test window. "
            "This usually means executions exist before the first test window start."
        )

    eq_df = pd.DataFrame({"timestamp": pts, "equity": equity.astype(np.float64)})
    eq_df.to_parquet(equity_path, index=False)

    total_trades = int(execs2.shape[0])
    total_net = float(execs2["net_pnl"].astype(float).sum())
    profits_total = execs2.loc[execs2["net_pnl"].astype(float) > 0, "net_pnl"].astype(float).sum()
    losses_total = execs2.loc[execs2["net_pnl"].astype(float) < 0, "net_pnl"].astype(float).sum()
    pf_total = float(profits_total / abs(losses_total)) if float(losses_total) != 0.0 else None

    max_dd_total = _max_drawdown(equity)

    worst_window = None
    if windows:
        worst_window = min(windows, key=lambda x: float(x.get("net_pnl", 0.0)))

    # trades/day sanity uses test horizon length
    total_test_days = float(len(windows) * test_days)
    avg_trades_day = float(total_trades / total_test_days) if total_test_days > 0 else 0.0

    summary = {
        "total_trades": total_trades,
        "avg_trades_per_day": avg_trades_day,
        "net_pnl": total_net,
        "profit_factor": pf_total,
        "max_dd": float(max_dd_total),
        "worst_window": worst_window,
    }

    payload = {"windows": windows, "summary": summary}
    backtest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return RunBacktest5mResult(
        ok=True,
        windows=windows,
        summary=summary,
        backtest_path=str(backtest_path),
        equity_path=str(equity_path),
    )
