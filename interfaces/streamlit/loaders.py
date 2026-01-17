from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


def read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_jsonl(path: Path, *, limit: int | None = None) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    if limit is not None:
        lines = lines[-int(max(1, limit)) :]

    out: list[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def to_df(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"], utc=True, errors="coerce")
    return df


@dataclass(frozen=True)
class TensorBoardRun:
    run_dir: Path
    event_files: list[Path]


def find_tb_runs(log_root: Path) -> list[TensorBoardRun]:
    if not log_root.exists():
        return []

    runs: list[TensorBoardRun] = []
    for p in sorted(log_root.rglob("events.out.tfevents*")):
        rd = p.parent
        existing = next((r for r in runs if r.run_dir == rd), None)
        if existing is None:
            runs.append(TensorBoardRun(run_dir=rd, event_files=[p]))
        else:
            existing.event_files.append(p)

    runs = sorted(runs, key=lambda r: str(r.run_dir))
    return runs


def load_tb_scalars(run: TensorBoardRun) -> pd.DataFrame:
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    if not run.event_files:
        return pd.DataFrame()

    ea = EventAccumulator(str(run.run_dir), size_guidance={"scalars": 0})
    ea.Reload()

    tags = ea.Tags().get("scalars", [])
    if not tags:
        return pd.DataFrame()

    rows: list[dict] = []
    for tag in tags:
        for ev in ea.Scalars(tag):
            rows.append({"step": int(ev.step), "tag": str(tag), "value": float(ev.value)})

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    wide = df.pivot_table(index="step", columns="tag", values="value", aggfunc="last").sort_index()
    wide = wide.reset_index()
    return wide
