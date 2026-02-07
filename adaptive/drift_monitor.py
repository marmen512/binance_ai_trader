"""
Drift monitor wrapper for adaptive module.

Links to monitoring/drift_monitor_v2.py to keep adaptive module self-contained.
"""

from monitoring.drift_monitor_v2 import DriftMonitorV2, DriftMetrics

__all__ = ['DriftMonitorV2', 'DriftMetrics']
