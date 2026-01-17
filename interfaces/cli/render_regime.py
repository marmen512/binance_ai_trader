from __future__ import annotations

import json

from market.pipeline import DetectRegimeResult


def render_detect_regime_table(res: DetectRegimeResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"dataset\trows_in\t{res.rows_in}")
    lines.append(f"dataset\trows_out\t{res.rows_out}")
    lines.append(f"output\tpath\t{res.output_path}")
    for k, v in sorted(res.counts.items()):
        lines.append(f"counts\t{k}\t{v}")
    return "\n".join(lines)


def render_detect_regime_json(res: DetectRegimeResult) -> str:
    return json.dumps(res.__dict__, ensure_ascii=False, indent=2)
