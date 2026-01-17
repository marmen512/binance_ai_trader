from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.merge import merge_datasets
from data_pipeline.normalization import normalize_columns
from data_pipeline.parquet_loader import load_parquets
from data_pipeline.validation import validate_ohlcv
from models.inference import load_model_from_artifact
from model_registry.registry import ModelCard
from trading.decision_engine import DecisionConfig, predictions_to_position


@dataclass(frozen=True)
class DecisionEngineResult:
    ok: bool
    rows: int
    model_id: str
    output_path: str
    report_path: str


def _load_model_card(model_id: str, *, cards_dir: str | Path) -> ModelCard:
    p = Path(cards_dir) / f"{model_id}.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    if "data_sha256" not in raw and "dataset_sha256" in raw:
        raw["data_sha256"] = raw["dataset_sha256"]

    allowed = set(getattr(ModelCard, "__annotations__", {}).keys())
    filtered = {k: v for k, v in raw.items() if k in allowed}
    return ModelCard(**filtered)


def run_decision_engine(
    paths: list[str | Path],
    *,
    model_id: str,
    output_path: str | Path,
    report_path: str | Path,
    cards_dir: str | Path = Path("model_registry") / "model_cards",
    cfg: DecisionConfig | None = None,
) -> DecisionEngineResult:
    cfg2 = cfg or DecisionConfig()

    dfs = load_parquets(paths)
    dfs = [normalize_columns(df) for df in dfs]
    merged = merge_datasets(dfs).df

    report = validate_ohlcv(merged)
    if not report.ok:
        return DecisionEngineResult(
            ok=False,
            rows=int(merged.shape[0]),
            model_id=model_id,
            output_path=str(output_path),
            report_path=str(report_path),
        )

    card = _load_model_card(model_id, cards_dir=cards_dir)
    model = load_model_from_artifact(card.artifact_path)

    df = merged.copy()

    missing = [c for c in model.feature_cols if c not in df.columns]
    if missing:
        return DecisionEngineResult(
            ok=False,
            rows=int(df.shape[0]),
            model_id=model_id,
            output_path=str(output_path),
            report_path=str(report_path),
        )

    x = df[model.feature_cols].to_numpy(dtype=np.float64)
    y_pred = model.predict(x)
    y_hat = pd.Series(y_pred, index=df.index, dtype="float64")

    pos = predictions_to_position(df, y_hat, cfg2)

    out = df.copy()
    out["y_hat"] = y_hat
    out["position_model"] = pos

    op = Path(output_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(op, index=False)

    rp = Path(report_path)
    rp.parent.mkdir(parents=True, exist_ok=True)

    rep = {
        "ok": True,
        "rows": int(out.shape[0]),
        "model_id": model_id,
        "mean_pred": float(np.mean(y_pred)) if y_pred.size else 0.0,
        "std_pred": float(np.std(y_pred)) if y_pred.size else 0.0,
        "nonzero_positions": int((pos.abs() > 0).sum()),
        "max_abs_position": float(pos.abs().max()) if not pos.empty else 0.0,
        "output_path": str(op),
    }
    rp.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return DecisionEngineResult(
        ok=True,
        rows=int(out.shape[0]),
        model_id=model_id,
        output_path=str(op),
        report_path=str(rp),
    )
