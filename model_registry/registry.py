from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class ModelCard:
    model_id: str
    created_at: str
    algo: str
    data_paths: list[str]
    data_sha256: str
    rows_train: int
    rows_val: int
    rows_test: int
    target_col: str
    feature_cols: list[str]
    metrics: dict[str, float]
    artifact_path: str


def _hash_files(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x)):
        h.update(str(p).encode("utf-8"))
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def write_model_card(
    registry_dir: str | Path,
    *,
    algo: str,
    data_paths: list[str | Path],
    rows_train: int,
    rows_val: int,
    rows_test: int,
    target_col: str,
    feature_cols: list[str],
    metrics: dict[str, float],
    artifact_path: str | Path,
) -> ModelCard:
    reg = Path(registry_dir)
    reg.mkdir(parents=True, exist_ok=True)

    path_objs = [Path(p) for p in data_paths]
    for p in path_objs:
        if not p.exists():
            raise FileNotFoundError(f"Dataset path not found: {p}")

    sha256 = _hash_files(path_objs)
    created_at = datetime.now(timezone.utc).isoformat()
    model_id = f"m_{sha256[:12]}"

    card = ModelCard(
        model_id=model_id,
        created_at=created_at,
        algo=algo,
        data_paths=[str(p) for p in path_objs],
        data_sha256=sha256,
        rows_train=int(rows_train),
        rows_val=int(rows_val),
        rows_test=int(rows_test),
        target_col=target_col,
        feature_cols=list(feature_cols),
        metrics={k: float(v) for k, v in metrics.items()},
        artifact_path=str(artifact_path),
    )

    out_path = reg / f"{model_id}.json"
    payload = dict(card.__dict__)
    payload["dataset_sha256"] = payload.get("data_sha256")
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return card
