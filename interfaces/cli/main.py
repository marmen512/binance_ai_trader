from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.exceptions import BinanceAITraderError
from interfaces.cli.features_5m_commands import (
    build_features_5m_command,
    feature_status_5m_command,
    verify_features_5m_command,
)
from interfaces.cli.targets_5m_commands import (
    build_targets_5m_command,
    target_status_5m_command,
    verify_targets_5m_command,
)
from interfaces.cli.training_5m_commands import (
    train_xgb_5m_command,
    training_status_5m_command,
)
from interfaces.cli.signals_5m_commands import (
    build_signals_5m_command,
    signal_status_5m_command,
    verify_signals_5m_command,
)
from interfaces.cli.executions_5m_commands import (
    build_executions_5m_command,
    execution_status_5m_command,
    verify_executions_5m_command,
)
from interfaces.cli.backtest_5m_commands import (
    backtest_status_5m_command,
    run_backtest_5m_command,
    verify_backtest_5m_command,
)
from interfaces.cli.paper_gate_5m_commands import (
    paper_gate_5m_command,
    paper_status_5m_command,
)
from interfaces.cli.paper_trading_commands import (
    evaluate_paper_trades_command,
    convert_replay_to_instruction_command,
    offline_finetune_command,
    correct_policy_command,
    create_policy_correction_dataset_command,
    create_good_trade_reinforcement_command,
    analyze_weighting_system_command,
)
from interfaces.cli.commands import (
    aggregate_sentiment_command,
    build_features_command,
    build_targets_command,
    copy_trade_once_command,
    dataset_status_5m_command,
    dataset_status_command,
    detect_regime_command,
    download_funding_5m_command,
    download_datasets_command,
    download_oi_5m_command,
    download_price_5m_command,
    doctor,
    health_check,
    paper_trade_command,
    paper_trade_live_once_command,
    paper_trade_once_command,
    paper_sanity_report_command,
    train_command,
    verify_datasets_command,
    verify_datasets_5m_command,
    run_decision_engine_command,
    run_strategy_sim_command,
    train_offline_command,
    validate_data_command,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="binance_ai_trader")
    p.add_argument(
        "--config",
        default=str(Path("config") / "config.yaml"),
        help="Path to config.yaml",
    )

    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("health-check", help="Run dependency checks and config load")
    sub.add_parser("doctor", help="Alias for health-check")

    dd = sub.add_parser("download-datasets", help="Download mandatory datasets (price + optional sentiment)")
    dd.add_argument(
        "--sentiment",
        choices=("tweets", "news"),
        default=None,
        help="Optional: download ONE sentiment dataset",
    )

    dp = sub.add_parser("download-price-5m", help="Download Binance Futures BTCUSDT 5m klines to ai_data/price")
    dp.add_argument("--start", required=True, help="UTC start timestamp (e.g. 2024-01-01T00:00:00Z)")
    dp.add_argument("--end", required=True, help="UTC end timestamp (e.g. 2024-02-01T00:00:00Z)")
    dp.add_argument("--symbol", default="BTCUSDT")

    df = sub.add_parser("download-funding-5m", help="Download Binance Futures funding rate and align to 5m grid")
    df.add_argument("--start", required=True, help="UTC start timestamp")
    df.add_argument("--end", required=True, help="UTC end timestamp")
    df.add_argument("--symbol", default="BTCUSDT")

    doi = sub.add_parser("download-oi-5m", help="Download Binance Futures open interest history (5m)")
    doi.add_argument("--start", required=True, help="UTC start timestamp")
    doi.add_argument("--end", required=True, help="UTC end timestamp")
    doi.add_argument("--symbol", default="BTCUSDT")

    sub.add_parser("verify-datasets", help="Verify mandatory datasets integrity")
    sub.add_parser("dataset-status", help="Show dataset presence and readiness")

    sub.add_parser("verify-datasets-5m", help="Verify mandatory 5m datasets integrity")
    sub.add_parser("dataset-status-5m", help="Show 5m dataset presence and readiness")

    ag = sub.add_parser("aggregate-sentiment", help="Aggregate sentiment raw into 1h/4h/1d features")
    ag.add_argument("--freq", choices=("5m", "1h", "4h", "1d"), required=True)

    v = sub.add_parser("validate-data", help="Validate OHLCV parquet dataset(s)")
    v.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    v.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )
    v.add_argument(
        "--no-registry",
        action="store_true",
        help="Do not write dataset card into ai_data/data_registry",
    )

    b = sub.add_parser("build-features", help="Build feature dataset from OHLCV parquet")
    b.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    b.add_argument(
        "--output-path",
        required=True,
        help="Path to output parquet file",
    )
    b.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    sub.add_parser("build-features-5m", help="Build canonical 5m feature dataset (<=15 features)")
    sub.add_parser("verify-features-5m", help="Verify canonical 5m feature dataset integrity")
    sub.add_parser("feature-status-5m", help="Show 5m feature dataset status and metadata")

    sub.add_parser("build-targets-5m", help="Build canonical 5m direction targets (horizon=3)")
    sub.add_parser("verify-targets-5m", help="Verify canonical 5m target dataset integrity")
    sub.add_parser("target-status-5m", help="Show 5m target dataset status and metadata")

    sub.add_parser("train-xgb-5m", help="Train 5m XGBoost classifier (signal model only)")
    sub.add_parser("training-status-5m", help="Show 5m training artifacts status")

    sub.add_parser("build-signals-5m", help="Build 5m signals from XGBoost softprob (SELL/HOLD/BUY)")
    sub.add_parser("verify-signals-5m", help="Verify canonical 5m signal dataset integrity")
    sub.add_parser("signal-status-5m", help="Show 5m signal dataset status and metadata")

    sub.add_parser("build-executions-5m", help="Build paper-only 5m executions from signals (state machine)")
    sub.add_parser("verify-executions-5m", help="Verify paper-only 5m executions dataset integrity")
    sub.add_parser("execution-status-5m", help="Show 5m executions dataset status and metadata")

    sub.add_parser("run-backtest-5m", help="Run one-pass walk-forward backtest on executions (5m)")
    sub.add_parser("backtest-status-5m", help="Show 5m backtest artifacts status")
    sub.add_parser("verify-backtest-5m", help="Verify 5m backtest outputs integrity")

    sub.add_parser("paper-gate-5m", help="Evaluate 5m paper-trading GO/NO-GO gate")
    sub.add_parser("paper-status-5m", help="Show 5m paper readiness status")

    ept = sub.add_parser("evaluate-paper-trades", help="Evaluate completed paper trades with deterministic rules")
    ept.add_argument("--replay-path", default="ai_data/paper/replay.jsonl", help="Path to replay buffer")
    ept.add_argument("--output-path", default="ai_data/paper/evaluations.json", help="Output path for evaluations")

    cri = sub.add_parser("convert-replay-to-instruction", help="Convert replay trades to instruction dataset")
    cri.add_argument("--replay-path", default="ai_data/paper/replay.jsonl", help="Path to replay buffer")
    cri.add_argument("--output-path", default="ai_data/trading/instruction_dataset.jsonl", help="Output path")
    cri.add_argument("--max-samples", type=int, default=None, help="Maximum samples to generate")
    cri.add_argument("--stable-path", default=None, help="Path to stable instruction dataset for mixing")
    cri.add_argument("--mix-ratio", type=float, default=0.3, help="Ratio of replay data in mixed dataset")

    oft = sub.add_parser("offline-finetune", help="Offline fine-tuning for LLM trading agent")
    oft.add_argument("--train-path", required=True, help="Training data path")
    oft.add_argument("--model-name", default="microsoft/DialoGPT-medium", help="Base model name")
    oft.add_argument("--val-path", default=None, help="Validation data path")
    oft.add_argument("--output-dir", default="ai_data/models/llm_trader", help="Output directory")
    oft.add_argument("--learning-rate", type=float, default=1e-5, help="Learning rate")
    oft.add_argument("--batch-size", type=int, default=4, help="Batch size")
    oft.add_argument("--num-epochs", type=int, default=3, help="Number of epochs")

    cpc = sub.add_parser("correct-policy", help="Generate policy corrections from evaluated trades")
    cpc.add_argument("--replay-path", default="ai_data/paper/replay.jsonl", help="Path to replay buffer")
    cpc.add_argument("--evaluations-path", default="ai_data/paper/evaluations.json", help="Path to trade evaluations")
    cpc.add_argument("--output-path", default="ai_data/paper/corrections.json", help="Output path for corrections")

    pcd = sub.add_parser("create-policy-correction-dataset", help="Create weighted policy correction training dataset")
    pcd.add_argument("--replay-path", default="ai_data/paper/replay.jsonl", help="Path to replay buffer")
    pcd.add_argument("--output-path", default="ai_data/trading/policy_corrections.jsonl", help="Output path")
    pcd.add_argument("--correction-ratio", type=float, default=1.0, help="Ratio of corrections to include")
    pcd.add_argument("--stable-path", default=None, help="Path to stable instruction dataset for mixing")
    pcd.add_argument("--policy-weight", type=float, default=2.0, help="Weight for policy corrections")
    pcd.add_argument("--stable-weight", type=float, default=1.0, help="Weight for stable instructions")
    pcd.add_argument("--anti-hold-weight", type=float, default=1.5, help="Weight for anti-HOLD entries")
    pcd.add_argument("--comprehensive", action="store_true", help="Create comprehensive dataset with policy corrections and anti-HOLD")

    gtr = sub.add_parser("create-good-trade-reinforcement", help="Create GOOD-trade reinforcement dataset")
    gtr.add_argument("--replay-path", default="ai_data/paper/replay.jsonl", help="Path to replay buffer")
    gtr.add_argument("--output-path", default="ai_data/trading/good_trade_reinforcement.jsonl", help="Output path")
    gtr.add_argument("--sample-ratio", type=float, default=1.0, help="Ratio of GOOD trades to include")

    aws = sub.add_parser("analyze-weighting-system", help="Analyze the advanced weighting system configuration")
    aws.add_argument("--replay-path", default="ai_data/paper/replay.jsonl", help="Path to replay buffer (for analysis)")

    t = sub.add_parser("build-targets", help="Build targets dataset from OHLCV/feature parquet")
    t.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    t.add_argument(
        "--output-path",
        required=True,
        help="Path to output parquet file",
    )
    t.add_argument(
        "--horizon",
        type=int,
        default=1,
        help="Prediction horizon in bars (future shift)",
    )
    t.add_argument(
        "--lower-q",
        type=float,
        default=0.33,
        help="Lower quantile threshold for DOWN",
    )
    t.add_argument(
        "--upper-q",
        type=float,
        default=0.66,
        help="Upper quantile threshold for UP",
    )
    t.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    r = sub.add_parser("detect-regime", help="Detect market regime labels")
    r.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    r.add_argument(
        "--output-path",
        required=True,
        help="Path to output parquet file",
    )
    r.add_argument(
        "--vol-high-q",
        type=float,
        default=0.80,
        help="Quantile for HIGH_VOL volatility threshold",
    )
    r.add_argument(
        "--bb-width-high-q",
        type=float,
        default=0.80,
        help="Quantile for HIGH_VOL Bollinger width threshold",
    )
    r.add_argument(
        "--liq-low-q",
        type=float,
        default=0.10,
        help="Quantile for LOW_LIQUIDITY volume z-score threshold",
    )
    r.add_argument(
        "--trend-strength-q",
        type=float,
        default=0.70,
        help="Quantile for TREND strength threshold based on |macd_hist|",
    )
    r.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    s = sub.add_parser("run-strategy-sim", help="Run regime-routed strategy simulation")
    s.add_argument(
        "--input",
        required=True,
        help="Path to input parquet file (features + regime labels)",
    )
    s.add_argument(
        "--output-path",
        required=True,
        help="Path to output parquet file with strategy outputs",
    )
    s.add_argument(
        "--report-path",
        required=True,
        help="Path to output JSON report",
    )
    s.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    tr = sub.add_parser("train-offline", help="Train offline model (time-series split)")
    tr.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    tr.add_argument(
        "--target-col",
        default="future_log_return",
        help="Target column name",
    )
    tr.add_argument(
        "--train-frac",
        type=float,
        default=0.70,
        help="Train fraction (time-series)",
    )
    tr.add_argument(
        "--val-frac",
        type=float,
        default=0.15,
        help="Validation fraction (time-series)",
    )
    tr.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="Ridge regularization strength",
    )
    tr.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    tr2 = sub.add_parser("train", help="Train 1h classifier model (LONG/SHORT/FLAT) with TensorBoard logs")
    tr2.add_argument("--timeframe", choices=("1h",), required=True)
    tr2.add_argument("--model-name", default="clf_1h")
    tr2.add_argument("--sentiment-freq", choices=("1h", "4h", "1d"), default=None)
    tr2.add_argument("--epochs", type=int, default=10)
    tr2.add_argument("--batch-size", type=int, default=512)
    tr2.add_argument("--lr", type=float, default=1e-3)
    tr2.add_argument("--hidden-dim", type=int, default=128)
    tr2.add_argument("--dropout", type=float, default=0.10)
    tr2.add_argument("--seed", type=int, default=42)
    tr2.add_argument(
        "--output",
        choices=("table", "json"),
        default="json",
        help="Output format",
    )

    pl = sub.add_parser("paper-trade", help="Run offline paper trading loop on a parquet (1h candle-close simulation)")
    pl.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    pl.add_argument("--pair", default="BTCUSDT")
    pl.add_argument("--model-id", required=True)
    pl.add_argument("--deposit", type=float, default=10_000.0)
    pl.add_argument("--max-leverage", type=float, default=1.0)
    pl.add_argument("--fee-bps", type=float, default=1.0)
    pl.add_argument("--slippage-bps", type=float, default=1.0)
    pl.add_argument("--start-index", type=int, default=0)
    pl.add_argument("--max-steps", type=int, default=None)
    pl.add_argument("--reset-state", action="store_true")
    pl.add_argument("--classifier-min-conf", type=float, default=0.45)
    pl.add_argument("--no-enforce-trade-validity", action="store_true")
    pl.add_argument(
        "--output",
        choices=("table", "json"),
        default="json",
        help="Output format",
    )

    de = sub.add_parser("run-decision-engine", help="Run model inference + risk-aware decision engine")
    de.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    de.add_argument(
        "--model-id",
        required=True,
        help="Model ID from model_registry/model_cards (e.g. m_...)" ,
    )
    de.add_argument(
        "--output-path",
        required=True,
        help="Path to output parquet file with predictions/positions",
    )
    de.add_argument(
        "--report-path",
        required=True,
        help="Path to output JSON report",
    )
    de.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    ct = sub.add_parser("copy-trade-once", help="Run a copy-trading step from an expert signal JSON")
    ct.add_argument(
        "--signal-path",
        required=True,
        help="Path to expert signal JSON (e.g. ai_data/copy/signals/demo.json)",
    )
    ct.add_argument(
        "--allocation",
        type=float,
        default=1.0,
        help="Follower allocation multiplier applied to expert target_position",
    )
    ct.add_argument(
        "--max-leverage",
        type=float,
        default=1.0,
        help="Max leverage cap for follower target position",
    )
    ct.add_argument(
        "--fee-bps",
        type=float,
        default=1.0,
        help="Fee in basis points",
    )
    ct.add_argument(
        "--slippage-bps",
        type=float,
        default=1.0,
        help="Slippage in basis points",
    )
    ct.add_argument(
        "--output",
        choices=("table", "json"),
        default="table",
        help="Output format",
    )

    pt = sub.add_parser("paper-trade-once", help="Run a single paper trading step")
    pt.add_argument(
        "--input",
        dest="inputs",
        action="append",
        required=True,
        help="Path to input parquet file (repeatable)",
    )
    pt.add_argument("--model-id", required=True)
    pt.add_argument(
        "--state-path",
        default=str(Path("ai_data") / "paper" / "state.json"),
    )
    pt.add_argument(
        "--report-path",
        default=str(Path("ai_data") / "paper" / "last_trade.json"),
    )
    pt.add_argument("--fee-bps", type=float, default=1.0)
    pt.add_argument("--slippage-bps", type=float, default=1.0)
    pt.add_argument("--lookback", type=int, default=200)
    pt.add_argument("--no-require-eligible-row", action="store_true")
    pt.add_argument("--no-enforce-trade-validity", action="store_true")
    pt.add_argument("--position-mode", default="risk_scaled")
    pt.add_argument("--max-leverage", type=float, default=None)
    pt.add_argument(
        "--output",
        choices=("table", "json"),
        default="json",
        help="Output format",
    )

    ptl = sub.add_parser("paper-trade-live", help="Run live paper trading against Binance klines (read-only data fetch)")
    ptl.add_argument("--once", action="store_true")
    ptl.add_argument("--pair", default="BTCUSDT")
    ptl.add_argument("--model-id", required=True)
    ptl.add_argument("--deposit", type=float, default=10_000.0)
    ptl.add_argument("--max-leverage", type=float, default=1.0)
    ptl.add_argument("--fee-bps", type=float, default=1.0)
    ptl.add_argument("--slippage-bps", type=float, default=1.0)
    ptl.add_argument("--reset-state", action="store_true")
    ptl.add_argument("--classifier-min-conf", type=float, default=0.45)
    ptl.add_argument("--cooldown-candles", type=int, default=1)
    ptl.add_argument("--no-enforce-trade-validity", action="store_true")
    ptl.add_argument("--fetch-limit", type=int, default=300)
    ptl.add_argument(
        "--output",
        choices=("table", "json"),
        default="json",
        help="Output format",
    )

    psr = sub.add_parser("paper-sanity-report", help="Sanity-check paper equity vs a simple replay backtest")
    psr.add_argument("--session-id", default=None)
    psr.add_argument("--limit-rows", type=int, default=2000)
    psr.add_argument(
        "--output",
        choices=("table", "json"),
        default="json",
        help="Output format",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "health-check":
            res = health_check(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "paper-trade":
            res = paper_trade_command(
                args.config,
                paths=args.inputs,
                pair=args.pair,
                model_id=args.model_id,
                deposit=args.deposit,
                max_leverage=args.max_leverage,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                enforce_trade_validity=not args.no_enforce_trade_validity,
                start_index=args.start_index,
                max_steps=args.max_steps,
                reset_state=args.reset_state,
                classifier_min_conf=args.classifier_min_conf,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "paper-trade-once":
            res = paper_trade_once_command(
                args.config,
                paths=args.inputs,
                model_id=args.model_id,
                state_path=args.state_path,
                report_path=args.report_path,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                lookback=args.lookback,
                require_eligible_row=not args.no_require_eligible_row,
                enforce_trade_validity=not args.no_enforce_trade_validity,
                position_mode=args.position_mode,
                max_leverage=args.max_leverage,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "paper-trade-live":
            if not args.once:
                raise ValueError("Only --once is supported for paper-trade-live")

            res = paper_trade_live_once_command(
                args.config,
                pair=args.pair,
                model_id=args.model_id,
                deposit=args.deposit,
                max_leverage=args.max_leverage,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                reset_state=args.reset_state,
                enforce_trade_validity=not args.no_enforce_trade_validity,
                classifier_min_conf=args.classifier_min_conf,
                cooldown_candles=args.cooldown_candles,
                fetch_limit=args.fetch_limit,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "doctor":
            res = doctor(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "paper-sanity-report":
            res = paper_sanity_report_command(
                args.config,
                session_id=args.session_id,
                limit_rows=args.limit_rows,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "download-datasets":
            res = download_datasets_command(args.config, sentiment_source=args.sentiment)
            print(res.output)
            return res.exit_code

        if args.command == "download-price-5m":
            res = download_price_5m_command(args.config, start=args.start, end=args.end, symbol=args.symbol)
            print(res.output)
            return res.exit_code

        if args.command == "download-funding-5m":
            res = download_funding_5m_command(args.config, start=args.start, end=args.end, symbol=args.symbol)
            print(res.output)
            return res.exit_code

        if args.command == "download-oi-5m":
            res = download_oi_5m_command(args.config, start=args.start, end=args.end, symbol=args.symbol)
            print(res.output)
            return res.exit_code

        if args.command == "verify-datasets":
            res = verify_datasets_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "verify-datasets-5m":
            res = verify_datasets_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "dataset-status":
            res = dataset_status_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "dataset-status-5m":
            res = dataset_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "aggregate-sentiment":
            res = aggregate_sentiment_command(args.config, freq=args.freq)
            print(res.output)
            return res.exit_code

        if args.command == "validate-data":
            res = validate_data_command(
                args.config,
                paths=args.inputs,
                output=args.output,
                write_registry=not args.no_registry,
            )
            print(res.output)
            return res.exit_code

        if args.command == "build-features":
            res = build_features_command(
                args.config,
                paths=args.inputs,
                output_path=args.output_path,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "build-features-5m":
            res = build_features_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "verify-features-5m":
            res = verify_features_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "feature-status-5m":
            res = feature_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "build-targets-5m":
            res = build_targets_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "verify-targets-5m":
            res = verify_targets_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "target-status-5m":
            res = target_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "train-xgb-5m":
            res = train_xgb_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "training-status-5m":
            res = training_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "build-signals-5m":
            res = build_signals_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "verify-signals-5m":
            res = verify_signals_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "signal-status-5m":
            res = signal_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "build-executions-5m":
            res = build_executions_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "verify-executions-5m":
            res = verify_executions_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "execution-status-5m":
            res = execution_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "run-backtest-5m":
            res = run_backtest_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "backtest-status-5m":
            res = backtest_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "verify-backtest-5m":
            res = verify_backtest_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "paper-gate-5m":
            res = paper_gate_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "paper-status-5m":
            res = paper_status_5m_command(args.config)
            print(res.output)
            return res.exit_code

        if args.command == "evaluate-paper-trades":
            res = evaluate_paper_trades_command(
                replay_path=args.replay_path,
                output_path=args.output_path
            )
            print(res.output)
            return res.exit_code

        if args.command == "convert-replay-to-instruction":
            res = convert_replay_to_instruction_command(
                replay_path=args.replay_path,
                output_path=args.output_path,
                max_samples=args.max_samples,
                stable_path=args.stable_path,
                mix_ratio=args.mix_ratio
            )
            print(res.output)
            return res.exit_code

        if args.command == "offline-finetune":
            res = offline_finetune_command(
                train_path=args.train_path,
                model_name=args.model_name,
                val_path=args.val_path,
                output_dir=args.output_dir,
                learning_rate=args.learning_rate,
                batch_size=args.batch_size,
                num_epochs=args.num_epochs
            )
            print(res.output)
            return res.exit_code

        if args.command == "correct-policy":
            res = correct_policy_command(
                replay_path=args.replay_path,
                evaluations_path=args.evaluations_path,
                output_path=args.output_path
            )
            print(res.output)
            return res.exit_code

        if args.command == "create-policy-correction-dataset":
            res = create_policy_correction_dataset_command(
                replay_path=args.replay_path,
                output_path=args.output_path,
                correction_ratio=args.correction_ratio,
                stable_path=args.stable_path,
                policy_weight=args.policy_weight,
                stable_weight=args.stable_weight,
                anti_hold_weight=getattr(args, 'anti_hold_weight', 1.5),
                comprehensive=getattr(args, 'comprehensive', False)
            )
            print(res.output)
            return res.exit_code

        if args.command == "create-good-trade-reinforcement":
            res = create_good_trade_reinforcement_command(
                replay_path=args.replay_path,
                output_path=args.output_path,
                sample_ratio=getattr(args, 'sample_ratio', 1.0)
            )
            print(res.output)
            return res.exit_code

        if args.command == "analyze-weighting-system":
            res = analyze_weighting_system_command(
                replay_path=getattr(args, 'replay_path', "ai_data/paper/replay.jsonl")
            )
            print(res.output)
            return res.exit_code

        if args.command == "build-targets":
            res = build_targets_command(
                args.config,
                paths=args.inputs,
                output_path=args.output_path,
                output=args.output,
                horizon=args.horizon,
                lower_q=args.lower_q,
                upper_q=args.upper_q,
            )
            print(res.output)
            return res.exit_code

        if args.command == "detect-regime":
            res = detect_regime_command(
                args.config,
                paths=args.inputs,
                output_path=args.output_path,
                output=args.output,
                vol_high_q=args.vol_high_q,
                bb_width_high_q=args.bb_width_high_q,
                liq_low_q=args.liq_low_q,
                trend_strength_q=args.trend_strength_q,
            )
            print(res.output)
            return res.exit_code

        if args.command == "run-strategy-sim":
            res = run_strategy_sim_command(
                args.config,
                input_path=args.input,
                output_path=args.output_path,
                report_path=args.report_path,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "train-offline":
            res = train_offline_command(
                args.config,
                paths=args.inputs,
                output=args.output,
                target_col=args.target_col,
                train_frac=args.train_frac,
                val_frac=args.val_frac,
                alpha=args.alpha,
            )
            print(res.output)
            return res.exit_code

        if args.command == "train":
            res = train_command(
                args.config,
                timeframe=args.timeframe,
                model_name=args.model_name,
                sentiment_freq=args.sentiment_freq,
                epochs=args.epochs,
                batch_size=args.batch_size,
                lr=args.lr,
                hidden_dim=args.hidden_dim,
                dropout=args.dropout,
                seed=args.seed,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "run-decision-engine":
            res = run_decision_engine_command(
                args.config,
                paths=args.inputs,
                model_id=args.model_id,
                output_path=args.output_path,
                report_path=args.report_path,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        if args.command == "copy-trade-once":
            res = copy_trade_once_command(
                args.config,
                signal_path=args.signal_path,
                allocation=args.allocation,
                max_leverage=args.max_leverage,
                fee_bps=args.fee_bps,
                slippage_bps=args.slippage_bps,
                output=args.output,
            )
            print(res.output)
            return res.exit_code

        raise BinanceAITraderError(f"Unknown command: {args.command}")
    except BinanceAITraderError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
