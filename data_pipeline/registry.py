from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class RegistryCard:
    name: str
    source: str
    path: str
    hash: str
    sha256: str
    date_range: str
    frequency: str
    columns: list[str]
    no_overwrite: bool
    created_at: str


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_registry_card(
    *,
    out_path: str | Path,
    name: str,
    source: str,
    data_path: str | Path,
    frequency: str,
    columns: list[str],
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
) -> RegistryCard:
    op = Path(out_path)
    dp = Path(data_path)
    if not dp.exists():
        raise BinanceAITraderError(f"Registry data path missing: {dp}")

    op.parent.mkdir(parents=True, exist_ok=True)
    if op.exists():
        raise BinanceAITraderError(f"Refusing to overwrite registry card: {op}")

    sha = _sha256_file(dp)
    card = RegistryCard(
        name=str(name),
        source=str(source),
        path=str(dp),
        hash=f"sha256:{sha}",
        sha256=str(sha),
        date_range=f"{start_ts.date().isoformat()} -> {end_ts.date().isoformat()}",
        frequency=str(frequency),
        columns=[str(c) for c in columns],
        no_overwrite=True,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    op.write_text(json.dumps(card.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return card
