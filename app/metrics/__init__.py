"""
Metrics module for production safety.

Provides cardinality guards and metrics utilities.
"""

from app.metrics.guard import (
    MetricsCardinalityGuard,
    CardinalityViolation,
    get_global_guard,
    validate_metric_labels
)

__all__ = [
    "MetricsCardinalityGuard",
    "CardinalityViolation",
    "get_global_guard",
    "validate_metric_labels",
]
