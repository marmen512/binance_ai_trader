from __future__ import annotations

from core.dependencies import DependencyStatus


def render_dependency_table(statuses: list[DependencyStatus]) -> str:
    lines: list[str] = []
    lines.append("NAME\tSTATUS\tDETAILS")
    for s in statuses:
        status = "OK" if s.ok else "MISSING"
        details = s.details or ""
        lines.append(f"{s.name}\t{status}\t{details}")
    return "\n".join(lines)
