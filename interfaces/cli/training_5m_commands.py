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
from features.validators import verify_features_5m
from targets.validators import verify_targets_5m
from training.xgb_5m import train_xgb_5m


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


def train_xgb_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    _gate_verify_datasets_5m()
    verify_features_5m()
    verify_targets_5m()

    res = train_xgb_5m()
    logger.info("train-xgb-5m: OK best_iteration=%s val_mlogloss=%s", res.best_iteration, res.val_mlogloss)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def training_status_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    model_dir = Path("ai_data") / "models" / "xgb_5m"
    payload: dict = {
        "model_dir": str(model_dir),
        "exists": bool(model_dir.exists()),
        "model_json": str(model_dir / "model.json"),
        "training_meta": str(model_dir / "training_meta.json"),
        "feature_schema": str(model_dir / "feature_schema.json"),
    }

    meta_p = model_dir / "training_meta.json"
    if meta_p.exists():
        try:
            payload["meta"] = json.loads(meta_p.read_text(encoding="utf-8"))
        except Exception:
            payload["meta"] = None

    logger.info("training-status-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(payload, ensure_ascii=False, indent=2))
