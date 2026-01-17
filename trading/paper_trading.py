from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.merge import merge_datasets
from data_pipeline.normalization import normalize_columns
from data_pipeline.parquet_loader import load_parquets
from data_pipeline.validation import validate_ohlcv
from execution_safety.post_trade_checks import run_post_trade_checks
from execution_safety.pre_trade_checks import run_pre_trade_checks
from monitoring.alerts import write_alert
from monitoring.events import append_event
from monitoring.metrics import write_metrics
from model_registry.registry import ModelCard
from models.inference import load_model_from_artifact
from trading.decision_engine import DecisionConfig, predictions_to_position
from trading.paper_broker import PaperFill, PaperState, execute_to_target, load_state, save_state


@dataclass(frozen=True)
class PaperTradeOnceResult:
    ok: bool
    model_id: str
    used_row_index: int
    mid_price: float
    y_hat: float
    target_position: float
    executed: bool
    fill: PaperFill | None
    pre_trade_ok: bool
    pre_trade_reasons: list[str]
    post_trade_ok: bool
    post_trade_reasons: list[str]
    state_path: str
    report_path: str


def _load_model_card(model_id: str, *, cards_dir: str | Path) -> ModelCard:
    p = Path(cards_dir) / f"{model_id}.json"
    raw = json.loads(p.read_text(encoding="utf-8"))
    if "data_sha256" not in raw and "dataset_sha256" in raw:
        raw["data_sha256"] = raw["dataset_sha256"]
    allowed = set(getattr(ModelCard, "__annotations__", {}).keys())
    filtered = {k: v for k, v in raw.items() if k in allowed}
    return ModelCard(**filtered)


def paper_trade_once(
    paths: list[str | Path],
    *,
    model_id: str,
    state_path: str | Path = Path("ai_data") / "paper" / "state.json",
    report_path: str | Path = Path("ai_data") / "paper" / "last_trade.json",
    cards_dir: str | Path = Path("model_registry") / "model_cards",
    fee_bps: float = 1.0,
    slippage_bps: float = 1.0,
    lookback: int = 200,
    require_eligible_row: bool = True,
    enforce_trade_validity: bool = True,
    position_mode: str = "risk_scaled",
    max_leverage: float | None = None,
    decision_cfg: DecisionConfig | None = None,
) -> PaperTradeOnceResult:
    cfg = decision_cfg or DecisionConfig()
    if max_leverage is not None:
        cfg = DecisionConfig(
            max_leverage=float(max_leverage),
            min_signal=cfg.min_signal,
            risk_vol_col=cfg.risk_vol_col,
            risk_atr_col=cfg.risk_atr_col,
        )

    dfs = load_parquets(paths)
    dfs = [normalize_columns(df) for df in dfs]
    merged = merge_datasets(dfs).df

    report = validate_ohlcv(merged)
    if not report.ok or merged.empty:
        write_alert(level="error", code="PAPER_INVALID_DATA", message="Invalid OHLCV input for paper trade")
        append_event("paper_trade_once", {"ok": False, "reason": "INVALID_DATA"})
        res = PaperTradeOnceResult(
            ok=False,
            model_id=model_id,
            used_row_index=-1,
            mid_price=0.0,
            y_hat=0.0,
            target_position=0.0,
            executed=False,
            fill=None,
            pre_trade_ok=False,
            pre_trade_reasons=["INVALID_DATA"],
            post_trade_ok=False,
            post_trade_reasons=[],
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        return res

    df = merged.copy()
    if "timestamp" in df.columns:
        df = df.sort_values("timestamp").reset_index(drop=True)

    # Choose the row to act on.
    # Default: search backwards for the most recent eligible row (e.g. trade_validity_target != SKIP).
    tail = df.tail(int(max(1, lookback))).reset_index(drop=True)
    selected = tail.iloc[-1]
    sel_idx = int(df.shape[0] - 1)

    if require_eligible_row and not tail.empty:
        for i in range(int(tail.shape[0]) - 1, -1, -1):
            r = tail.iloc[i]
            tv_ok = True
            if "trade_validity_target" in r.index:
                tv_ok = str(r.get("trade_validity_target")) != "SKIP"
            liq_ok = True
            if "low_liquidity_flag" in r.index:
                liq_ok = not bool(r.get("low_liquidity_flag", False))

            if tv_ok and liq_ok:
                selected = r
                sel_idx = int(df.shape[0] - (tail.shape[0] - i))
                break

    row = selected
    idx = int(sel_idx)

    if "close" not in df.columns:
        write_alert(level="error", code="PAPER_MISSING_CLOSE", message="Missing close column")
        append_event("paper_trade_once", {"ok": False, "reason": "MISSING_CLOSE"})
        res = PaperTradeOnceResult(
            ok=False,
            model_id=model_id,
            used_row_index=idx,
            mid_price=0.0,
            y_hat=0.0,
            target_position=0.0,
            executed=False,
            fill=None,
            pre_trade_ok=False,
            pre_trade_reasons=["MISSING_CLOSE"],
            post_trade_ok=False,
            post_trade_reasons=[],
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        return res

    mid = float(pd.to_numeric(row.get("close"), errors="coerce"))
    if not (mid > 0):
        write_alert(level="error", code="PAPER_BAD_PRICE", message="Bad close price")
        append_event("paper_trade_once", {"ok": False, "reason": "BAD_PRICE", "mid_price": mid})
        res = PaperTradeOnceResult(
            ok=False,
            model_id=model_id,
            used_row_index=idx,
            mid_price=mid,
            y_hat=0.0,
            target_position=0.0,
            executed=False,
            fill=None,
            pre_trade_ok=False,
            pre_trade_reasons=["BAD_PRICE"],
            post_trade_ok=False,
            post_trade_reasons=[],
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        return res

    card = _load_model_card(model_id, cards_dir=cards_dir)
    model = load_model_from_artifact(card.artifact_path)

    missing = [c for c in model.feature_cols if c not in df.columns]
    if missing:
        write_alert(
            level="error",
            code="PAPER_MISSING_FEATURES",
            message="Missing feature columns for inference",
            payload={"missing": missing},
        )
        append_event("paper_trade_once", {"ok": False, "reason": "MISSING_FEATURES", "missing": missing})
        res = PaperTradeOnceResult(
            ok=False,
            model_id=model_id,
            used_row_index=idx,
            mid_price=mid,
            y_hat=0.0,
            target_position=0.0,
            executed=False,
            fill=None,
            pre_trade_ok=False,
            pre_trade_reasons=["MISSING_FEATURES"],
            post_trade_ok=False,
            post_trade_reasons=[],
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        return res

    row_df = pd.DataFrame([row])
    x_row = row_df[model.feature_cols].to_numpy(dtype=np.float64)

    if not bool(np.isfinite(x_row).all()):
        write_alert(
            level="error",
            code="PAPER_DRIFT_INVALID_FEATURES",
            message="Feature vector contains NaN/inf",
            payload={"used_row_index": idx},
        )
        append_event("paper_trade_once", {"ok": False, "reason": "INVALID_FEATURES", "used_row_index": idx})
        res = PaperTradeOnceResult(
            ok=False,
            model_id=model_id,
            used_row_index=idx,
            mid_price=mid,
            y_hat=0.0,
            target_position=0.0,
            executed=False,
            fill=None,
            pre_trade_ok=False,
            pre_trade_reasons=[],
            post_trade_ok=False,
            post_trade_reasons=[],
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        return res

    y_hat = float(model.predict(x_row).reshape(-1)[0])

    if not bool(np.isfinite(y_hat)):
        write_alert(
            level="error",
            code="PAPER_DRIFT_INVALID_PREDICTION",
            message="Prediction contains NaN/inf",
            payload={"used_row_index": idx},
        )
        append_event("paper_trade_once", {"ok": False, "reason": "INVALID_PREDICTION", "used_row_index": idx})
        res = PaperTradeOnceResult(
            ok=False,
            model_id=model_id,
            used_row_index=idx,
            mid_price=mid,
            y_hat=0.0,
            target_position=0.0,
            executed=False,
            fill=None,
            pre_trade_ok=False,
            pre_trade_reasons=[],
            post_trade_ok=False,
            post_trade_reasons=[],
            state_path=str(state_path),
            report_path=str(report_path),
        )
        _write_report(report_path, res)
        return res

    if position_mode == "sign":
        if abs(y_hat) < 1e-12:
            target_pos = 0.0
        else:
            target_pos = float(np.sign(y_hat) * cfg.max_leverage)
    else:
        target_pos = float(predictions_to_position(row_df, pd.Series([y_hat]), cfg).iloc[0])

    pre = run_pre_trade_checks(
        row,
        target_position=target_pos,
        max_leverage=cfg.max_leverage,
        enforce_trade_validity=enforce_trade_validity,
    )
    executed = bool(pre.ok)

    state = load_state(state_path)

    if not pre.ok:
        write_alert(
            level="warning",
            code="PAPER_PRE_TRADE_BLOCK",
            message="Pre-trade checks blocked execution",
            payload={"reasons": list(pre.reasons)},
        )
        target_pos = 0.0

    new_state, fill = execute_to_target(
        state=state,
        target_position=target_pos,
        mid_price=mid,
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
    )
    save_state(state_path, new_state)

    post = run_post_trade_checks(equity=float(new_state.cash + new_state.position_units * mid))

    # Monitoring snapshot after the step
    write_metrics(
        {
            "paper_cash": float(new_state.cash),
            "paper_position_units": float(new_state.position_units),
            "paper_fees_paid": float(new_state.fees_paid),
            "paper_equity": float(new_state.cash + new_state.position_units * mid),
            "paper_mid_price": float(mid),
            "paper_target_position": float(target_pos),
            "paper_y_hat": float(y_hat),
        }
    )

    append_event(
        "paper_trade_once",
        {
            "ok": bool(pre.ok and post.ok),
            "model_id": model_id,
            "mid_price": float(mid),
            "y_hat": float(y_hat),
            "target_position": float(target_pos),
            "executed": bool(executed),
            "pre_trade_reasons": list(pre.reasons),
            "post_trade_reasons": list(post.reasons),
            "fill": None if fill is None else fill.__dict__,
        },
    )

    if not post.ok:
        write_alert(
            level="error",
            code="PAPER_POST_TRADE_FAIL",
            message="Post-trade checks failed",
            payload={"reasons": list(post.reasons)},
        )

    res = PaperTradeOnceResult(
        ok=bool(pre.ok and post.ok),
        model_id=model_id,
        used_row_index=idx,
        mid_price=mid,
        y_hat=y_hat,
        target_position=float(target_pos),
        executed=executed,
        fill=fill,
        pre_trade_ok=bool(pre.ok),
        pre_trade_reasons=list(pre.reasons),
        post_trade_ok=bool(post.ok),
        post_trade_reasons=list(post.reasons),
        state_path=str(state_path),
        report_path=str(report_path),
    )
    _write_report(report_path, res)
    return res


def _write_report(path: str | Path, res: PaperTradeOnceResult) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    payload = res.__dict__.copy()
    if res.fill is not None:
        payload["fill"] = res.fill.__dict__

    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
