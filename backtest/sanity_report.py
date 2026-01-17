from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PaperSanityReport:
    ok: bool
    session_id: str | None
    rows: int
    paper_final_equity: float | None
    replay_final_equity: float | None
    final_diff_pct: float | None
    corr: float | None
    identical: bool
    error: str | None


def _read_jsonl(path: Path, *, limit: int) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    lines = lines[-int(max(1, limit)) :]
    out: list[dict] = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


def build_paper_sanity_report(
    *,
    metrics_path: Path,
    session_id: str | None,
    limit_rows: int = 2000,
) -> PaperSanityReport:
    try:
        rows = _read_jsonl(metrics_path, limit=int(limit_rows))
        if not rows:
            return PaperSanityReport(
                ok=False,
                session_id=session_id,
                rows=0,
                paper_final_equity=None,
                replay_final_equity=None,
                final_diff_pct=None,
                corr=None,
                identical=False,
                error="NO_METRICS",
            )

        df = pd.DataFrame(rows)
        if session_id is not None and "session_id" in df.columns:
            df = df[df["session_id"].astype("object") == str(session_id)].copy()

        if df.empty:
            return PaperSanityReport(
                ok=False,
                session_id=session_id,
                rows=0,
                paper_final_equity=None,
                replay_final_equity=None,
                final_diff_pct=None,
                corr=None,
                identical=False,
                error="NO_ROWS_FOR_SESSION",
            )

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

        if "price" not in df.columns or "position" not in df.columns or "equity" not in df.columns:
            return PaperSanityReport(
                ok=False,
                session_id=session_id,
                rows=int(df.shape[0]),
                paper_final_equity=None,
                replay_final_equity=None,
                final_diff_pct=None,
                corr=None,
                identical=False,
                error="MISSING_REQUIRED_FIELDS",
            )

        price = pd.to_numeric(df["price"], errors="coerce")
        paper_eq = pd.to_numeric(df["equity"], errors="coerce")
        pos_s = df["position"].astype("object").fillna("FLAT").astype(str).str.upper()

        pos = pos_s.map({"SHORT": -1.0, "FLAT": 0.0, "LONG": 1.0}).fillna(0.0)

        rets = price.pct_change().replace([np.inf, -np.inf], 0.0).fillna(0.0)
        replay = pd.Series(index=df.index, dtype="float64")
        start_eq = float(paper_eq.dropna().iloc[0]) if not paper_eq.dropna().empty else 1.0
        replay.iloc[0] = start_eq
        for i in range(1, int(df.shape[0])):
            replay.iloc[i] = float(replay.iloc[i - 1]) * (1.0 + float(pos.iloc[i - 1]) * float(rets.iloc[i]))

        paper_eq2 = paper_eq.fillna(method="ffill").fillna(method="bfill")

        identical = bool(np.allclose(paper_eq2.to_numpy(), replay.to_numpy(), rtol=0.0, atol=0.0))

        pe = float(paper_eq2.iloc[-1])
        re = float(replay.iloc[-1])
        final_diff_pct = (re / pe) - 1.0 if pe != 0 else None

        corr = None
        try:
            corr = float(np.corrcoef(paper_eq2.to_numpy(), replay.to_numpy())[0, 1])
        except Exception:
            corr = None

        ok = True
        if identical:
            ok = False
        if final_diff_pct is not None and abs(final_diff_pct) > 0.20:
            ok = False

        return PaperSanityReport(
            ok=bool(ok),
            session_id=session_id,
            rows=int(df.shape[0]),
            paper_final_equity=float(pe),
            replay_final_equity=float(re),
            final_diff_pct=float(final_diff_pct) if final_diff_pct is not None else None,
            corr=corr,
            identical=bool(identical),
            error=None,
        )

    except Exception as e:
        return PaperSanityReport(
            ok=False,
            session_id=session_id,
            rows=0,
            paper_final_equity=None,
            replay_final_equity=None,
            final_diff_pct=None,
            corr=None,
            identical=False,
            error=str(e),
        )
