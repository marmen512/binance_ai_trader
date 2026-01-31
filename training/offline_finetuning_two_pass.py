"""
Two-pass offline fine-tuning module.

This module re-exports the fine_tune_pass function from offline_finetuning_core
for use in the two-pass training workflow.
"""

from __future__ import annotations

from training.offline_finetuning_core import fine_tune_pass

__all__ = ["fine_tune_pass"]