from __future__ import annotations

from pathlib import Path


def is_emergency_stop_active(*, stop_file: str | Path = Path("ai_data") / "paper" / "STOP") -> bool:
    p = Path(stop_file)
    return p.exists()
