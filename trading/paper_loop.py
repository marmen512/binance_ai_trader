from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.normalization import normalize_columns
from features.copy_trader_stats import add_copy_trader_stats
from features.technical import add_technical_features
from features.time_features import add_time_features
from features.volatility import add_volatility_features
from features.volume import add_volume_features
from execution_safety.post_trade_checks import run_post_trade_checks
from execution_safety.pre_trade_checks import run_pre_trade_checks
from monitoring.alerts import write_alert
from monitoring.events import append_event
from model_registry.registry import ModelCard
from models.classification_inference import load_classifier_from_artifact
from models.inference import load_model_from_artifact
from trading.decision_engine import DecisionConfig, predictions_to_position
from trading.paper_broker import PaperFill, PaperState, execute_to_target, load_state, save_state


@dataclass(frozen=True)
class PaperTradeLoopResult:
    ok: bool
    model_id: str
    rows: int
    trades: int
    start_ts: str | None
    end_ts: str | None
    state_path: str
    trades_path: str
    metrics_path: str


def _load_model_card(model_id: str, *, cards_dir: str | Path) -> ModelCard:
    p = Path(cards_dir) / f"{model_id}.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    if "data_sha256" not in raw and "dataset_sha256" in raw:
        raw["data_sha256"] = raw["dataset_sha256"]

    allowed = set(getattr(ModelCard, "__annotations__", {}).keys())
    filtered = {k: v for k, v in raw.items() if k in allowed}
    return ModelCard(**filtered)


def _ensure_writer(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _append_jsonl(path: Path, obj: dict) -> None:
    _ensure_writer(path)
    path.open("a", encoding="utf-8").write(json.dumps(obj, ensure_ascii=False) + "\n")


def _infer_target_position(
    *,
    row: pd.Series,
    model_card: ModelCard,
    max_leverage: float,
    decision_cfg: DecisionConfig,
    classifier_min_conf: float,
) -> tuple[float, dict]:
    """Returns (target_position, debug_payload)."""

    debug: dict = {}

    if model_card.algo == "torch_mlp_classifier":
        clf = load_classifier_from_artifact(model_card.artifact_path)

        missing = [c for c in clf.feature_cols if c not in row.index]
        if missing:
            raise ValueError(f"Missing feature cols for classifier: {missing}")

        x = pd.DataFrame([row])[clf.feature_cols].to_numpy(dtype=np.float64)
        logits = clf.predict_logits(x)
        probs = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        probs = probs / np.clip(np.sum(probs, axis=1, keepdims=True), 1e-12, None)
        p = probs.reshape(-1)

        pred = int(np.argmax(p))
        conf = float(p[pred]) if p.size else 0.0

        debug.update({"kind": "classifier", "probs": [float(v) for v in p], "pred": pred, "conf": conf})

        if conf < float(classifier_min_conf):
            return 0.0, debug

        # class idx mapping in training: 0=SHORT, 1=FLAT, 2=LONG
        if pred == 0:
            return -float(max_leverage), debug
        if pred == 2:
            return float(max_leverage), debug
        return 0.0, debug

    # default: regression-style artifact
    reg = load_model_from_artifact(model_card.artifact_path)

    missing = [c for c in reg.feature_cols if c not in row.index]
    if missing:
        raise ValueError(f"Missing feature cols for regression model: {missing}")

    x = pd.DataFrame([row])[reg.feature_cols].to_numpy(dtype=np.float64)
    y_hat = float(reg.predict(x).reshape(-1)[0])
    y_hat_s = pd.Series([y_hat], index=[0], dtype="float64")
    df1 = pd.DataFrame([row])

    pos = predictions_to_position(df1, y_hat_s, decision_cfg)
    tgt = float(pos.iloc[0]) if not pos.empty else 0.0

    debug.update({"kind": "regression", "y_hat": y_hat, "target_position": tgt})

    return float(np.clip(tgt, -float(max_leverage), float(max_leverage))), debug


def _build_features_for_loop(df: pd.DataFrame) -> pd.DataFrame:
    out = normalize_columns(df)
    out = add_technical_features(out)
    out = add_volatility_features(out)
    out = add_volume_features(out)
    out = add_time_features(out)
    out = add_copy_trader_stats(out)

    # Keep only rows where feature engineering produced finite values.
    out2 = out.dropna().reset_index(drop=True)
    return out2


def paper_trade_loop(
    paths: list[str | Path],
    *,
    model_id: str,
    pair: str | None = None,
    state_path: str | Path = Path("ai_data") / "paper" / "state.json",
    trades_path: str | Path = Path("ai_data") / "paper" / "trades.jsonl",
    metrics_path: str | Path = Path("ai_data") / "paper" / "metrics.jsonl",
    cards_dir: str | Path = Path("model_registry") / "model_cards",
    fee_bps: float = 1.0,
    slippage_bps: float = 1.0,
    max_leverage: float = 1.0,
    enforce_trade_validity: bool = True,
    deposit: float | None = None,
    reset_state: bool = False,
    start_index: int = 0,
    max_steps: int | None = None,
    classifier_min_conf: float = 0.45,
    decision_cfg: DecisionConfig | None = None,
) -> PaperTradeLoopResult:
    cfg = decision_cfg or DecisionConfig(max_leverage=float(max_leverage))

    dfs = [pd.read_parquet(Path(p)) for p in paths]
    df0 = pd.concat(dfs, axis=0, ignore_index=True)
    if "timestamp" in df0.columns:
        df0["timestamp"] = pd.to_datetime(df0["timestamp"], utc=True, errors="coerce")
        df0 = df0.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    df = _build_features_for_loop(df0)

    if df.empty or "close" not in df.columns:
        write_alert(level="error", code="PAPER_LOOP_BAD_DATA", message="Empty dataframe or missing close")
        append_event("paper_trade_loop", {"ok": False, "reason": "BAD_DATA"})
        return PaperTradeLoopResult(
            ok=False,
            model_id=model_id,
            rows=int(df.shape[0]),
            trades=0,
            start_ts=None,
            end_ts=None,
            state_path=str(state_path),
            trades_path=str(trades_path),
            metrics_path=str(metrics_path),
        )

    card = _load_model_card(model_id, cards_dir=cards_dir)

    if reset_state:
        init_cash = float(deposit) if deposit is not None else 10_000.0
        st = PaperState(cash=init_cash, position_units=0.0, fees_paid=0.0)
        save_state(state_path, st)
    else:
        st = load_state(state_path)

    start = int(max(0, start_index))
    end = int(df.shape[0])
    if max_steps is not None:
        end = min(end, start + int(max_steps))

    trade_count = 0
    equity_peak = None

    for i in range(start, end):
        row = df.iloc[i]
        mid = float(pd.to_numeric(row.get("close"), errors="coerce"))
        if not (mid > 0):
            continue

        try:
            tgt_pos, dbg = _infer_target_position(
                row=row,
                model_card=card,
                max_leverage=float(max_leverage),
                decision_cfg=cfg,
                classifier_min_conf=float(classifier_min_conf),
            )
        except Exception as e:
            write_alert(level="error", code="PAPER_LOOP_INFER_FAIL", message=str(e))
            append_event("paper_trade_loop", {"ok": False, "reason": "INFER_FAIL", "err": str(e), "i": i})
            continue

        pre = run_pre_trade_checks(
            row,
            target_position=float(tgt_pos),
            max_leverage=float(max_leverage),
            enforce_trade_validity=bool(enforce_trade_validity),
        )

        executed = False
        fill: PaperFill | None = None
        if pre.ok:
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

        ts = row.get("timestamp")
        ts_s = None
        try:
            ts_s = pd.to_datetime(ts, utc=True).isoformat() if ts is not None else None
        except Exception:
            ts_s = None

        equity_before = float(st.cash + st.position_units * mid)

        if tgt_pos > 0:
            pos_label = "LONG"
        elif tgt_pos < 0:
            pos_label = "SHORT"
        else:
            pos_label = "FLAT"

        confidence = None
        try:
            confidence = float(dbg.get("conf")) if isinstance(dbg, dict) and dbg.get("conf") is not None else None
        except Exception:
            confidence = None

        drawdown = None
        try:
            if equity_peak is None:
                equity_peak = float(equity_before)
            equity_peak = max(float(equity_peak), float(equity_before))
            drawdown = (float(equity_before) / float(equity_peak)) - 1.0 if float(equity_peak) > 0 else 0.0
        except Exception:
            drawdown = None

        # Contract-first metrics record (append-only)
        metrics_rec = {
            "timestamp": ts_s,
            "equity": float(equity_before),
            "balance": float(st.cash),
            "drawdown": float(drawdown) if drawdown is not None else None,
            "confidence": float(confidence) if confidence is not None else None,
            "position": str(pos_label),
            "price": float(mid),
            # legacy/debug fields (safe extras)
            "ts": ts_s,
            "i": int(i),
            "cash": float(st.cash),
            "position_units": float(st.position_units),
            "mid": float(mid),
            "target_position": float(tgt_pos),
        }
        _append_jsonl(Path(metrics_path), metrics_rec)

        # Only append a trade record when an execution actually happened.
        if executed and fill is not None:
            equity_after = float(fill.equity_after)
            pnl = float(equity_after - equity_before)

            trade_rec = {
                "trade_id": f"{ts_s or 'na'}_{int(i)}",
                "timestamp": ts_s,
                "pair": str(pair or ""),
                "side": str(pos_label),
                "entry_price": float(fill.price),
                "exit_price": float(fill.price),
                "size": float(abs(fill.delta_units)),
                "pnl": float(pnl),
                # legacy/debug fields (safe extras)
                "ts": ts_s,
                "i": int(i),
                "executed": bool(executed),
                "pre_ok": bool(pre.ok),
                "pre_reasons": list(pre.reasons),
                "post_ok": bool(post.ok),
                "post_reasons": list(post.reasons),
                "debug": dbg,
                "fill": {
                    "ok": bool(fill.ok),
                    "price": float(fill.price),
                    "delta_units": float(fill.delta_units),
                    "fee": float(fill.fee),
                    "cash_after": float(fill.cash_after),
                    "position_units_after": float(fill.position_units_after),
                    "equity_after": float(fill.equity_after),
                },
            }
            _append_jsonl(Path(trades_path), trade_rec)

        save_state(state_path, st)

        if executed:
            trade_count += 1

    start_ts = None
    end_ts = None
    if "timestamp" in df.columns and not df.empty:
        try:
            start_ts = pd.to_datetime(df.iloc[start].get("timestamp"), utc=True).isoformat()
            end_ts = pd.to_datetime(df.iloc[end - 1].get("timestamp"), utc=True).isoformat()
        except Exception:
            start_ts = None
            end_ts = None

    append_event(
        "paper_trade_loop",
        {
            "ok": True,
            "model_id": str(model_id),
            "rows": int(end - start),
            "trades": int(trade_count),
            "state_path": str(state_path),
            "trades_path": str(trades_path),
            "metrics_path": str(metrics_path),
        },
    )

    return PaperTradeLoopResult(
        ok=True,
        model_id=model_id,
        rows=int(end - start),
        trades=int(trade_count),
        start_ts=start_ts,
        end_ts=end_ts,
        state_path=str(state_path),
        trades_path=str(trades_path),
        metrics_path=str(metrics_path),
    )
