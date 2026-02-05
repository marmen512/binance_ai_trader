#!/usr/bin/env python3
"""Integration test for adaptive retraining system."""
import sys
sys.path.insert(0, '/home/runner/.local/lib/python3.12/site-packages')

print("Testing imports...")
from core.drift_detector import DriftDetector
from core.probability_gate import ProbabilityGate
from core.position_sizer import PositionSizer
print("✓ All imports successful")

print("\nTesting DriftDetector...")
detector = DriftDetector(window_size=10, winrate_threshold=0.5)
for pnl in [10, -5, 8, -3, 12]:
    detector.add_trade(pnl)
stats = detector.get_stats()
print(f"  Stats: {stats}")
print("✓ DriftDetector works")

print("\nTesting ProbabilityGate...")
gate = ProbabilityGate(min_probability=0.6)
assert gate.filter('BUY', 0.7) == 'BUY'
assert gate.filter('BUY', 0.5) == 'HOLD'
print("✓ ProbabilityGate works")

print("\nTesting PositionSizer...")
sizer = PositionSizer()
size = sizer.calculate_size(0.7, 10000)
print(f"  Position size @ 0.7 confidence: ${size:.2f}")
print("✓ PositionSizer works")

print("\n✓ All tests passed!")
