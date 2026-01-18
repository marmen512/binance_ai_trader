#!/usr/bin/env bash
set -euo pipefail

# Read JSONL from stdin → convert to JSON array
python3 - << 'PY'
import sys, json
from scripts.paper_live_monitor import monitor

lines = [line.strip() for line in sys.stdin if line.strip()]
try:
    replay_log = [json.loads(line) for line in lines]
except json.JSONDecodeError as e:
    print("❌ CI GATE ERROR: invalid JSONL input")
    sys.exit(1)

metrics = monitor(replay_log)

assert metrics["HOLD_PCT"] >= 55, "HOLD_PCT < 55%"
assert metrics["BAD_CONFIDENCE_CASES"] == 0, "confidence leakage"
assert metrics["REPEATED_BAD_PATTERNS"] == 0, "repeated BAD patterns"
assert metrics["GOOD_RATIO"] <= 0.20, "GOOD overuse"

print("✅ PAPER v1 CI GATE PASSED")
PY
