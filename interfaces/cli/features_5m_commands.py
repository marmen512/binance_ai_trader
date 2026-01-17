from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from core.config import load_config
from core.logging import setup_logger
from features.pipeline_5m import build_features_5m
from features.validators import verify_features_5m


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


def build_features_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = build_features_5m()
    logger.info("build-features-5m: OK rows_out=%s", res.rows_out)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def verify_features_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = verify_features_5m()
    logger.info("verify-features-5m: OK rows=%s", res.rows)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def feature_status_5m_command(config_path: str | Path) -> "CommandResult":
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    fp = Path("ai_data") / "features" / "features_5m.parquet"
    meta: dict | None = None
    if fp.exists():
        df = pd.read_parquet(fp)
        ts = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        start_ts = ts.min().isoformat() if not ts.isna().all() else None
        end_ts = ts.max().isoformat() if not ts.isna().all() else None
        meta = {
            "sha256": _sha256_file(fp),
            "hash": f"sha256:{_sha256_file(fp)}",
            "rows": int(df.shape[0]),
            "columns": list(df.columns),
            "date_range": f"{start_ts} -> {end_ts}",
            "frequency": "5m",
        }

    payload = {
        "path": str(fp),
        "exists": bool(fp.exists()),
        "meta": meta,
    }

    logger.info("feature-status-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(payload, ensure_ascii=False, indent=2))
