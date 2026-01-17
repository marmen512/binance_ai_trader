from __future__ import annotations

import pandas as pd

from data_pipeline.schema import OhlcvSchema


def detect_regime(
    df: pd.DataFrame,
    *,
    vol_high_q: float = 0.80,
    bb_width_high_q: float = 0.80,
    liq_low_q: float = 0.10,
    trend_strength_q: float = 0.70,
    schema: OhlcvSchema | None = None,
) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    # Preconditions: these are created in PHASE 2.
    required = ["vol_20", "bb_width_20", "macd_hist", "volume_z_20"]
    missing = [c for c in required if c not in out.columns]
    if missing:
        out["market_regime"] = "UNKNOWN"
        out["low_liquidity_flag"] = False
        return out

    vol = pd.to_numeric(out["vol_20"], errors="coerce")
    bb = pd.to_numeric(out["bb_width_20"], errors="coerce")
    macd_hist = pd.to_numeric(out["macd_hist"], errors="coerce")
    volz = pd.to_numeric(out["volume_z_20"], errors="coerce")

    # If atr_pct exists (from targets), we can use it as an additional volatility proxy.
    atr_pct = None
    if "atr_pct" in out.columns:
        atr_pct = pd.to_numeric(out["atr_pct"], errors="coerce")

    vol_thr = float(vol.quantile(vol_high_q))
    bb_thr = float(bb.quantile(bb_width_high_q))
    liq_thr = float(volz.quantile(liq_low_q))
    trend_thr = float(macd_hist.abs().quantile(trend_strength_q))

    high_vol = (vol >= vol_thr) | (bb >= bb_thr)
    if atr_pct is not None:
        atr_thr = float(atr_pct.quantile(vol_high_q))
        high_vol = high_vol | (atr_pct >= atr_thr)

    low_liq = (volz <= liq_thr) & (volz < 0)
    strong_trend = macd_hist.abs() >= trend_thr

    # Variant B: low liquidity is a separate flag, not a regime label.
    # Regime focuses on price/vol dynamics; safety filters can use low_liquidity_flag.
    regime = pd.Series("RANGE", index=out.index, dtype="object")
    regime = regime.mask(strong_trend, "TREND")
    regime = regime.mask(high_vol, "HIGH_VOL")

    out["market_regime"] = regime
    out["low_liquidity_flag"] = low_liq.fillna(False)
    out["regime_thresholds"] = (
        "vol_thr="
        + str(vol_thr)
        + ",bb_thr="
        + str(bb_thr)
        + ",liq_thr="
        + str(liq_thr)
        + ",trend_thr="
        + str(trend_thr)
    )

    # Keep timestamp ordering invariant
    if s.timestamp in out.columns:
        out = out.sort_values(s.timestamp)

    return out
