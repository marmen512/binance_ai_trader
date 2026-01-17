#!/usr/bin/env bash
# PAPER TRADING SYSTEM v1 - CI GATE (HARD BLOCKER)
#
# ⚠ CRITICAL: This is a CI GATE, not a metric report.
# Any failure MUST block: merge, release, promotion.
# This gate enforces paper trading behavioral invariants.
#
# ARCHITECTURAL ASSUMPTIONS:
# - Model is frozen (no online learning)
# - replay_log.json contains historical data only
# - System is in paper trading mode (read-only)
#
# BEHAVIORAL ENFORCEMENT:
# - HOLD dominance (≥55%) - capital preservation
# - Zero confidence leakage in BAD trades
# - Zero repeated BAD reasoning patterns
# - GOOD trades limited (≤20%) - prevents overconfidence
#
# This script MUST remain deterministic.
# Any modification that weakens these checks violates the paper trading contract.

set -euo pipefail

# Simple CI gate that works with both pipe and file input
if [ $# -eq 1 ]; then
    # File argument provided
    python3 -c "
import json
import sys
from scripts.paper_live_monitor import monitor

with open('$1', 'r') as f:
    raw = f.read()

if not raw:
    print('❌ CI GATE ERROR: empty file')
    sys.exit(1)

try:
    replay = json.loads(raw)
except Exception as e:
    print('❌ CI GATE ERROR: invalid JSON input')
    sys.exit(1)

m = monitor(replay)

# HARD INVARIANTS - failure blocks ALL deployment
assert m['HOLD_PCT'] >= 55, 'HOLD_PCT < 55%: violates capital preservation'
assert m['BAD_CONFIDENCE_CASES'] == 0, 'BAD_CONFIDENCE_CASES > 0: confidence leakage detected'
assert m['REPEATED_BAD_PATTERNS'] == 0, 'REPEATED_BAD_PATTERNS > 0: systematic issues'
assert m['GOOD_RATIO'] <= 0.20, 'GOOD_RATIO > 20%: overconfidence risk'

print('✅ PAPER v1 CI GATE PASSED')
# NOTE: Passing this gate does NOT improve the model.
# It only certifies behavioral safety during paper trading.
"
else
    # Pipe input
    python3 -c "
import json
import sys
from scripts.paper_live_monitor import monitor

raw = sys.stdin.read()
if not raw or not raw.strip():
    print('❌ CI GATE ERROR: empty stdin')
    sys.exit(1)

try:
    replay = json.loads(raw)
except Exception as e:
    print('❌ CI GATE ERROR: invalid JSON input')
    sys.exit(1)

m = monitor(replay)

# HARD INVARIANTS - failure blocks ALL deployment
assert m['HOLD_PCT'] >= 55, 'HOLD_PCT < 55%: violates capital preservation'
assert m['BAD_CONFIDENCE_CASES'] == 0, 'BAD_CONFIDENCE_CASES > 0: confidence leakage detected'
assert m['REPEATED_BAD_PATTERNS'] == 0, 'REPEATED_BAD_PATTERNS > 0: systematic issues'
assert m['GOOD_RATIO'] <= 0.20, 'GOOD_RATIO > 20%: overconfidence risk'

print('✅ PAPER v1 CI GATE PASSED')
# NOTE: Passing this gate does NOT improve the model.
# It only certifies behavioral safety during paper trading.
"
fi
