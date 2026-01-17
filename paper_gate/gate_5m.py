from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class PaperGate5mResult:
    ok: bool
    verdict: str  # PAPER-GO / NO-GO
    checklist: dict[str, bool]
    metrics: dict
    reasons: list[str]


def _utc_now() -> pd.Timestamp:
    return pd.Timestamp(datetime.now(timezone.utc))


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise BinanceAITraderError(f"Failed to read json: {path}") from e


def _require_exists(path: Path, *, label: str, reasons: list[str]) -> bool:
    if path.exists():
        return True
    reasons.append(f"MISSING_{label}")
    return False


def _max_drawdown_from_equity(eq: np.ndarray) -> float:
    if eq.size == 0:
        return 0.0
    peak = np.maximum.accumulate(eq)
    dd = (peak - eq) / np.maximum(peak, 1e-12)
    return float(np.max(dd))


def paper_gate_5m(
    *,
    backtest_path: str | Path = Path("ai_data") / "backtests" / "backtest_5m.json",
    equity_path: str | Path = Path("ai_data") / "backtests" / "equity_5m.parquet",
    executions_path: str | Path = Path("ai_data") / "executions" / "executions_5m.parquet",
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
    funding_path: str | Path = Path("ai_data") / "derivatives" / "funding_rate_5m.parquet",
    oi_path: str | Path = Path("ai_data") / "derivatives" / "open_interest_5m.parquet",
    sentiment_path: str | Path = Path("ai_data") / "sentiment" / "aggregated" / "sentiment_5m.parquet",
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
    signals_path: str | Path = Path("ai_data") / "signals" / "signals_5m.parquet",
    targets_path: str | Path = Path("ai_data") / "targets" / "targets_5m.parquet",
    executions_artifact_path: str | Path = Path("ai_data") / "executions" / "executions_5m.parquet",
    verify_backtest_path: str | Path = Path("ai_data") / "backtests" / "backtest_5m.json",
    # Required paper safety configs (must exist)
    kill_switch_cfg: str | Path = Path("ai_data") / "paper" / "kill_switch.json",
    drift_cfg: str | Path = Path("ai_data") / "paper" / "drift_monitoring.json",
    latency_cfg: str | Path = Path("ai_data") / "paper" / "latency_budget.json",
) -> PaperGate5mResult:
    reasons: list[str] = []

    backtest_path = Path(backtest_path)
    equity_path = Path(equity_path)
    executions_path = Path(executions_path)
    price_path = Path(price_path)
    funding_path = Path(funding_path)
    oi_path = Path(oi_path)
    sentiment_path = Path(sentiment_path)
    features_path = Path(features_path)
    signals_path = Path(signals_path)
    targets_path = Path(targets_path)

    checklist: dict[str, bool] = {}

    # 0) Required artifacts exist
    checklist["backtest_json_exists"] = _require_exists(backtest_path, label="BACKTEST_JSON", reasons=reasons)
    checklist["equity_parquet_exists"] = _require_exists(equity_path, label="EQUITY_PARQUET", reasons=reasons)

    # Required pipeline artifacts (proxy for verify-green)
    checklist["datasets_exist"] = all(
        _require_exists(p, label=f"DATA_{p.name.upper().replace('.', '_')}", reasons=reasons)
        for p in [price_path, funding_path, oi_path, sentiment_path]
    )
    checklist["features_exist"] = _require_exists(features_path, label="FEATURES", reasons=reasons)
    checklist["targets_exist"] = _require_exists(targets_path, label="TARGETS", reasons=reasons)
    checklist["signals_exist"] = _require_exists(signals_path, label="SIGNALS", reasons=reasons)
    checklist["executions_exist"] = _require_exists(executions_path, label="EXECUTIONS", reasons=reasons)

    # Safety configs
    checklist["kill_switch_configured"] = _require_exists(Path(kill_switch_cfg), label="KILL_SWITCH_CFG", reasons=reasons)
    checklist["drift_monitoring_configured"] = _require_exists(Path(drift_cfg), label="DRIFT_CFG", reasons=reasons)
    checklist["latency_budget_configured"] = _require_exists(Path(latency_cfg), label="LATENCY_CFG", reasons=reasons)

    if not all(checklist.values()):
        return PaperGate5mResult(
            ok=False,
            verdict="NO-GO",
            checklist=checklist,
            metrics={},
            reasons=reasons,
        )

    bt = _read_json(backtest_path)
    windows = bt.get("windows")
    summary = bt.get("summary")
    if not isinstance(windows, list) or not isinstance(summary, dict):
        raise BinanceAITraderError("Invalid backtest_5m.json schema")

    eqdf = pd.read_parquet(equity_path)
    if "timestamp" not in eqdf.columns or "equity" not in eqdf.columns:
        raise BinanceAITraderError("equity_5m.parquet must contain timestamp and equity")

    eqdf2 = eqdf.copy()
    eqdf2["timestamp"] = pd.to_datetime(eqdf2["timestamp"], utc=True, errors="coerce")
    if eqdf2["timestamp"].isna().any():
        raise BinanceAITraderError("equity contains invalid timestamps")

    eqdf2 = eqdf2.sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last").reset_index(drop=True)
    eqv = pd.to_numeric(eqdf2["equity"], errors="coerce").to_numpy(dtype=np.float64)
    if not np.isfinite(eqv).all():
        raise BinanceAITraderError("equity contains non-finite values")

    execs = pd.read_parquet(executions_path)
    if execs.empty:
        reasons.append("NO_EXECUTIONS")
        return PaperGate5mResult(ok=False, verdict="NO-GO", checklist=checklist, metrics={}, reasons=reasons)

    for c in ["gross_pnl", "net_pnl", "fee", "slippage", "exit_ts"]:
        if c not in execs.columns:
            raise BinanceAITraderError(f"executions_5m missing required column: {c}")

    execs2 = execs.copy()
    execs2["exit_ts"] = pd.to_datetime(execs2["exit_ts"], utc=True, errors="coerce")
    if execs2["exit_ts"].isna().any():
        raise BinanceAITraderError("executions contain invalid exit_ts")

    # -------- Gate metrics --------
    pf = summary.get("profit_factor")
    max_dd = float(summary.get("max_dd")) if summary.get("max_dd") is not None else _max_drawdown_from_equity(eqv)
    trades_total = int(summary.get("total_trades", int(execs2.shape[0])))
    trades_per_day = float(summary.get("avg_trades_per_day", 0.0))

    winrate = float((execs2["net_pnl"].astype(float) > 0).mean())

    # Worst 7d window return based on equity at window boundaries
    eq_idx = pd.Index(eqdf2["timestamp"])
    eq_series = pd.Series(eqdf2["equity"].to_numpy(dtype=np.float64), index=eq_idx)

    window_returns: list[float] = []
    window_pf_flags: list[float | None] = []
    for w in windows:
        try:
            ts0 = pd.Timestamp(str(w["test_start"]))
            ts1 = pd.Timestamp(str(w["test_end"]))
        except Exception:
            continue

        # nearest forward fill: equity is piecewise constant
        e0 = float(eq_series.loc[eq_series.index[eq_series.index <= ts0].max()]) if (eq_series.index <= ts0).any() else float(eq_series.iloc[0])
        e1 = float(eq_series.loc[eq_series.index[eq_series.index < ts1].max()]) if (eq_series.index < ts1).any() else float(eq_series.iloc[-1])
        r = (e1 / e0) - 1.0 if e0 != 0 else 0.0
        window_returns.append(float(r))

        pfi = w.get("profit_factor")
        window_pf_flags.append(float(pfi) if pfi is not None else None)

    worst_window_return = float(min(window_returns)) if window_returns else 0.0

    # Stability checks
    pf_vals = [x for x in window_pf_flags if x is not None]
    pct_pf_ge_1_1 = float(sum(1 for x in pf_vals if x >= 1.1) / len(pf_vals)) if pf_vals else 0.0

    two_bad_in_row = False
    prev_bad = False
    for x in window_pf_flags:
        bad = (x is not None) and (x < 0.9)
        if prev_bad and bad:
            two_bad_in_row = True
            break
        prev_bad = bad

    # Simple V-shape heuristic: huge drawdown window followed by huge rebound window
    vshape = False
    if len(window_returns) >= 2:
        worst_i = int(np.argmin(np.array(window_returns)))
        if worst_i + 1 < len(window_returns):
            if window_returns[worst_i] <= -0.06 and window_returns[worst_i + 1] >= 0.06:
                vshape = True

    # Cost-pressure
    avg_gross = float(execs2["gross_pnl"].astype(float).mean())
    avg_cost = float((execs2["fee"].astype(float) + execs2["slippage"].astype(float)).mean())

    metrics = {
        "profit_factor": pf,
        "max_drawdown": float(max_dd),
        "trades_per_day": float(trades_per_day),
        "winrate": float(winrate),
        "worst_window_return": float(worst_window_return),
        "pct_windows_pf_ge_1_1": float(pct_pf_ge_1_1),
        "two_consecutive_pf_lt_0_9": bool(two_bad_in_row),
        "vshape_detected": bool(vshape),
        "avg_gross_pnl_per_trade": float(avg_gross),
        "avg_cost_per_trade": float(avg_cost),
        "total_trades": int(trades_total),
        "windows": int(len(windows)),
    }

    # -------- Quantitative criteria (hard) --------
    checklist["pf_ge_1_15"] = (pf is not None) and (float(pf) >= 1.15)
    checklist["max_dd_le_20pct"] = float(max_dd) <= 0.20
    checklist["trades_day_5_20"] = 5.0 <= float(trades_per_day) <= 20.0
    checklist["winrate_52_56"] = 0.52 <= float(winrate) <= 0.56
    checklist["worst_window_ge_-6pct"] = float(worst_window_return) >= -0.06

    if not checklist["pf_ge_1_15"]:
        reasons.append("PF_TOO_LOW")
    if not checklist["max_dd_le_20pct"]:
        reasons.append("DD_TOO_HIGH")
    if not checklist["trades_day_5_20"]:
        reasons.append("TRADES_PER_DAY_OUT_OF_RANGE")
    if not checklist["winrate_52_56"]:
        reasons.append("WINRATE_OUT_OF_RANGE")
    if not checklist["worst_window_ge_-6pct"]:
        reasons.append("WORST_WINDOW_TOO_BAD")

    # -------- Stability criteria --------
    checklist["stability_70pct_pf_ge_1_1"] = float(pct_pf_ge_1_1) >= 0.70
    checklist["no_two_bad_pf_windows"] = not bool(two_bad_in_row)
    checklist["no_vshape"] = not bool(vshape)

    if not checklist["stability_70pct_pf_ge_1_1"]:
        reasons.append("STABILITY_TOO_LOW")
    if not checklist["no_two_bad_pf_windows"]:
        reasons.append("TWO_BAD_WINDOWS_IN_ROW")
    if not checklist["no_vshape"]:
        reasons.append("VSHAPE_SUSPECT")

    # -------- Cost-pressure --------
    checklist["edge_gt_2x_cost"] = float(avg_gross) >= 2.0 * float(avg_cost)
    if not checklist["edge_gt_2x_cost"]:
        reasons.append("EDGE_NOT_ABOVE_COST")

    # -------- Data freshness --------
    now = _utc_now()

    def _latest_ts(path: Path, col: str = "timestamp") -> pd.Timestamp:
        df = pd.read_parquet(path)
        if col not in df.columns:
            raise BinanceAITraderError(f"{path} missing timestamp column")
        ts = pd.to_datetime(df[col], utc=True, errors="coerce")
        if ts.isna().any():
            raise BinanceAITraderError(f"{path} contains invalid timestamps")
        return ts.max()

    price_last = _latest_ts(price_path, col="timestamp")
    fund_last = _latest_ts(funding_path, col="timestamp")
    oi_last = _latest_ts(oi_path, col="timestamp")
    sent_last = _latest_ts(sentiment_path, col="timestamp")

    ohlcv_lag = now - price_last
    fund_lag = now - fund_last
    oi_lag = now - oi_last

    checklist["ohlcv_lag_le_1_candle"] = ohlcv_lag <= pd.Timedelta(minutes=5)
    checklist["funding_lag_le_2_candles"] = fund_lag <= pd.Timedelta(minutes=10)
    checklist["oi_lag_le_2_candles"] = oi_lag <= pd.Timedelta(minutes=10)

    # Sentiment must be lagged-only: enforce it's not ahead of price and at least 1 candle behind
    checklist["sentiment_not_realtime"] = sent_last <= (price_last - pd.Timedelta(minutes=5))

    if not checklist["ohlcv_lag_le_1_candle"]:
        reasons.append("OHLCV_STALE")
    if not checklist["funding_lag_le_2_candles"]:
        reasons.append("FUNDING_STALE")
    if not checklist["oi_lag_le_2_candles"]:
        reasons.append("OI_STALE")
    if not checklist["sentiment_not_realtime"]:
        reasons.append("SENTIMENT_REALTIME_FORBIDDEN")

    ok = all(bool(v) for v in checklist.values())

    return PaperGate5mResult(
        ok=ok,
        verdict="PAPER-GO" if ok else "NO-GO",
        checklist=checklist,
        metrics=metrics,
        reasons=reasons,
    )
