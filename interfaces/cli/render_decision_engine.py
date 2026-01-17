from __future__ import annotations

import json

from trading.pipeline import DecisionEngineResult


def render_decision_engine_table(res: DecisionEngineResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"engine\trows\t{res.rows}")
    lines.append(f"model\tmodel_id\t{res.model_id}")
    lines.append(f"output\tparquet\t{res.output_path}")
    lines.append(f"output\treport\t{res.report_path}")
    return "\n".join(lines)


def render_decision_engine_json(res: DecisionEngineResult) -> str:
    return json.dumps(res.__dict__, ensure_ascii=False, indent=2)
