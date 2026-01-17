from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from core.config import load_config
from core.exceptions import BinanceAITraderError
from core.logging import setup_logger
from data_pipeline.validators import (
    validate_funding_rate_5m,
    validate_open_interest_5m,
    validate_price_5m,
    validate_sentiment_agg_5m,
)
from execution.builder_5m import build_executions_5m
from execution.validators import verify_executions_5m
from features.validators import verify_features_5m
from signals.validators import verify_signals_5m
from targets.validators import verify_targets_5m


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    output: str


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def build_executions_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    _gate_verify_datasets_5m()
    verify_features_5m()
    verify_targets_5m()
    verify_signals_5m()

    res = build_executions_5m()
    logger.info("build-executions-5m: OK trades_out=%s", res.trades_out)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def verify_executions_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = verify_executions_5m()
    logger.info("verify-executions-5m: OK trades=%s", res.trades)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def execution_status_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    ep = Path("ai_data") / "executions" / "executions_5m.parquet"
    meta: dict | None = None
    if ep.exists():
        df = pd.read_parquet(ep)
        entry_ts = pd.to_datetime(df["entry_ts"], utc=True, errors="coerce") if "entry_ts" in df.columns else None
        start_ts = entry_ts.min().isoformat() if entry_ts is not None and not entry_ts.isna().all() else None
        end_ts = entry_ts.max().isoformat() if entry_ts is not None and not entry_ts.isna().all() else None
        meta = {
            "sha256": _sha256_file(ep),
            "hash": f"sha256:{_sha256_file(ep)}",
            "trades": int(df.shape[0]),
            "columns": list(df.columns),
            "date_range": f"{start_ts} -> {end_ts}",
            "frequency": "5m",
        }

    payload = {
        "path": str(ep),
        "exists": bool(ep.exists()),
        "meta": meta,
    }

    logger.info("execution-status-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(payload, ensure_ascii=False, indent=2))
