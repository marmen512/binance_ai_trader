from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from data_pipeline.schema import OhlcvSchema
from strategies.strategy_router import StrategyRouter


@dataclass(frozen=True)
class StrategySimResult:
    ok: bool
    rows: int
    total_return: float
    sharpe: float
    max_drawdown: float
    trades: int
    output_path: str
    report_path: str


def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    running_max = equity.cummax()
    dd = equity / running_max - 1.0
    return float(dd.min())


def run_strategy_sim(
    df: pd.DataFrame,
    *,
    output_path: str | Path,
    report_path: str | Path,
    schema: OhlcvSchema | None = None,
) -> StrategySimResult:
    s = schema or OhlcvSchema()
    if s.close not in df.columns:
        return StrategySimResult(
            ok=False,
            rows=int(df.shape[0]),
            total_return=0.0,
            sharpe=0.0,
            max_drawdown=0.0,
            trades=0,
            output_path=str(output_path),
            report_path=str(report_path),
        )

    router = StrategyRouter()
    strat = router.route(df)

    close = pd.to_numeric(df[s.close], errors="coerce")
    ret = close.pct_change().fillna(0.0)

    pos = pd.to_numeric(strat.position, errors="coerce").fillna(0.0)
    pos = pos.clip(-1, 1)

    strat_ret = pos.shift(1).fillna(0.0) * ret
    equity = (1.0 + strat_ret).cumprod()

    total_return = float(equity.iloc[-1] - 1.0) if not equity.empty else 0.0

    mu = float(strat_ret.mean())
    sigma = float(strat_ret.std(ddof=0))
    sharpe = float(mu / sigma) if sigma > 0 else 0.0

    trades = int((pos != pos.shift(1)).sum())

    dd = _max_drawdown(equity)

    out = df.copy()
    out["strategy_name"] = strat.name
    out["position"] = pos
    out["strategy_return"] = strat_ret
    out["equity"] = equity

    op = Path(output_path)
    op.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(op, index=False)

    rp = Path(report_path)
    rp.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "ok": True,
        "rows": int(out.shape[0]),
        "strategy": strat.name,
        "total_return": total_return,
        "sharpe": sharpe,
        "max_drawdown": dd,
        "trades": trades,
    }
    rp.write_text(pd.Series(report).to_json(force_ascii=False, indent=2) + "\n", encoding="utf-8")

    return StrategySimResult(
        ok=True,
        rows=int(out.shape[0]),
        total_return=total_return,
        sharpe=sharpe,
        max_drawdown=dd,
        trades=trades,
        output_path=str(op),
        report_path=str(rp),
    )
