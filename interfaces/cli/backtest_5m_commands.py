from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from core.config import load_config
from core.exceptions import BinanceAITraderError
from core.logging import setup_logger
from backtest.runner_5m import run_backtest_5m
from backtest.validators_5m import verify_backtest_5m
from data_pipeline.validators import (
    validate_funding_rate_5m,
    validate_open_interest_5m,
    validate_price_5m,
    validate_sentiment_agg_5m,
)
from features.validators import verify_features_5m
from signals.validators import verify_signals_5m
from targets.validators import verify_targets_5m


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    output: str


def _gate_verify_datasets_5m() -> None:
    price_p = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet"
    fund_p = Path("ai_data") / "derivatives" / "funding_rate_5m.parquet"
    oi_p = Path("ai_data") / "derivatives" / "open_interest_5m.parquet"
    sent_p = Path("ai_data") / "sentiment" / "aggregated" / "sentiment_5m.parquet"

    price_card = Path("ai_data") / "dataset_registry" / "price_binance_5m.json"
    fund_card = Path("ai_data") / "dataset_registry" / "funding_rate_5m.json"
    oi_card = Path("ai_data") / "dataset_registry" / "open_interest_5m.json"
    sent_card = Path("ai_data") / "dataset_registry" / "sentiment_5m.json"

    missing: list[str] = []
    for p in [price_p, fund_p, oi_p, sent_p, price_card, fund_card, oi_card, sent_card]:
        if not p.exists():
            missing.append(str(p))
    if missing:
        raise BinanceAITraderError(f"Missing mandatory 5m datasets/cards: {missing}")

    price_df = pd.read_parquet(price_p)
    fund_df = pd.read_parquet(fund_p)
    oi_df = pd.read_parquet(oi_p)
    sent_df = pd.read_parquet(sent_p)

    validate_price_5m(price_df, coverage_min=0.99)
    validate_funding_rate_5m(fund_df, nan_max_ratio=0.01)
    validate_open_interest_5m(oi_df, nan_max_ratio=0.01)
    validate_sentiment_agg_5m(sent_df, nan_max_ratio=0.01)


def _gate_verify_executions_5m() -> None:
    ep = Path("ai_data") / "executions" / "executions_5m.parquet"
    if not ep.exists():
        raise BinanceAITraderError(f"Missing executions_5m parquet: {ep}")

    df = pd.read_parquet(ep)
    if df.empty:
        raise BinanceAITraderError("executions_5m is empty")

    for c in ["entry_ts", "exit_ts", "net_pnl", "gross_pnl", "fee", "slippage", "holding_candles"]:
        if c not in df.columns:
            raise BinanceAITraderError(f"executions_5m missing required column: {c}")

    entry_ts = pd.to_datetime(df["entry_ts"], utc=True, errors="coerce")
    exit_ts = pd.to_datetime(df["exit_ts"], utc=True, errors="coerce")
    if entry_ts.isna().any() or exit_ts.isna().any():
        raise BinanceAITraderError("executions contain invalid timestamps")

    if (exit_ts <= entry_ts).any():
        raise BinanceAITraderError("executions must satisfy exit_ts > entry_ts")

    if not df["holding_candles"].astype(int).between(1, 6).all():
        raise BinanceAITraderError("executions must satisfy holding_candles <= 6")

    calc = df["gross_pnl"].astype(float) - df["fee"].astype(float) - df["slippage"].astype(float)
    if (calc - df["net_pnl"].astype(float)).abs().max() > 1e-9:
        raise BinanceAITraderError("executions must satisfy net_pnl=gross-fee-slippage")

    df2 = pd.DataFrame({"entry_ts": entry_ts, "exit_ts": exit_ts}).sort_values("entry_ts").reset_index(drop=True)
    prev_exit = None
    for i in range(df2.shape[0]):
        et = df2.loc[i, "entry_ts"]
        xt = df2.loc[i, "exit_ts"]
        if prev_exit is not None and et <= prev_exit:
            raise BinanceAITraderError("overlapping executions detected")
        prev_exit = xt


def run_backtest_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    _gate_verify_datasets_5m()
    verify_features_5m()
    verify_targets_5m()
    verify_signals_5m()
    _gate_verify_executions_5m()

    res = run_backtest_5m()
    logger.info("run-backtest-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def backtest_status_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    bt = Path("ai_data") / "backtests" / "backtest_5m.json"
    eq = Path("ai_data") / "backtests" / "equity_5m.parquet"

    payload: dict = {
        "backtest_path": str(bt),
        "equity_path": str(eq),
        "backtest_exists": bool(bt.exists()),
        "equity_exists": bool(eq.exists()),
    }

    if bt.exists():
        try:
            payload["backtest"] = json.loads(bt.read_text(encoding="utf-8"))
        except Exception:
            payload["backtest"] = None

    logger.info("backtest-status-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(payload, ensure_ascii=False, indent=2))


def verify_backtest_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = verify_backtest_5m()
    logger.info("verify-backtest-5m: OK windows=%s", res.windows)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))
