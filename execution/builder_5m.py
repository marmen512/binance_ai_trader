from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from core.exceptions import BinanceAITraderError


@dataclass(frozen=True)
class BuildExecutions5mResult:
    ok: bool
    rows_in: int
    trades_out: int
    output_path: str


def build_executions_5m(
    *,
    signals_path: str | Path = Path("ai_data") / "signals" / "signals_5m.parquet",
    price_path: str | Path = Path("ai_data") / "price" / "binance_futures_btcusdt_5m.parquet",
    features_path: str | Path = Path("ai_data") / "features" / "features_5m.parquet",
    output_path: str | Path = Path("ai_data") / "executions" / "executions_5m.parquet",
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.0002,
    atr_col: str = "atr_14",
    sl_mult: float = 0.5,
    tp_mult: float = 1.0,
    max_holding_candles: int = 6,
) -> BuildExecutions5mResult:
    if float(fee_pct) != 0.0004:
        raise BinanceAITraderError("Execution contract requires fee_pct=0.0004 (0.04% per side)")
    if float(slippage_pct) != 0.0002:
        raise BinanceAITraderError("Execution contract requires slippage_pct=0.0002 (0.02% per side)")
    if float(sl_mult) != 0.5:
        raise BinanceAITraderError("Execution contract requires SL=0.5*ATR")
    if float(tp_mult) != 1.0:
        raise BinanceAITraderError("Execution contract requires TP=1.0*ATR")
    if int(max_holding_candles) != 6:
        raise BinanceAITraderError("Execution contract requires max_holding_candles=6")

    signals_path = Path(signals_path)
    price_path = Path(price_path)
    features_path = Path(features_path)
    output_path = Path(output_path)

    if not signals_path.exists():
        raise BinanceAITraderError(f"Missing signals_5m parquet: {signals_path}")
    if not price_path.exists():
        raise BinanceAITraderError(f"Missing price_5m parquet: {price_path}")
    if not features_path.exists():
        raise BinanceAITraderError(f"Missing features_5m parquet: {features_path}")

    if output_path.exists():
        raise BinanceAITraderError(f"Refusing to overwrite existing executions: {output_path}")

    sig = pd.read_parquet(signals_path)
    price = pd.read_parquet(price_path)
    feat = pd.read_parquet(features_path)

    for df, name in [(sig, "signals"), (price, "price"), (feat, "features")]:
        if "timestamp" not in df.columns:
            raise BinanceAITraderError(f"{name} parquet missing required column: timestamp")

    if "signal" not in sig.columns:
        raise BinanceAITraderError("signals parquet missing required column: signal")

    for c in ["open", "high", "low", "close"]:
        if c not in price.columns:
            raise BinanceAITraderError(f"price parquet missing required column: {c}")

    if atr_col not in feat.columns:
        raise BinanceAITraderError(f"features parquet missing required ATR column: {atr_col}")

    sig_ts = pd.to_datetime(sig["timestamp"], utc=True, errors="coerce")
    price_ts = pd.to_datetime(price["timestamp"], utc=True, errors="coerce")
    feat_ts = pd.to_datetime(feat["timestamp"], utc=True, errors="coerce")

    if sig_ts.isna().any() or price_ts.isna().any() or feat_ts.isna().any():
        raise BinanceAITraderError("Invalid timestamps in one of signals/price/features")

    sig2 = sig.copy()
    sig2["timestamp"] = sig_ts
    sig2 = sig2[["timestamp", "signal"]].sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")

    price2 = price.copy()
    price2["timestamp"] = price_ts
    price2 = price2[["timestamp", "open", "high", "low", "close"]].sort_values("timestamp").drop_duplicates(
        subset=["timestamp"], keep="last"
    )

    feat2 = feat.copy()
    feat2["timestamp"] = feat_ts
    feat2 = feat2[["timestamp", atr_col]].sort_values("timestamp").drop_duplicates(subset=["timestamp"], keep="last")

    # Strict alignment: require signals and features timestamps to exist in price
    merged = sig2.merge(price2, on="timestamp", how="left").merge(feat2, on="timestamp", how="left")
    if merged[["open", "high", "low", "close", atr_col]].isna().any().any():
        raise BinanceAITraderError("Missing required price/features values for some timestamps")

    merged = merged.sort_values("timestamp").reset_index(drop=True)

    signals = merged["signal"].astype(int).to_numpy(dtype=np.int64)
    o = merged["open"].astype(float).to_numpy()
    h = merged["high"].astype(float).to_numpy()
    l = merged["low"].astype(float).to_numpy()
    c = merged["close"].astype(float).to_numpy()
    atr = merged[atr_col].astype(float).to_numpy()
    ts = merged["timestamp"].to_numpy()

    if not np.isfinite(np.vstack([o, h, l, c, atr]).T).all():
        raise BinanceAITraderError("Non-finite values in price/features")

    trades: list[dict] = []

    state = "FLAT"  # FLAT, LONG, SHORT
    entry_i: int | None = None
    entry_price: float | None = None
    side: str | None = None

    for i in range(len(merged)):
        if state == "FLAT":
            if signals[i] == 1:
                state = "LONG"
                entry_i = i
                entry_price = float(c[i])
                side = "LONG"
            elif signals[i] == -1:
                state = "SHORT"
                entry_i = i
                entry_price = float(c[i])
                side = "SHORT"
            else:
                continue

            continue

        # In position: evaluate next candles only
        if entry_i is None or entry_price is None or side is None:
            raise BinanceAITraderError("Internal state error: missing entry")

        holding = i - entry_i
        if holding <= 0:
            continue

        if holding > max_holding_candles:
            raise BinanceAITraderError("Internal state error: holding exceeded max")

        sl_dist = float(sl_mult) * float(atr[entry_i])
        tp_dist = float(tp_mult) * float(atr[entry_i])

        if sl_dist <= 0 or tp_dist <= 0:
            raise BinanceAITraderError("ATR must be positive for SL/TP")

        exit_reason: str | None = None
        exit_price: float | None = None

        if side == "LONG":
            sl_price = entry_price - sl_dist
            tp_price = entry_price + tp_dist

            # Conservative resolution if both hit in same candle: assume SL
            if float(l[i]) <= sl_price:
                exit_reason = "SL"
                exit_price = sl_price
            elif float(h[i]) >= tp_price:
                exit_reason = "TP"
                exit_price = tp_price
        else:  # SHORT
            sl_price = entry_price + sl_dist
            tp_price = entry_price - tp_dist

            if float(h[i]) >= sl_price:
                exit_reason = "SL"
                exit_price = sl_price
            elif float(l[i]) <= tp_price:
                exit_reason = "TP"
                exit_price = tp_price

        if exit_reason is None and holding == max_holding_candles:
            exit_reason = "TIME"
            exit_price = float(c[i])

        if exit_reason is None:
            continue

        if exit_price is None:
            raise BinanceAITraderError("Internal state error: missing exit price")

        size = 1.0
        gross_pnl = (exit_price - entry_price) * size if side == "LONG" else (entry_price - exit_price) * size

        fee = float(fee_pct) * (entry_price + exit_price) * size
        slip = float(slippage_pct) * (entry_price + exit_price) * size
        net_pnl = gross_pnl - fee - slip

        trades.append(
            {
                "entry_ts": pd.Timestamp(ts[entry_i]).isoformat(),
                "exit_ts": pd.Timestamp(ts[i]).isoformat(),
                "side": side,
                "entry_price": float(entry_price),
                "exit_price": float(exit_price),
                "exit_reason": exit_reason,
                "gross_pnl": float(gross_pnl),
                "net_pnl": float(net_pnl),
                "fee": float(fee),
                "slippage": float(slip),
                "holding_candles": int(holding),
            }
        )

        # back to flat
        state = "FLAT"
        entry_i = None
        entry_price = None
        side = None

    out = pd.DataFrame(trades)
    if not out.empty:
        out["entry_ts"] = pd.to_datetime(out["entry_ts"], utc=True)
        out["exit_ts"] = pd.to_datetime(out["exit_ts"], utc=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(output_path, index=False)

    return BuildExecutions5mResult(
        ok=True,
        rows_in=int(merged.shape[0]),
        trades_out=int(out.shape[0]),
        output_path=str(output_path),
    )
