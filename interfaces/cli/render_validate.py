from __future__ import annotations

import json

from data_pipeline.pipeline import ValidateDataResult


def render_validate_table(res: ValidateDataResult) -> str:
    lines: list[str] = []

    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"dataset\trows\t{res.report.rows}")
    lines.append(f"dataset\tstart_ts\t{res.report.start_ts or ''}")
    lines.append(f"dataset\tend_ts\t{res.report.end_ts or ''}")
    lines.append(f"merge\tdropped_duplicates\t{res.merge.dropped_duplicates}")
    lines.append(f"result\tok\t{str(res.report.ok)}")

    if res.card is not None:
        lines.append(f"registry\tdataset_id\t{res.card.dataset_id}")
        lines.append(f"registry\tsha256\t{res.card.sha256}")

    if res.report.issues:
        lines.append("issues\tlevel\tcode\tmessage")
        for i in res.report.issues:
            lines.append(f"issues\t{i.level}\t{i.code}\t{i.message}")

    return "\n".join(lines)


def render_validate_json(res: ValidateDataResult) -> str:
    payload = {
        "ok": res.report.ok,
        "rows": res.report.rows,
        "start_ts": res.report.start_ts,
        "end_ts": res.report.end_ts,
        "dropped_duplicates": res.merge.dropped_duplicates,
        "issues": [i.__dict__ for i in res.report.issues],
        "dataset_card": None if res.card is None else res.card.__dict__,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
