"""Adaptive AI Trading System - Isolated Shadow Learning Pipeline

CRITICAL ARCHITECTURAL BOUNDARIES:
==================================

This module implements a COMPLETELY ISOLATED adaptive learning system that:

✅ DOES NOT modify existing paper trading v1 pipeline
✅ DOES NOT change frozen model logic  
✅ DOES NOT touch execution_safety gates
✅ DOES NOT enable online learning in production path
✅ Implements adaptive learning as separate shadow pipeline ONLY

Architecture:
-------------

1. DUAL MODEL:
   - frozen: Production model (trades) - READ ONLY from main pipeline
   - shadow: Learning model (learns) - NEVER trades directly

2. SHADOW LEARNS ONLY FROM:
   - Paper trade logs (historical)
   - Paper feature snapshots (read-only)
   - No coupling to live execution

3. PROMOTION FLOW:
   paper_trades → feature_log → shadow_learns → quality_check → promotion_gate → new_frozen
   
4. SAFETY:
   - All learning happens offline/async
   - Model registry with versioning
   - Rollback capability
   - Zero coupling to core execution

Learning Loop:
--------------
1. Paper trade opens → snapshot features_at_entry
2. Trade closes → outcome label
3. Send to shadow trainer → learn_one()
4. Log metrics (drift, expectancy, winrate)
5. Check drift → auto pause if degraded
6. Evaluate promotion (NOT automatic)

Required Logs:
--------------
adaptive_logs/
├── features/
│   ├── features_log.jsonl          # All trade features
│   └── features_snapshot.parquet   # Periodic snapshots
├── metrics/
│   ├── shadow_metrics.json         # Shadow model metrics
│   ├── frozen_metrics.json         # Frozen baseline
│   └── drift_alerts.jsonl          # Drift detection alerts
└── decisions/
    └── promotion_decisions.jsonl   # Promotion evaluations

Module Structure:
-----------------
adaptive/
├── dual_model/       - Frozen + Shadow model management
├── shadow_learner/   - Online learning loop (shadow only)
├── drift_monitor/    - Quality control + drift detection
├── promotion_gate/   - Model promotion decisions
├── feature_store/    - Trade feature logging/replay
└── adaptive_controller.py - Main orchestrator

NO IMPORTS from this module into:
- execution/
- execution_safety/
- trading/ (except read-only log access)
- paper_gate/

This is a READ-ONLY consumer of paper trading artifacts.
"""

from __future__ import annotations

from adaptive.dual_model import DualModelManager, ModelRole, ModelMetadata
from adaptive.shadow_learner import ShadowLearner, LearningConfig, LearningUpdate
from adaptive.drift_monitor import DriftMonitor, DriftConfig, DriftMetrics
from adaptive.promotion_gate import PromotionGate, PromotionCriteria, PromotionDecision
from adaptive.feature_store import FeatureStore, TradeFeatureSnapshot
from adaptive.adaptive_controller import AdaptiveController, AdaptiveConfig

__version__ = "0.1.0-shadow-only"

__all__ = [
    "AdaptiveController",
    "AdaptiveConfig",
    "DualModelManager",
    "ModelRole",
    "ModelMetadata",
    "ShadowLearner",
    "LearningConfig",
    "LearningUpdate",
    "DriftMonitor",
    "DriftConfig",
    "DriftMetrics",
    "PromotionGate",
    "PromotionCriteria",
    "PromotionDecision",
    "FeatureStore",
    "TradeFeatureSnapshot",
]
