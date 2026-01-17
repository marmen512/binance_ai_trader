from __future__ import annotations

import json

from features.pipeline import BuildFeaturesResult


def render_build_features_table(res: BuildFeaturesResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"dataset\trows_in\t{res.rows_in}")
    lines.append(f"dataset\trows_out\t{res.rows_out}")
    lines.append(f"output\tpath\t{res.output_path}")
    lines.append(f"features\tcount\t{len(res.features_added)}")
    return "\n".join(lines)


def render_build_features_json(res: BuildFeaturesResult) -> str:
    return json.dumps(res.__dict__, ensure_ascii=False, indent=2)
