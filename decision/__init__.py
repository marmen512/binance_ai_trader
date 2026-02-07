"""
Decision module for hybrid signal fusion.

Combines signals from multiple sources (own model, copy-trader validation,
regime model) using confidence weighting and voting.
"""

from decision.hybrid_engine import HybridDecisionEngine, SignalSource, HybridDecision

__all__ = [
    'HybridDecisionEngine',
    'SignalSource',
    'HybridDecision',
]
