"""
PAPER TRADING CLI COMMANDS — TRAINING FREE

IMPORTANT:
Paper trading must NEVER depend on training modules.
Offline training is executed manually only.
"""

from __future__ import annotations

import argparse


def register_paper_commands(subparsers):
    p = subparsers.add_parser(
        "paper-status",
        help="Show paper trading runtime status",
    )

    p.set_defaults(func=_paper_status)


def _paper_status(args):
    print("Paper trading CLI loaded (training-free mode)")
