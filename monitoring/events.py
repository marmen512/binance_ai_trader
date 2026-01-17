from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Event:
    ts: str
    kind: str
    payload: dict


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(
    kind: str,
    payload: dict,
    *,
    path: str | Path = Path("ai_data") / "monitoring" / "events.jsonl",
) -> Event:
    e = Event(ts=_now_ts(), kind=str(kind), payload=dict(payload))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.open("a", encoding="utf-8").write(json.dumps(e.__dict__, ensure_ascii=False) + "\n")
    return e


def read_recent_events(
    *,
    path: str | Path = Path("ai_data") / "monitoring" / "events.jsonl",
    limit: int = 200,
) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []

    lines = p.read_text(encoding="utf-8").splitlines()
    out: list[dict] = []
    for line in lines[-int(max(1, limit)) :]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
