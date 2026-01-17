from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from model_registry.registry import ModelCard
from models.classification_inference import load_classifier_from_artifact


@dataclass(frozen=True)
class ClassifierPrediction:
    class_index: int
    class_label: str
    confidence: float
    probs: list[float]


def predict_classifier_row(*, row: pd.Series, model_card: ModelCard) -> ClassifierPrediction:
    """Single inference entrypoint for the 1H classifier.

    Returns:
    - class_label in {SHORT, FLAT, LONG} (or whatever is stored in the artifact)
    - confidence = max softmax probability
    """

    clf = load_classifier_from_artifact(model_card.artifact_path)

    missing = [c for c in clf.feature_cols if c not in row.index]
    if missing:
        raise ValueError(f"Missing feature cols for classifier: {missing}")

    x = pd.DataFrame([row])[clf.feature_cols].to_numpy(dtype=np.float64)
    logits = clf.predict_logits(x)

    # stable softmax
    z = logits - np.max(logits, axis=1, keepdims=True)
    probs = np.exp(z)
    probs = probs / np.clip(np.sum(probs, axis=1, keepdims=True), 1e-12, None)

    p = probs.reshape(-1)
    pred = int(np.argmax(p)) if p.size else 0
    conf = float(p[pred]) if p.size else 0.0

    names = list(getattr(clf, "class_names", []) or ["SHORT", "FLAT", "LONG"])
    label = names[pred] if 0 <= pred < len(names) else str(pred)

    return ClassifierPrediction(
        class_index=pred,
        class_label=str(label),
        confidence=float(conf),
        probs=[float(v) for v in p.tolist()] if p.size else [],
    )
