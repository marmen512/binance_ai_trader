from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class LoadedModel:
    feature_cols: list[str]
    target_col: str
    coef: np.ndarray
    intercept: float
    mean: np.ndarray
    scale: np.ndarray

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = (x - self.mean) / self.scale
        return x @ self.coef + self.intercept


def load_model_from_artifact(artifact_path: str | Path) -> LoadedModel:
    ap = Path(artifact_path)
    if not ap.exists():
        raise FileNotFoundError(f"Artifact not found: {ap}")

    meta_path = ap.parent / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.json not found next to artifact: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    feature_cols = list(meta.get("feature_cols", []))
    target_col = str(meta.get("target_col", "future_log_return"))

    schema_path = ap.parent / "feature_schema.json"
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = schema.get("feature_cols") if isinstance(schema, dict) else None
        if not isinstance(expected, list):
            raise ValueError(f"Invalid feature_schema.json format: {schema_path}")

        expected_cols = [str(c) for c in expected]
        if [str(c) for c in feature_cols] != expected_cols:
            raise ValueError("Feature schema mismatch: meta.json feature_cols != feature_schema.json")

    blob = np.load(ap)
    coef = np.asarray(blob["coef"], dtype=np.float64)
    intercept = float(np.asarray(blob["intercept"], dtype=np.float64).reshape(-1)[0])
    mean = np.asarray(blob["mean"], dtype=np.float64)
    scale = np.asarray(blob["scale"], dtype=np.float64)

    if len(feature_cols) != int(coef.shape[0]):
        raise ValueError("Artifact shape mismatch: feature_cols != coef")

    return LoadedModel(
        feature_cols=feature_cols,
        target_col=target_col,
        coef=coef,
        intercept=intercept,
        mean=mean,
        scale=scale,
    )
