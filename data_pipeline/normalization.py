from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from data_pipeline.schema import OhlcvSchema


DEFAULT_ALIASES: Mapping[str, list[str]] = {
    "timestamp": ["timestamp", "time", "ts", "open_time", "openTime", "date", "datetime"],
    "open": ["open", "o", "open_price", "Open"],
    "high": ["high", "h", "high_price", "High"],
    "low": ["low", "l", "low_price", "Low"],
    "close": ["close", "c", "close_price", "Close"],
    "volume": ["volume", "v", "base_volume", "Volume"],
}


def normalize_columns(
    df: pd.DataFrame,
    schema: OhlcvSchema | None = None,
    aliases: Mapping[str, list[str]] = DEFAULT_ALIASES,
) -> pd.DataFrame:
    s = schema or OhlcvSchema()
    out = df.copy()

    lower_map = {c.lower(): c for c in out.columns}

    rename: dict[str, str] = {}
    for canonical in (s.timestamp, s.open, s.high, s.low, s.close, s.volume):
        candidates = aliases.get(canonical, [canonical])
        found_col: str | None = None
        for cand in candidates:
            key = cand.lower()
            if key in lower_map:
                found_col = lower_map[key]
                break
        if found_col is not None and found_col != canonical:
            rename[found_col] = canonical

    if rename:
        out = out.rename(columns=rename)

    return out
