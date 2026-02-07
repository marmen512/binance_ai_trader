"""
TWO-PASS OFFLINE FINETUNING.

This module provides the same fine_tune_pass function as offline_finetuning_core.
It exists to maintain backward compatibility with the two_pass_finetuning CLI.

The two-pass logic is implemented in the CLI layer, not here.

WARNING:
- MANUAL EXECUTION ONLY
- NO PAPER / LIVE / CI USAGE
"""

from training.offline_finetuning_core import fine_tune_pass

__all__ = ["fine_tune_pass"]
