from __future__ import annotations

import json

from training.pipeline import TrainOfflineResult


def render_train_offline_table(res: TrainOfflineResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"data\trows_in\t{res.rows_in}")
    lines.append(f"split\trows_train\t{res.rows_train}")
    lines.append(f"split\trows_val\t{res.rows_val}")
    lines.append(f"split\trows_test\t{res.rows_test}")
    lines.append(f"model\tmodel_id\t{res.model_id}")
    for k in sorted(res.metrics.keys()):
        lines.append(f"metrics\t{k}\t{res.metrics[k]}")
    lines.append(f"output\tartifact\t{res.artifact_path}")
    lines.append(f"output\tmodel_card\t{res.model_card_path}")
    return "\n".join(lines)


def render_train_offline_json(res: TrainOfflineResult) -> str:
    return json.dumps(res.__dict__, ensure_ascii=False, indent=2)
