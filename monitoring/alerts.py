from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class Alert:
    ts: str
    level: str
    code: str
    message: str
    payload: dict


def _now_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_alert(
    *,
    level: str,
    code: str,
    message: str,
    payload: dict | None = None,
    path: str | Path = Path("ai_data") / "monitoring" / "last_alert.json",
) -> Alert:
    a = Alert(
        ts=_now_ts(),
        level=str(level),
        code=str(code),
        message=str(message),
        payload={} if payload is None else dict(payload),
    )
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(a.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return a


def read_last_alert(*, path: str | Path = Path("ai_data") / "monitoring" / "last_alert.json") -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
