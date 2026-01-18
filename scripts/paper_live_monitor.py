"""
PAPER TRADING SYSTEM v1 - LIVE MONITOR (READ-ONLY)

⚠ CRITICAL ARCHITECTURAL BOUNDARY:
This script is READ-ONLY and performs NO side effects.
It only INSPECTS historical replay logs for behavioral safety.

This script MUST NEVER:
- Write files or modify any state
- Call training or model updates
- Trigger any learning mechanisms
- Modify model weights or parameters
- Create feedback loops

This script IS SAFE to run:
- Periodically during paper trading
- In cron jobs for monitoring
- During soak testing
- In CI pipelines for validation

This script IS NOT:
- A training signal generator
- A model improvement trigger
- A reinforcement learning component
- An online learning system

Any attempt to extend this script with training, model updates, or
any form of automated learning would violate the paper trading contract
and invalidate all paper trading results.

The system is intentionally frozen during paper trading mode.
Stability and capital preservation are prioritized over performance.
"""

import json
import hashlib
from collections import Counter

def fingerprint(txt):
    """Create deterministic fingerprint for reasoning text to detect patterns."""
    return hashlib.md5(txt.lower().strip().encode()).hexdigest()[:8]

def monitor(replay_log):
    """
    Analyze paper trading replay logs for behavioral safety invariants.
    
    This function is READ-ONLY and performs no side effects.
    It only calculates metrics to verify system behavior compliance.
    
    Args:
        replay_log: Historical paper trading decisions (read-only)
    
    Returns:
        dict: Behavioral metrics for safety validation
    """
# Defensive guard: empty or invalid replay must never crash monitor
    if not replay_log or not any(isinstance(r, dict) for r in replay_log): 
       return {
            "HOLD_PCT": 100.0,
            "BUY_PCT": 0.0,
            "SELL_PCT": 0.0,
            "BAD_CONFIDENCE_CASES": 0,
            "REPEATED_BAD_PATTERNS": 0,
            "GOOD_RATIO": 0.0,
        }

    total = len(replay_log)
    hold = sum(1 for r in replay_log if r["action"] == "HOLD")
    buy = sum(1 for r in replay_log if r["action"] == "BUY")
    sell = sum(1 for r in replay_log if r["action"] == "SELL")

    bad = [r for r in replay_log if r["label"] == "BAD"]
    good = [r for r in replay_log if r["label"] == "GOOD"]

    # Detect confidence leakage in BAD trades (forbidden in paper trading)
    certainty_words = ["strong momentum","high confidence","guaranteed","obvious"]
    bad_conf = sum(
        1 for r in bad
        if any(w in r["reasoning"].lower() for w in certainty_words)
    )

    # Detect repeated BAD reasoning patterns (indicates systematic issues)
    fps = Counter(fingerprint(r["reasoning"]) for r in bad)
    repeated = sum(1 for c in fps.values() if c >= 2)

    return {
        "HOLD_PCT": hold / total * 100,
        "BUY_PCT": buy / total * 100,
        "SELL_PCT": sell / total * 100,
        "BAD_CONFIDENCE_CASES": bad_conf,
        "REPEATED_BAD_PATTERNS": repeated,
        "GOOD_RATIO": len(good) / total
    }
