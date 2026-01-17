from __future__ import annotations

import pandas as pd


def add_copy_trader_stats(
    df: pd.DataFrame,
    *,
    trader_id_col: str = "copy_trader_id",
    pnl_col: str = "copy_trader_pnl",
) -> pd.DataFrame:
    out = df.copy()

    if trader_id_col not in out.columns or pnl_col not in out.columns:
        return out

    out["copy_trader_pnl"] = pd.to_numeric(out[pnl_col], errors="coerce")

    out["copy_trader_win"] = (out["copy_trader_pnl"] > 0).astype("float")

    g = out.groupby(trader_id_col, dropna=False)
    out["copy_trader_winrate_50"] = g["copy_trader_win"].transform(lambda s: s.rolling(50, min_periods=50).mean())
    out["copy_trader_pnl_mean_50"] = g["copy_trader_pnl"].transform(lambda s: s.rolling(50, min_periods=50).mean())
    out["copy_trader_pnl_std_50"] = g["copy_trader_pnl"].transform(lambda s: s.rolling(50, min_periods=50).std())

    return out
