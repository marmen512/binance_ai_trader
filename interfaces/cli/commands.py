"""
BASE CLI COMMANDS — TRAINING FREE

IMPORTANT:
Runtime CLI must not depend on training modules.
Offline training is executed manually only.
"""

from __future__ import annotations


def register_base_commands(subparsers):
    p = subparsers.add_parser(
        "doctor",
        help="Basic runtime environment check",
    )

    p.set_defaults(func=_doctor)


def _doctor(args):
    print("Runtime doctor OK")
    print("Training modules intentionally not loaded")
