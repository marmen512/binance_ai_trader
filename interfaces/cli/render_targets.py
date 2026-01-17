from __future__ import annotations

import json

from targets.pipeline import BuildTargetsResult


def render_build_targets_table(res: BuildTargetsResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"dataset\trows_in\t{res.rows_in}")
    lines.append(f"dataset\trows_out\t{res.rows_out}")
    lines.append(f"output\tpath\t{res.output_path}")
    return "\n".join(lines)


def render_build_targets_json(res: BuildTargetsResult) -> str:
    return json.dumps(res.__dict__, ensure_ascii=False, indent=2)
