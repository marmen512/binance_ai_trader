from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class MetricsSnapshot:
    ts: str
    metrics: dict[str, float]


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_metrics(
    metrics: dict[str, float],
    *,
    path: str | Path = Path("ai_data") / "monitoring" / "metrics.json",
) -> MetricsSnapshot:
    snap = MetricsSnapshot(ts=_now_ts(), metrics={k: float(v) for k, v in metrics.items()})
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(snap.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snap


def read_metrics(*, path: str | Path = Path("ai_data") / "monitoring" / "metrics.json") -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
