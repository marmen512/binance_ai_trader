from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class DatasetCard:
    dataset_id: str
    created_at: str
    paths: list[str]
    sha256: str
    rows: int
    start_ts: str | None
    end_ts: str | None


def _hash_files(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: str(x)):
        h.update(str(p).encode("utf-8"))
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    return h.hexdigest()


def write_dataset_card(
    registry_dir: str | Path,
    paths: list[str | Path],
    *,
    rows: int,
    start_ts: str | None,
    end_ts: str | None,
) -> DatasetCard:
    reg = Path(registry_dir)
    reg.mkdir(parents=True, exist_ok=True)

    path_objs = [Path(p) for p in paths]
    for p in path_objs:
        if not p.exists():
            raise BinanceAITraderError(f"Dataset path not found: {p}")

    sha256 = _hash_files(path_objs)
    created_at = datetime.now(timezone.utc).isoformat()
    dataset_id = f"ds_{sha256[:12]}"

    card = DatasetCard(
        dataset_id=dataset_id,
        created_at=created_at,
        paths=[str(p) for p in path_objs],
        sha256=sha256,
        rows=int(rows),
        start_ts=start_ts,
        end_ts=end_ts,
    )

    out_path = reg / f"{dataset_id}.json"
    out_path.write_text(json.dumps(card.__dict__, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return card
