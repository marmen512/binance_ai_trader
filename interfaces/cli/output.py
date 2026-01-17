# interfaces/cli/output.py

from dataclasses import dataclass
from typing import Any, Optional
import json
import sys


@dataclass
class CommandResult:
    ok: bool
    message: str
    data: Optional[Any] = None


def render(result: CommandResult) -> None:
    if result.ok:
        print(f"✅ {result.message}")
    else:
        print(f"❌ {result.message}", file=sys.stderr)

    if result.data is not None:
        print(json.dumps(result.data, indent=2, default=str))
