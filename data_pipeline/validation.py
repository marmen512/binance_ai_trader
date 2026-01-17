from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from data_pipeline.schema import OhlcvSchema


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidationReport:
    ok: bool
    issues: list[ValidationIssue]
    rows: int
    start_ts: str | None
    end_ts: str | None


def _coerce_timestamp(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    if pd.api.types.is_integer_dtype(series) or pd.api.types.is_float_dtype(series):
        s = series.dropna()
        if s.empty:
            return pd.to_datetime(series, unit="ms", errors="coerce", utc=True)
        med = float(s.median())
        unit = "ms" if med > 1e11 else "s"
        return pd.to_datetime(series, unit=unit, errors="coerce", utc=True)
    return pd.to_datetime(series, errors="coerce", utc=True)


def validate_ohlcv(df: pd.DataFrame, schema: OhlcvSchema | None = None) -> ValidationReport:
    s = schema or OhlcvSchema()
    issues: list[ValidationIssue] = []

    required = [s.timestamp, s.open, s.high, s.low, s.close, s.volume]
    missing = [c for c in required if c not in df.columns]
    if missing:
        for c in missing:
            issues.append(ValidationIssue(level="error", code="missing_column", message=f"Missing column: {c}"))
        return ValidationReport(ok=False, issues=issues, rows=len(df), start_ts=None, end_ts=None)

    out = df.copy()

    out[s.timestamp] = _coerce_timestamp(out[s.timestamp])
    if out[s.timestamp].isna().any():
        issues.append(ValidationIssue(level="error", code="timestamp_parse", message="Some timestamps could not be parsed"))

    out = out.dropna(subset=[s.timestamp])

    for c in (s.open, s.high, s.low, s.close, s.volume):
        out[c] = pd.to_numeric(out[c], errors="coerce")
        if out[c].isna().any():
            issues.append(ValidationIssue(level="error", code="numeric_parse", message=f"Non-numeric values detected in: {c}"))

    out = out.dropna(subset=[s.open, s.high, s.low, s.close, s.volume])

    if (out[s.volume] < 0).any():
        issues.append(ValidationIssue(level="error", code="volume_negative", message="Negative volume values detected"))

    if (out[s.high] < out[s.low]).any():
        issues.append(ValidationIssue(level="error", code="high_lt_low", message="Found rows where high < low"))

    if (out[[s.open, s.high, s.low, s.close]] < 0).any().any():
        issues.append(ValidationIssue(level="warn", code="price_negative", message="Negative prices detected"))

    out = out.sort_values(s.timestamp)
    if out[s.timestamp].duplicated().any():
        issues.append(ValidationIssue(level="warn", code="timestamp_duplicate", message="Duplicate timestamps detected"))

    monotonic = out[s.timestamp].is_monotonic_increasing
    if not monotonic:
        issues.append(ValidationIssue(level="error", code="timestamp_order", message="Timestamps are not monotonic increasing after sort"))

    rows = int(out.shape[0])
    start_ts = None
    end_ts = None
    if rows > 0:
        start_ts = out[s.timestamp].iloc[0].isoformat()
        end_ts = out[s.timestamp].iloc[-1].isoformat()

    ok = not any(i.level == "error" for i in issues)
    return ValidationReport(ok=ok, issues=issues, rows=rows, start_ts=start_ts, end_ts=end_ts)
