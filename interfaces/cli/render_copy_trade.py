from __future__ import annotations

import json

from trading.copy_trading import CopyTradeOnceResult


def render_copy_trade_table(res: CopyTradeOnceResult) -> str:
    lines: list[str] = []
    lines.append("SECTION\tKEY\tVALUE")
    lines.append(f"result\tok\t{str(res.ok)}")
    lines.append(f"result\texecuted\t{str(res.executed)}")
    lines.append(f"market\tmid_price\t{res.mid_price}")
    lines.append(f"expert\ttarget_position\t{res.expert_target_position}")
    lines.append(f"follower\ttarget_position\t{res.follower_target_position}")
    if res.fill is not None:
        lines.append(f"fill\tdelta_units\t{res.fill.delta_units}")
        lines.append(f"fill\tprice\t{res.fill.price}")
        lines.append(f"fill\tfee\t{res.fill.fee}")
        lines.append(f"fill\tcash_after\t{res.fill.cash_after}")
        lines.append(f"fill\tposition_units_after\t{res.fill.position_units_after}")
        lines.append(f"fill\tequity_after\t{res.fill.equity_after}")
    for r in res.reasons:
        lines.append(f"reason\tblock\t{r}")
    lines.append(f"output\tstate\t{res.state_path}")
    lines.append(f"output\treport\t{res.report_path}")
    return "\n".join(lines)


def render_copy_trade_json(res: CopyTradeOnceResult) -> str:
    payload = res.__dict__.copy()
    if res.fill is not None:
        payload["fill"] = res.fill.__dict__
    return json.dumps(payload, ensure_ascii=False, indent=2)
