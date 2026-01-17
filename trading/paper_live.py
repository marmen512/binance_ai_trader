from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from execution_safety.post_trade_checks import run_post_trade_checks
from execution_safety.pre_trade_checks import run_pre_trade_checks
from market.live_fetcher import (
    gate_new_closed_candles,
    latest_closed_1h_klines,
    last_processed_close_time_ms_from_cursor,
    last_trade_close_time_ms_from_cursor,
    read_live_cursor,
    write_live_cursor_v2,
)
from model_registry.registry import ModelCard
from models.predictor import predict_classifier_row
from trading.live_features import build_live_features
from trading.paper_broker import PaperFill, PaperState, execute_to_target, load_state, save_state
from trading.paper_session import ensure_session
from trading.risk_gate import allow_trade_with_reason


@dataclass(frozen=True)
class PaperTradeLiveOnceResult:
    ok: bool
    processed_candles: int
    executed_trades: int
    cursor_path: str
    last_processed_close_time_ms: int | None
    metrics_path: str
    trades_path: str
    state_path: str
    error: str | None


def _ensure_writer(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict) -> None:
    _ensure_writer(path)
    path.open("a", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False) + "\n")


def _read_equity_peak(metrics_path: Path) -> float | None:
    if not metrics_path.exists():
        return None
    try:
        lines = metrics_path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None

    peak: float | None = None
    for ln in lines[-5000:]:
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        try:
            e = float(obj.get("equity"))
        except Exception:
            continue
        peak = e if peak is None else max(peak, e)
    return peak


def _load_model_card(model_id: str, *, cards_dir: str | Path) -> ModelCard:
    p = Path(cards_dir) / f"{model_id}.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    if "data_sha256" not in raw and "dataset_sha256" in raw:
        raw["data_sha256"] = raw["dataset_sha256"]

    allowed = set(getattr(ModelCard, "__annotations__", {}).keys())
    filtered = {k: v for k, v in raw.items() if k in allowed}
    return ModelCard(**filtered)


def paper_trade_live_once(
    *,
    pair: str,
    model_id: str,
    cards_dir: str | Path = Path("model_registry") / "model_cards",
    state_path: str | Path = Path("ai_data") / "paper" / "state.json",
    cursor_path: str | Path = Path("ai_data") / "paper" / "live_cursor.json",
    session_path: str | Path = Path("ai_data") / "paper" / "session.json",
    metrics_path: str | Path = Path("ai_data") / "paper" / "metrics.jsonl",
    trades_path: str | Path = Path("ai_data") / "paper" / "trades.jsonl",
    fee_bps: float = 1.0,
    slippage_bps: float = 1.0,
    max_leverage: float = 1.0,
    deposit: float | None = None,
    reset_state: bool = False,
    enforce_trade_validity: bool = True,
    classifier_min_conf: float = 0.45,
    cooldown_candles: int = 1,
    fetch_limit: int = 300,
) -> PaperTradeLiveOnceResult:
    try:
        card = _load_model_card(model_id, cards_dir=cards_dir)

        sess = ensure_session(
            session_path=Path(session_path),
            model_id=str(model_id),
            pair=str(pair),
            params={
                "deposit": float(deposit) if deposit is not None else None,
                "max_leverage": float(max_leverage),
                "fee_bps": float(fee_bps),
                "slippage_bps": float(slippage_bps),
                "classifier_min_conf": float(classifier_min_conf),
                "cooldown_candles": int(cooldown_candles),
            },
            force_new=bool(reset_state),
        )

        session_dir_raw = sess.params.get("session_dir")
        if session_dir_raw:
            sdir = Path(str(session_dir_raw))
            state_path = sdir / "state.json"
            metrics_path = sdir / "metrics.jsonl"
            trades_path = sdir / "trades.jsonl"

        if reset_state:
            init_cash = float(deposit) if deposit is not None else 10_000.0
            st = PaperState(cash=init_cash, position_units=0.0, fees_paid=0.0)
            save_state(state_path, st)
        else:
            st = load_state(state_path)

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

        fetch = latest_closed_1h_klines(symbol=str(pair), limit=int(fetch_limit), now_ms=now_ms)
        if not fetch.ok:
            return PaperTradeLiveOnceResult(
                ok=False,
                processed_candles=0,
                executed_trades=0,
                cursor_path=str(cursor_path),
                last_processed_close_time_ms=None,
                metrics_path=str(metrics_path),
                trades_path=str(trades_path),
                state_path=str(state_path),
                error=str(fetch.error),
            )

        raw_df = fetch.df.copy()
        if raw_df.empty:
            return PaperTradeLiveOnceResult(
                ok=True,
                processed_candles=0,
                executed_trades=0,
                cursor_path=str(cursor_path),
                last_processed_close_time_ms=None,
                metrics_path=str(metrics_path),
                trades_path=str(trades_path),
                state_path=str(state_path),
                error=None,
            )

        cursor = read_live_cursor(Path(cursor_path))
        last_ms = last_processed_close_time_ms_from_cursor(cursor)
        last_trade_ms = last_trade_close_time_ms_from_cursor(cursor)

        new_closed_df, new_cursor_ms = gate_new_closed_candles(df=raw_df, last_processed_close_time_ms=last_ms, now_ms=now_ms)
        if new_closed_df.empty:
            return PaperTradeLiveOnceResult(
                ok=True,
                processed_candles=0,
                executed_trades=0,
                cursor_path=str(cursor_path),
                last_processed_close_time_ms=last_ms,
                metrics_path=str(metrics_path),
                trades_path=str(trades_path),
                state_path=str(state_path),
                error=None,
            )

        # Build features on full history to satisfy rolling windows, then process only new candles.
        raw_df = raw_df.sort_values("timestamp").reset_index(drop=True)
        feat_df = build_live_features(raw_df)

        # Process candles sequentially by close_time_ms.
        targets = set(pd.to_numeric(new_closed_df["close_time_ms"], errors="coerce").dropna().astype("int64").tolist())
        processed = 0
        executed_trades = 0
        last_trade_close_time_ms: int | None = last_trade_ms

        equity_peak = _read_equity_peak(Path(metrics_path))

        for _, row in feat_df.iterrows():
            ctm = row.get("close_time_ms")
            try:
                ctm_i = int(ctm)
            except Exception:
                continue
            if ctm_i not in targets:
                continue

            mid = float(pd.to_numeric(row.get("close"), errors="coerce"))
            if not (mid > 0):
                continue

            pred = predict_classifier_row(row=row, model_card=card)

            label = str(pred.class_label).upper()
            conf = float(pred.confidence)

            if conf < float(classifier_min_conf):
                tgt_pos = 0.0
            elif label == "SHORT" or label == "DOWN":
                tgt_pos = -float(max_leverage)
            elif label == "LONG" or label == "UP":
                tgt_pos = float(max_leverage)
            else:
                tgt_pos = 0.0

            gate = allow_trade_with_reason(
                state=st,
                prediction=label,
                confidence=float(conf),
                config={
                    "classifier_min_conf": float(classifier_min_conf),
                    "cooldown_candles": int(cooldown_candles),
                    "last_trade_close_time_ms": int(last_trade_close_time_ms) if last_trade_close_time_ms is not None else None,
                    "current_close_time_ms": int(ctm_i),
                },
            )

            if not gate.ok:
                tgt_pos = 0.0

            pre = run_pre_trade_checks(
                row,
                target_position=float(tgt_pos),
                max_leverage=float(max_leverage),
                enforce_trade_validity=bool(enforce_trade_validity),
            )

            equity_before = float(st.cash + st.position_units * mid)
            if equity_peak is None:
                equity_peak = float(equity_before)
            equity_peak = max(float(equity_peak), float(equity_before))
            drawdown = (float(equity_before) / float(equity_peak)) - 1.0 if float(equity_peak) > 0 else 0.0

            executed = False
            fill: PaperFill | None = None
            if pre.ok and gate.ok:
                st2, fill = execute_to_target(
                    state=st,
                    target_position=float(tgt_pos),
                    mid_price=mid,
                    fee_bps=float(fee_bps),
                    slippage_bps=float(slippage_bps),
                )
                executed = bool(fill.ok and abs(fill.delta_units) > 1e-12)
                st = st2

            post = run_post_trade_checks()

            ts = row.get("close_time") if "close_time" in row.index else row.get("timestamp")
            try:
                ts_s = pd.to_datetime(ts, utc=True).isoformat() if ts is not None else None
            except Exception:
                ts_s = None

            pos_label = "LONG" if tgt_pos > 0 else ("SHORT" if tgt_pos < 0 else "FLAT")

            metrics_rec = {
                "session_id": str(sess.session_id),
                "timestamp": ts_s,
                "equity": float(equity_before),
                "balance": float(st.cash),
                "drawdown": float(drawdown),
                "confidence": float(conf),
                "position": str(pos_label),
                "price": float(mid),
            }
            _append_jsonl(Path(metrics_path), metrics_rec)

            if executed and fill is not None:
                equity_after = float(fill.equity_after)
                pnl = float(equity_after - equity_before)
                trade_rec = {
                    "session_id": str(sess.session_id),
                    "trade_id": f"{ts_s or 'na'}_{ctm_i}",
                    "timestamp": ts_s,
                    "pair": str(pair),
                    "side": str(pos_label),
                    "entry_price": float(fill.price),
                    "exit_price": float(fill.price),
                    "size": float(abs(fill.delta_units)),
                    "pnl": float(pnl),
                }
                _append_jsonl(Path(trades_path), trade_rec)
                executed_trades += 1
                last_trade_close_time_ms = int(ctm_i)

            save_state(state_path, st)

            processed += 1

        if new_cursor_ms is not None:
            write_live_cursor_v2(
                Path(cursor_path),
                last_processed_close_time_ms=int(new_cursor_ms),
                last_trade_close_time_ms=int(last_trade_close_time_ms) if last_trade_close_time_ms is not None else None,
            )

        return PaperTradeLiveOnceResult(
            ok=True,
            processed_candles=int(processed),
            executed_trades=int(executed_trades),
            cursor_path=str(cursor_path),
            last_processed_close_time_ms=int(new_cursor_ms) if new_cursor_ms is not None else last_ms,
            metrics_path=str(metrics_path),
            trades_path=str(trades_path),
            state_path=str(state_path),
            error=None,
        )

    except Exception as e:
        return PaperTradeLiveOnceResult(
            ok=False,
            processed_candles=0,
            executed_trades=0,
            cursor_path=str(cursor_path),
            last_processed_close_time_ms=None,
            metrics_path=str(metrics_path),
            trades_path=str(trades_path),
            state_path=str(state_path),
            error=str(e),
        )
