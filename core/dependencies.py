from __future__ import annotations

import importlib
from dataclasses import dataclass

from core.exceptions import DependencyError


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    ok: bool
    details: str | None = None


REQUIRED_BASE: tuple[str, ...] = (
    "yaml",
)


def check_dependencies(modules: tuple[str, ...] = REQUIRED_BASE) -> list[DependencyStatus]:
    statuses: list[DependencyStatus] = []
    for name in modules:
        try:
            importlib.import_module(name)
        except Exception as e:  # noqa: BLE001
            statuses.append(DependencyStatus(name=name, ok=False, details=str(e)))
        else:
            statuses.append(DependencyStatus(name=name, ok=True, details=None))
    return statuses


def require_dependencies(modules: tuple[str, ...] = REQUIRED_BASE) -> None:
    statuses = check_dependencies(modules)
    missing = [s for s in statuses if not s.ok]
    if missing:
        msg = "Missing dependencies: " + ", ".join(f"{m.name} ({m.details})" for m in missing)
        raise DependencyError(msg)
