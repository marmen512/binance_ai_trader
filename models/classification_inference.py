from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class LoadedClassifier:
    feature_cols: list[str]
    class_names: list[str]
    mean: np.ndarray
    scale: np.ndarray
    state_dict_path: Path
    input_dim: int
    hidden_dim: int
    dropout: float
    n_classes: int

    def predict_logits(self, x: np.ndarray) -> np.ndarray:
        import torch

        x = np.asarray(x, dtype=np.float64)
        x = (x - self.mean) / self.scale

        xt = torch.tensor(x, dtype=torch.float32)
        model = _build_model(
            input_dim=int(self.input_dim),
            hidden_dim=int(self.hidden_dim),
            dropout=float(self.dropout),
            n_classes=int(self.n_classes),
        )
        blob = torch.load(self.state_dict_path, map_location="cpu")
        model.load_state_dict(blob)
        model.eval()
        with torch.no_grad():
            logits = model(xt).cpu().numpy()
        return np.asarray(logits, dtype=np.float64)


def _build_model(*, input_dim: int, hidden_dim: int, dropout: float, n_classes: int):
    import torch.nn as nn

    return nn.Sequential(
        nn.Linear(int(input_dim), int(hidden_dim)),
        nn.ReLU(),
        nn.Dropout(p=float(dropout)),
        nn.Linear(int(hidden_dim), int(n_classes)),
    )


def load_classifier_from_artifact(artifact_path: str | Path) -> LoadedClassifier:
    ap = Path(artifact_path)
    if not ap.exists():
        raise FileNotFoundError(f"Artifact not found: {ap}")

    meta_path = ap.parent / "meta.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.json not found next to artifact: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    feature_cols = list(meta.get("feature_cols", []))
    class_names = list(meta.get("class_names", ["SHORT", "FLAT", "LONG"]))

    schema_path = ap.parent / "feature_schema.json"
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        expected = schema.get("feature_cols") if isinstance(schema, dict) else None
        if not isinstance(expected, list):
            raise ValueError(f"Invalid feature_schema.json format: {schema_path}")

        expected_cols = [str(c) for c in expected]
        if [str(c) for c in feature_cols] != expected_cols:
            raise ValueError("Feature schema mismatch: meta.json feature_cols != feature_schema.json")

    input_dim = int(meta.get("input_dim", len(feature_cols)))
    hidden_dim = int(meta.get("hidden_dim", 128))
    dropout = float(meta.get("dropout", 0.10))
    n_classes = int(meta.get("n_classes", 3))

    mean = np.asarray(meta.get("scaler_mean", []), dtype=np.float64)
    scale = np.asarray(meta.get("scaler_scale", []), dtype=np.float64)

    if len(feature_cols) != int(mean.shape[0]) or len(feature_cols) != int(scale.shape[0]):
        raise ValueError("Artifact shape mismatch: feature_cols != scaler params")

    return LoadedClassifier(
        feature_cols=feature_cols,
        class_names=class_names,
        mean=mean,
        scale=scale,
        state_dict_path=ap,
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        dropout=dropout,
        n_classes=n_classes,
    )
