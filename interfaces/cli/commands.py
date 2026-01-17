from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from core.config import load_config
from core.exceptions import BinanceAITraderError
from core.logging import setup_logger
from data_pipeline.dataset_downloader import DatasetDownloader
from data_pipeline.funding_loader_5m import download_funding_rate_5m
from data_pipeline.pipeline import validate_data
from data_pipeline.price_loader_5m import download_binance_futures_price_5m
from data_pipeline.oi_loader_5m import download_open_interest_5m
from data_pipeline.validators import (
    validate_funding_rate_5m,
    validate_open_interest_5m,
    validate_price_5m,
    validate_sentiment_agg_5m,
)
from data_pipeline.sentiment_aggregation import aggregate_sentiment
from interfaces.cli.output import CommandResult, render
from targets.pipeline import build_targets
from market.pipeline import detect_regime_pipeline
from strategies.sim import run_strategy_sim
from training.pipeline import train_offline
from training.classification_pipeline import train_classification_1h
from features.pipeline import build_features
from trading.pipeline import run_decision_engine
from trading.paper_trading import paper_trade_once
from trading.paper_loop import paper_trade_loop
from trading.paper_live import paper_trade_live_once
from trading.paper_session import read_session
from backtest.sanity_report import build_paper_sanity_report
from interfaces.cli.renderer import render_dependency_table
from interfaces.cli.render_validate import render_validate_json, render_validate_table
from interfaces.cli.render_features import render_build_features_json, render_build_features_table
from interfaces.cli.render_targets import render_build_targets_json, render_build_targets_table
from interfaces.cli.render_regime import render_detect_regime_json, render_detect_regime_table
from interfaces.cli.render_strategy_sim import render_strategy_sim_json, render_strategy_sim_table
from interfaces.cli.render_train_offline import render_train_offline_json, render_train_offline_table
from interfaces.cli.render_decision_engine import render_decision_engine_json, render_decision_engine_table
from interfaces.cli.render_copy_trade import render_copy_trade_json, render_copy_trade_table


def train_command(
    config_path: str | Path,
    *,
    timeframe: str,
    model_name: str,
    sentiment_freq: str | None,
    epochs: int,
    batch_size: int,
    lr: float,
    hidden_dim: int,
    dropout: float,
    seed: int,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    tf = str(timeframe).strip().lower()
    if tf != "1h":
        return CommandResult(exit_code=2, output="ERROR: timeframe must be 1h")

    res = train_classification_1h(
        model_name=model_name,
        sentiment_freq=sentiment_freq,
        epochs=int(epochs),
        batch_size=int(batch_size),
        lr=float(lr),
        hidden_dim=int(hidden_dim),
        dropout=float(dropout),
        seed=int(seed),
    )

    payload = {
        "ok": bool(res.ok),
        "model_id": res.model_id,
        "artifact_path": res.artifact_path,
        "model_card_path": res.model_card_path,
        "tb_log_dir": res.tb_log_dir,
        "rows_train": int(res.rows_train),
        "rows_val": int(res.rows_val),
        "metrics": {k: float(v) for k, v in res.metrics.items()},
    }

    if output == "json":
        out = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        out = "\n".join(
            [
                f"ok: {payload['ok']}",
                f"model_id: {payload['model_id']}",
                f"tb_log_dir: {payload['tb_log_dir']}",
                f"rows_train: {payload['rows_train']}",
                f"rows_val: {payload['rows_val']}",
            ]
        )
        out += "\n"

    if res.ok:
        logger.info("train: OK model_id=%s tb_log_dir=%s", res.model_id, res.tb_log_dir)
        return CommandResult(exit_code=0, output=out)

    logger.error("train: FAILED")
    return CommandResult(exit_code=2, output=out)


def paper_trade_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    pair: str,
    model_id: str,
    deposit: float,
    max_leverage: float,
    fee_bps: float,
    slippage_bps: float,
    enforce_trade_validity: bool,
    start_index: int,
    max_steps: int | None,
    reset_state: bool,
    classifier_min_conf: float,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = paper_trade_loop(
        paths,
        pair=str(pair),
        model_id=model_id,
        deposit=float(deposit),
        reset_state=bool(reset_state),
        max_leverage=float(max_leverage),
        fee_bps=float(fee_bps),
        slippage_bps=float(slippage_bps),
        enforce_trade_validity=bool(enforce_trade_validity),
        start_index=int(start_index),
        max_steps=int(max_steps) if max_steps is not None else None,
        classifier_min_conf=float(classifier_min_conf),
    )

    payload = {
        "ok": bool(res.ok),
        "model_id": str(res.model_id),
        "rows": int(res.rows),
        "trades": int(res.trades),
        "start_ts": res.start_ts,
        "end_ts": res.end_ts,
        "state_path": str(res.state_path),
        "trades_path": str(res.trades_path),
        "metrics_path": str(res.metrics_path),
    }

    if output == "json":
        out = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        out = "\n".join(
            [
                f"ok: {payload['ok']}",
                f"model_id: {payload['model_id']}",
                f"rows: {payload['rows']}",
                f"trades: {payload['trades']}",
                f"state_path: {payload['state_path']}",
                f"trades_path: {payload['trades_path']}",
                f"metrics_path: {payload['metrics_path']}",
            ]
        )
        out += "\n"

    if res.ok:
        logger.info("paper-trade: OK rows=%s trades=%s", res.rows, res.trades)
        return CommandResult(exit_code=0, output=out)

    logger.error("paper-trade: FAILED")
    return CommandResult(exit_code=2, output=out)


def paper_trade_live_once_command(
    config_path: str | Path,
    *,
    pair: str,
    model_id: str,
    deposit: float,
    max_leverage: float,
    fee_bps: float,
    slippage_bps: float,
    reset_state: bool,
    enforce_trade_validity: bool,
    classifier_min_conf: float,
    cooldown_candles: int,
    fetch_limit: int,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = paper_trade_live_once(
        pair=str(pair),
        model_id=str(model_id),
        deposit=float(deposit),
        max_leverage=float(max_leverage),
        fee_bps=float(fee_bps),
        slippage_bps=float(slippage_bps),
        reset_state=bool(reset_state),
        enforce_trade_validity=bool(enforce_trade_validity),
        classifier_min_conf=float(classifier_min_conf),
        cooldown_candles=int(cooldown_candles),
        fetch_limit=int(fetch_limit),
    )

    payload = {
        "ok": bool(res.ok),
        "processed_candles": int(res.processed_candles),
        "executed_trades": int(res.executed_trades),
        "cursor_path": str(res.cursor_path),
        "last_processed_close_time_ms": res.last_processed_close_time_ms,
        "metrics_path": str(res.metrics_path),
        "trades_path": str(res.trades_path),
        "state_path": str(res.state_path),
        "error": res.error,
    }

    if output == "json":
        out = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        out = "\n".join(
            [
                f"ok: {payload['ok']}",
                f"processed_candles: {payload['processed_candles']}",
                f"executed_trades: {payload['executed_trades']}",
                f"cursor_path: {payload['cursor_path']}",
                f"metrics_path: {payload['metrics_path']}",
                f"trades_path: {payload['trades_path']}",
                f"state_path: {payload['state_path']}",
            ]
        )
        out += "\n"

    if res.ok:
        logger.info(
            "paper-trade-live --once: OK processed=%s trades=%s",
            res.processed_candles,
            res.executed_trades,
        )
        return CommandResult(exit_code=0, output=out)

    logger.error("paper-trade-live --once: FAILED err=%s", res.error)
    return CommandResult(exit_code=2, output=out)


def paper_sanity_report_command(
    config_path: str | Path,
    *,
    session_id: str | None,
    limit_rows: int,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    session_path = Path("ai_data") / "paper" / "session.json"

    metrics_path = Path("ai_data") / "paper" / "metrics.jsonl"

    sid = session_id
    if sid is None:
        sess = read_session(session_path)
        if sess is not None:
            sid = sess.session_id

            sdir = sess.params.get("session_dir") if isinstance(sess.params, dict) else None
            if sdir:
                cand = Path(str(sdir)) / "metrics.jsonl"
                if cand.exists():
                    metrics_path = cand

    rep = build_paper_sanity_report(metrics_path=metrics_path, session_id=sid, limit_rows=int(limit_rows))

    payload = {
        "ok": bool(rep.ok),
        "session_id": rep.session_id,
        "rows": int(rep.rows),
        "paper_final_equity": rep.paper_final_equity,
        "replay_final_equity": rep.replay_final_equity,
        "final_diff_pct": rep.final_diff_pct,
        "corr": rep.corr,
        "identical": bool(rep.identical),
        "error": rep.error,
        "metrics_path": str(metrics_path),
    }

    if output == "json":
        out = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        out = "\n".join(
            [
                f"ok: {payload['ok']}",
                f"session_id: {payload['session_id']}",
                f"rows: {payload['rows']}",
                f"paper_final_equity: {payload['paper_final_equity']}",
                f"replay_final_equity: {payload['replay_final_equity']}",
                f"final_diff_pct: {payload['final_diff_pct']}",
                f"corr: {payload['corr']}",
                f"identical: {payload['identical']}",
                f"metrics_path: {payload['metrics_path']}",
            ]
        )
        out += "\n"

    if rep.ok:
        logger.info("paper-sanity-report: OK session_id=%s rows=%s", rep.session_id, rep.rows)
        return CommandResult(exit_code=0, output=out)

    logger.error("paper-sanity-report: FAILED err=%s", rep.error)
    return CommandResult(exit_code=2, output=out)


@dataclass(frozen=True)
class CommandResult:
    exit_code: int
    output: str


def health_check(config_path: str | Path) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")
    logger.info("Loaded config: env=%s log_level=%s", cfg.env, cfg.log_level)

    statuses = check_dependencies()
    table = render_dependency_table(statuses)
    ok = all(s.ok for s in statuses)
    exit_code = 0 if ok else 2

    if ok:
        logger.info("Dependency check: OK")
    else:
        logger.error("Dependency check: FAILED")

    return CommandResult(exit_code=exit_code, output=table)


def doctor(config_path: str | Path) -> CommandResult:
    return health_check(config_path)


def validate_data_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    output: str,
    write_registry: bool,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = validate_data(paths, write_registry=write_registry)

    if output == "json":
        out = render_validate_json(res)
    else:
        out = render_validate_table(res)

    if res.report.ok:
        logger.info("validate-data: OK rows=%s", res.report.rows)
        return CommandResult(exit_code=0, output=out)

    logger.error("validate-data: FAILED")
    return CommandResult(exit_code=2, output=out)


def build_features_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    output_path: str | Path,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = build_features(paths, output_path=output_path)

    if output == "json":
        out = render_build_features_json(res)
    else:
        out = render_build_features_table(res)

    if res.ok:
        logger.info("build-features: OK rows_in=%s rows_out=%s", res.rows_in, res.rows_out)
        return CommandResult(exit_code=0, output=out)

    logger.error("build-features: FAILED")
    return CommandResult(exit_code=2, output=out)


def build_targets_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    output_path: str | Path,
    output: str,
    horizon: int,
    lower_q: float,
    upper_q: float,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = build_targets(
        paths,
        output_path=output_path,
        horizon=horizon,
        lower_q=lower_q,
        upper_q=upper_q,
    )

    if output == "json":
        out = render_build_targets_json(res)
    else:
        out = render_build_targets_table(res)

    if res.ok:
        logger.info("build-targets: OK rows_in=%s rows_out=%s", res.rows_in, res.rows_out)
        return CommandResult(exit_code=0, output=out)

    logger.error("build-targets: FAILED")
    return CommandResult(exit_code=2, output=out)


def detect_regime_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    output_path: str | Path,
    output: str,
    vol_high_q: float,
    bb_width_high_q: float,
    liq_low_q: float,
    trend_strength_q: float,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = detect_regime_pipeline(
        paths,
        output_path=output_path,
        vol_high_q=vol_high_q,
        bb_width_high_q=bb_width_high_q,
        liq_low_q=liq_low_q,
        trend_strength_q=trend_strength_q,
    )

    if output == "json":
        out = render_detect_regime_json(res)
    else:
        out = render_detect_regime_table(res)

    if res.ok:
        logger.info("detect-regime: OK rows_in=%s rows_out=%s", res.rows_in, res.rows_out)
        return CommandResult(exit_code=0, output=out)

    logger.error("detect-regime: FAILED")
    return CommandResult(exit_code=2, output=out)


def run_strategy_sim_command(
    config_path: str | Path,
    *,
    input_path: str | Path,
    output_path: str | Path,
    report_path: str | Path,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    # Load as a single parquet file
    res_df = validate_data([input_path], write_registry=False)
    df = res_df.merge.df

    sim = run_strategy_sim(df, output_path=output_path, report_path=report_path)

    if output == "json":
        out = render_strategy_sim_json(sim)
    else:
        out = render_strategy_sim_table(sim)

    if sim.ok:
        logger.info("run-strategy-sim: OK rows=%s", sim.rows)
        return CommandResult(exit_code=0, output=out)

    logger.error("run-strategy-sim: FAILED")
    return CommandResult(exit_code=2, output=out)


def train_offline_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    output: str,
    target_col: str,
    train_frac: float,
    val_frac: float,
    alpha: float,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = train_offline(
        paths,
        target_col=target_col,
        train_frac=train_frac,
        val_frac=val_frac,
        alpha=alpha,
    )

    if output == "json":
        out = render_train_offline_json(res)
    else:
        out = render_train_offline_table(res)

    if res.ok:
        logger.info("train-offline: OK model_id=%s", res.model_id)
        return CommandResult(exit_code=0, output=out)

    logger.error("train-offline: FAILED")
    return CommandResult(exit_code=2, output=out)


def run_decision_engine_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    model_id: str,
    output_path: str | Path,
    report_path: str | Path,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = run_decision_engine(
        paths,
        model_id=model_id,
        output_path=output_path,
        report_path=report_path,
    )

    if output == "json":
        out = render_decision_engine_json(res)
    else:
        out = render_decision_engine_table(res)

    if res.ok:
        logger.info("run-decision-engine: OK rows=%s model_id=%s", res.rows, res.model_id)
        return CommandResult(exit_code=0, output=out)

    logger.error("run-decision-engine: FAILED")
    return CommandResult(exit_code=2, output=out)


def copy_trade_once_command(
    config_path: str | Path,
    *,
    signal_path: str | Path,
    allocation: float,
    max_leverage: float,
    fee_bps: float,
    slippage_bps: float,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = copy_trade_once(
        signal_path=signal_path,
        allocation=float(allocation),
        max_leverage=float(max_leverage),
        fee_bps=float(fee_bps),
        slippage_bps=float(slippage_bps),
    )

    if output == "json":
        out = render_copy_trade_json(res)
    else:
        out = render_copy_trade_table(res)

    if res.ok:
        logger.info("copy-trade-once: OK")
        return CommandResult(exit_code=0, output=out)

    logger.error("copy-trade-once: FAILED")
    return CommandResult(exit_code=2, output=out)


def paper_trade_once_command(
    config_path: str | Path,
    *,
    paths: list[str | Path],
    model_id: str,
    state_path: str | Path,
    report_path: str | Path,
    fee_bps: float,
    slippage_bps: float,
    lookback: int,
    require_eligible_row: bool,
    enforce_trade_validity: bool,
    position_mode: str,
    max_leverage: float | None,
    output: str,
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    res = paper_trade_once(
        paths,
        model_id=model_id,
        state_path=state_path,
        report_path=report_path,
        fee_bps=float(fee_bps),
        slippage_bps=float(slippage_bps),
        lookback=int(lookback),
        require_eligible_row=bool(require_eligible_row),
        enforce_trade_validity=bool(enforce_trade_validity),
        position_mode=str(position_mode),
        max_leverage=max_leverage,
    )

    def _jsonable(v):
        if v is None:
            return None
        if hasattr(v, "__dict__"):
            return dict(v.__dict__)
        return v

    payload = {
        "ok": bool(res.ok),
        "model_id": res.model_id,
        "used_row_index": int(res.used_row_index),
        "mid_price": float(res.mid_price),
        "y_hat": float(res.y_hat),
        "target_position": float(res.target_position),
        "executed": bool(res.executed),
        "fill": _jsonable(res.fill),
        "pre_trade_ok": bool(res.pre_trade_ok),
        "pre_trade_reasons": list(res.pre_trade_reasons),
        "post_trade_ok": bool(res.post_trade_ok),
        "post_trade_reasons": list(res.post_trade_reasons),
        "state_path": str(res.state_path),
        "report_path": str(res.report_path),
    }

    out = json.dumps(payload, ensure_ascii=False, indent=2)

    if res.ok:
        logger.info("paper-trade-once: OK executed=%s", res.executed)
        return CommandResult(exit_code=0, output=out)

    logger.error("paper-trade-once: FAILED")
    return CommandResult(exit_code=2, output=out)


def download_datasets_command(config_path: str | Path, *, sentiment_source: str | None) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")
    dl = DatasetDownloader()

    try:
        dl.download_price_datasets(overwrite=False)
    except Exception as e:
        logger.warning("download-datasets: price download skipped/failed: %s", e)

    if sentiment_source is not None:
        try:
            dl.download_sentiment_dataset(sentiment_source, overwrite=False)
        except Exception as e:
            logger.warning("download-datasets: sentiment download skipped/failed: %s", e)

    dl.verify_integrity()
    logger.info("download-datasets: OK")
    return CommandResult(exit_code=0, output=json.dumps(dl.dataset_status(), ensure_ascii=False, indent=2))


def verify_datasets_command(config_path: str | Path) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")
    dl = DatasetDownloader()
    dl.verify_integrity()
    logger.info("verify-datasets: OK")
    return CommandResult(exit_code=0, output=json.dumps(dl.dataset_status(), ensure_ascii=False, indent=2))


def dataset_status_command(config_path: str | Path) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")
    dl = DatasetDownloader()
    st = dl.dataset_status()
    if st.get("mandatory_ready"):
        logger.info("dataset-status: OK")
        return CommandResult(exit_code=0, output=json.dumps(st, ensure_ascii=False, indent=2))
    logger.error("dataset-status: MISSING")
    return CommandResult(exit_code=2, output=json.dumps(st, ensure_ascii=False, indent=2))


def aggregate_sentiment_command(config_path: str | Path, *, freq: str) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")
    res = aggregate_sentiment(freq=freq)
    logger.info("aggregate-sentiment: OK freq=%s", freq)
    return CommandResult(exit_code=0, output=json.dumps(res.__dict__, ensure_ascii=False, indent=2))


def _parse_utc_ts(s: str) -> "pd.Timestamp":
    import pandas as pd

    ts = pd.to_datetime(str(s), utc=True, errors="coerce")
    if ts is pd.NaT:
        raise BinanceAITraderError(f"Invalid timestamp: {s}")
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts


def download_price_5m_command(
    config_path: str | Path,
    *,
    start: str,
    end: str,
    symbol: str = "BTCUSDT",
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    import pandas as pd

    start_ts = _parse_utc_ts(start)
    end_ts = _parse_utc_ts(end)
    res = download_binance_futures_price_5m(symbol=symbol, start_ts=start_ts, end_ts=end_ts)
    logger.info("download-price-5m: OK rows=%s", res.get("rows"))
    return CommandResult(exit_code=0, output=json.dumps(res, ensure_ascii=False, indent=2))


def download_funding_5m_command(
    config_path: str | Path,
    *,
    start: str,
    end: str,
    symbol: str = "BTCUSDT",
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    start_ts = _parse_utc_ts(start)
    end_ts = _parse_utc_ts(end)
    res = download_funding_rate_5m(symbol=symbol, start_ts=start_ts, end_ts=end_ts)
    logger.info("download-funding-5m: OK rows=%s", res.get("rows"))
    return CommandResult(exit_code=0, output=json.dumps(res, ensure_ascii=False, indent=2))


def download_oi_5m_command(
    config_path: str | Path,
    *,
    start: str,
    end: str,
    symbol: str = "BTCUSDT",
) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    start_ts = _parse_utc_ts(start)
    end_ts = _parse_utc_ts(end)
    res = download_open_interest_5m(symbol=symbol, start_ts=start_ts, end_ts=end_ts)
    logger.info("download-oi-5m: OK rows=%s", res.get("rows"))
    return CommandResult(exit_code=0, output=json.dumps(res, ensure_ascii=False, indent=2))


def verify_datasets_5m_command(config_path: str | Path) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    import pandas as pd

    price_p = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet"
    fund_p = Path("ai_data") / "derivatives" / "funding_rate_5m.parquet"
    oi_p = Path("ai_data") / "derivatives" / "open_interest_5m.parquet"
    sent_p = Path("ai_data") / "sentiment" / "aggregated" / "sentiment_5m.parquet"

    price_card = Path("ai_data") / "dataset_registry" / "price_binance_5m.json"
    fund_card = Path("ai_data") / "dataset_registry" / "funding_rate_5m.json"
    oi_card = Path("ai_data") / "dataset_registry" / "open_interest_5m.json"
    sent_card = Path("ai_data") / "dataset_registry" / "sentiment_5m.json"

    missing: list[str] = []
    for p in [price_p, fund_p, oi_p, sent_p]:
        if not p.exists():
            missing.append(str(p))
    for p in [price_card, fund_card, oi_card, sent_card]:
        if not p.exists():
            missing.append(str(p))
    if missing:
        raise BinanceAITraderError(f"Missing mandatory 5m datasets/cards: {missing}")

    price_df = pd.read_parquet(price_p)
    fund_df = pd.read_parquet(fund_p)
    oi_df = pd.read_parquet(oi_p)
    sent_df = pd.read_parquet(sent_p)

    validate_price_5m(price_df, coverage_min=0.99)
    validate_funding_rate_5m(fund_df, nan_max_ratio=0.01)
    validate_open_interest_5m(oi_df, nan_max_ratio=0.01)

    validate_sentiment_agg_5m(sent_df, nan_max_ratio=0.01)

    payload = {
        "ok": True,
        "price_path": str(price_p),
        "funding_path": str(fund_p),
        "open_interest_path": str(oi_p),
        "sentiment_path": str(sent_p),
    }
    logger.info("verify-datasets-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(payload, ensure_ascii=False, indent=2))


def dataset_status_5m_command(config_path: str | Path) -> CommandResult:
    cfg = load_config(config_path)
    logger = setup_logger("binance_ai_trader.cli")

    price_p = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet"
    fund_p = Path("ai_data") / "derivatives" / "funding_rate_5m.parquet"
    oi_p = Path("ai_data") / "derivatives" / "open_interest_5m.parquet"
    sent_p = Path("ai_data") / "sentiment" / "aggregated" / "sentiment_5m.parquet"

    def _read_card(path: Path) -> dict | None:
        try:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _sha256_file(path: Path) -> str:
        import hashlib

        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _enrich_meta(meta: dict | None, *, parquet_path: Path, freq: str) -> dict | None:
        # Do not write/overwrite anything; only enrich the returned status payload.
        out = dict(meta or {})
        if parquet_path.exists():
            try:
                if "columns" not in out:
                    import pandas as pd

                    cols = list(pd.read_parquet(parquet_path, engine="pyarrow").columns)
                    out["columns"] = cols
            except Exception:
                pass

            try:
                if "sha256" not in out:
                    out["sha256"] = _sha256_file(parquet_path)
                if "hash" not in out and "sha256" in out:
                    out["hash"] = f"sha256:{out['sha256']}"
            except Exception:
                pass

        out.setdefault("frequency", str(freq))
        return out

    price_card = Path("ai_data") / "dataset_registry" / "price_binance_5m.json"
    fund_card = Path("ai_data") / "dataset_registry" / "funding_rate_5m.json"
    oi_card = Path("ai_data") / "dataset_registry" / "open_interest_5m.json"
    sent_card = Path("ai_data") / "dataset_registry" / "sentiment_5m.json"

    st = {
        "price": {
            "path": str(price_p),
            "exists": bool(price_p.exists()),
            "card": str(price_card),
            "card_exists": bool(price_card.exists()),
            "meta": _enrich_meta(_read_card(price_card), parquet_path=price_p, freq="5m"),
        },
        "derivatives": {
            "funding_rate": {
                "path": str(fund_p),
                "exists": bool(fund_p.exists()),
                "card": str(fund_card),
                "card_exists": bool(fund_card.exists()),
                "meta": _enrich_meta(_read_card(fund_card), parquet_path=fund_p, freq="5m"),
            },
            "open_interest": {
                "path": str(oi_p),
                "exists": bool(oi_p.exists()),
                "card": str(oi_card),
                "card_exists": bool(oi_card.exists()),
                "meta": _enrich_meta(_read_card(oi_card), parquet_path=oi_p, freq="5m"),
            },
        },
        "sentiment": {
            "path": str(sent_p),
            "exists": bool(sent_p.exists()),
            "card": str(sent_card),
            "card_exists": bool(sent_card.exists()),
            "meta": _enrich_meta(_read_card(sent_card), parquet_path=sent_p, freq="5m"),
        },
    }

    logger.info("dataset-status-5m: OK")
    return CommandResult(exit_code=0, output=json.dumps(st, ensure_ascii=False, indent=2))
