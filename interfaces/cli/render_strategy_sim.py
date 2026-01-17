from __future__ import annotations

import json

from strategies.sim import StrategySimResult


def render_strategy_sim_table(res: StrategySimResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"sim\trows\t{res.rows}")
    lines.append(f"metrics\ttotal_return\t{res.total_return}")
    lines.append(f"metrics\tsharpe\t{res.sharpe}")
    lines.append(f"metrics\tmax_drawdown\t{res.max_drawdown}")
    lines.append(f"metrics\ttrades\t{res.trades}")
    lines.append(f"output\tparquet\t{res.output_path}")
    lines.append(f"output\treport\t{res.report_path}")
    return "\n".join(lines)


def render_strategy_sim_json(res: StrategySimResult) -> str:
    return json.dumps(res.__dict__, ensure_ascii=False, indent=2)
