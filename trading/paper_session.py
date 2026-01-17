from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PaperSession:
    session_id: str
    start_time: str
    model_id: str
    pair: str
    params: dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_session(path: Path) -> PaperSession | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return PaperSession(
            session_id=str(raw.get("session_id")),
            start_time=str(raw.get("start_time")),
            model_id=str(raw.get("model_id")),
            pair=str(raw.get("pair")),
            params=dict(raw.get("params", {})),
        )
    except Exception:
        return None


def write_session(path: Path, session: PaperSession) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_id": str(session.session_id),
        "start_time": str(session.start_time),
        "model_id": str(session.model_id),
        "pair": str(session.pair),
        "params": dict(session.params),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def session_dir(*, paper_root: Path, session_id: str) -> Path:
    return Path(paper_root) / "sessions" / f"session_{str(session_id)}"


def write_session_meta(*, out_dir: Path, session: PaperSession) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "session_id": str(session.session_id),
        "model_id": str(session.model_id),
        "start_time": str(session.start_time),
        "pair": str(session.pair),
        "deposit": session.params.get("deposit"),
        "leverage": session.params.get("max_leverage"),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_session(
    *,
    session_path: Path,
    model_id: str,
    pair: str,
    params: dict[str, Any],
    force_new: bool = False,
) -> PaperSession:
    paper_root = session_path.parent

    if not force_new:
        existing = read_session(session_path)
        if existing is not None and existing.model_id == str(model_id) and existing.pair == str(pair):
            sdir_raw = existing.params.get("session_dir")
            if sdir_raw:
                sdir = Path(str(sdir_raw))
            else:
                sdir = session_dir(paper_root=paper_root, session_id=str(existing.session_id))
                existing = PaperSession(
                    session_id=str(existing.session_id),
                    start_time=str(existing.start_time),
                    model_id=str(existing.model_id),
                    pair=str(existing.pair),
                    params={**dict(existing.params), "session_dir": str(sdir)},
                )
                write_session(session_path, existing)

            write_session_meta(out_dir=sdir, session=existing)
            for fn in ["metrics.jsonl", "trades.jsonl"]:
                p = sdir / fn
                if not p.exists():
                    p.write_text("", encoding="utf-8")
            return existing

    sid = uuid.uuid4().hex
    sess = PaperSession(
        session_id=str(sid),
        start_time=_utc_now_iso(),
        model_id=str(model_id),
        pair=str(pair),
        params=dict(params),
    )

    sdir = session_dir(paper_root=paper_root, session_id=str(sess.session_id))
    sess2 = PaperSession(
        session_id=str(sess.session_id),
        start_time=str(sess.start_time),
        model_id=str(sess.model_id),
        pair=str(sess.pair),
        params={**dict(sess.params), "session_dir": str(sdir)},
    )

    write_session_meta(out_dir=sdir, session=sess2)
    for fn in ["metrics.jsonl", "trades.jsonl"]:
        p = sdir / fn
        if not p.exists():
            p.write_text("", encoding="utf-8")
    write_session(session_path, sess2)
    return sess2
