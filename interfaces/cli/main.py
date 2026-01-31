from __future__ import annotations

"""
CLI ENTRYPOINT — PAPER / COPY SAFE MODE

Training commands intentionally removed.
Offline training must be executed manually only.
"""

import argparse

from interfaces.cli.paper_trading_commands import register_paper_commands
from interfaces.cli.commands import register_base_commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="binance-ai-trader",
        description="Binance AI Trader CLI (Paper-safe mode)",
    )

    sub = parser.add_subparsers(dest="command")

    register_base_commands(sub)
    register_paper_commands(sub)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
