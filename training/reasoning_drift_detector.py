#!/usr/bin/env python3
"""
Reasoning drift detector for identifying overconfidence and repeated BAD reasoning patterns.
"""

from __future__ import annotations

import json
import re
import sys
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

CONFIDENCE_PATTERNS = [
    r"strong momentum",
    r"high confidence",
    r"clear continuation",
    r"low risk high reward",
    r"uncertainty",
    r"no clear edge",
    r"cost",
]

EDGE_PATTERNS = [
    r"risk.*reward",
    r"asymmetric",
    r"cost.*covered",
    r"uncertainty",
    r"no clear edge",
]

def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.lower().strip()

def create_reasoning_fingerprint(reasoning: str) -> str:
    """Create deterministic fingerprint of reasoning text."""
    normalized = normalize_text(reasoning)
    # Remove numbers and extra whitespace for pattern matching
    cleaned = re.sub(r'\d+', '', normalized)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return hashlib.md5(cleaned.encode()).hexdigest()[:8]

def main(path: str):
    p = Path(path)
    if not p.exists():
        print("FILE_NOT_FOUND")
        sys.exit(1)

    bad_confident = 0
    bad_total = 0
    hold_total = 0
    buy_sell_total = 0

    phrase_counter = Counter()
    reasoning_fingerprints = defaultdict(list)
    repeated_reasoning_count = 0

    with p.open() as f:
        for line in f:
            row = json.loads(line)
            label = row.get("label", "")
            action = row.get("action", "")
            reasoning = normalize_text(row.get("reasoning", ""))
            
            if action == "HOLD":
                hold_total += 1
            
            if action in ("BUY", "SELL"):
                buy_sell_total += 1
            
            if label == "BAD":
                bad_total += 1
                
                # Create fingerprint for this reasoning
                fingerprint = create_reasoning_fingerprint(reasoning)
                reasoning_fingerprints[fingerprint].append(reasoning)
                
                # Check for confidence patterns
                for pattern in CONFIDENCE_PATTERNS:
                    if re.search(pattern, reasoning):
                        bad_confident += 1
                        phrase_counter[pattern] += 1
                
                # Check for edge patterns
                for pattern in EDGE_PATTERNS:
                    if re.search(pattern, reasoning):
                        bad_confident += 1
                        phrase_counter[pattern] += 1

    # Analyze repeated reasoning patterns
    repeated_patterns = []
    for fingerprint, reasonings in reasoning_fingerprints.items():
        if len(reasonings) >= 3:  # Same reasoning appears 3+ times
            repeated_reasoning_count += len(reasonings)
            repeated_patterns.append((fingerprint, len(reasonings), reasonings[0]))

    print("\n=== REASONING DRIFT REPORT ===")
    print("BAD trades:", bad_total)
    print("HOLD actions:", hold_total)
    print("BUY/SELL actions:", buy_sell_total)
    print("Confident BAD trades:", bad_confident)
    print("Repeated BAD reasoning patterns:", repeated_reasoning_count)
    
    print("\n=== CONFIDENCE PATTERNS ===")
    for pattern, count in phrase_counter.most_common():
        print(f"{pattern}: {count}")

    print("\n=== REPEATED BAD REASONING ===")
    for fingerprint, count, example in sorted(repeated_patterns, key=lambda x: x[1], reverse=True)[:5]:
        print(f"Pattern {fingerprint}: {count} occurrences")
        print(f"Example: {example[:100]}...")
    
    print("\n=== VERDICT ===")
    drift = False
    
    if bad_total > 0:
        ratio = bad_confident / bad_total
        print("confident_BAD_ratio:", round(ratio, 3))
        
        if ratio > 0.30:
            print("❌ DRIFT: confident language in BAD trades")
            drift = True
        else:
            print("✅ OK: no significant reasoning drift")

    if repeated_reasoning_count > bad_total * 0.2:  # More than 20% of BAD trades repeat
        print("❌ DRIFT: repeated BAD reasoning patterns detected")
        drift = True
    else:
        print("✅ OK: no repeated reasoning patterns")

    if buy_sell_total > hold_total * 1.2:
        print("❌ DRIFT: BUY/SELL dominating HOLD")
        drift = True
    else:
        print("✅ OK: appropriate HOLD usage")

    if drift:
        print("❌ DRIFT: reasoning drift detected")
    else:
        print("✅ OK: no significant reasoning drift")

    print("\n=== RECOMMENDATIONS ===")
    if bad_confident > 0:
        print("🚨 Reduce confident language in BAD trades")
        print("🚨 Add uncertainty acknowledgment")
        print("🚨 Focus on edge analysis")
    
    if repeated_reasoning_count > 0:
        print("🚨 Diversify BAD reasoning patterns")
        print("🚨 Review reasoning templates")
        print("🚨 Add more context-specific analysis")
    
    if buy_sell_total > hold_total * 1.2:
        print("🚨 Reduce action frequency")
        print("🚨 Increase HOLD criteria")
    
    if drift:
        print("🚨 Review reasoning templates")
        print("🚨 Implement edge validation")
    else:
        print("✅ Reasoning quality is appropriate")

    print("\n=== HEALTH CHECK ===")
    if bad_confident > 0.30:
        print("⚠️ WARNING: Overconfident BAD trades")
    if bad_confident < 0.10:
        print("⚠️ WARNING: Underconfident BAD trades")
    
    if buy_sell_total > hold_total * 1.5:
        print("⚠️ WARNING: Overtrading (too many BUY/SELL)")
    
    if hold_total == 0:
        print("⚠️ WARNING: No HOLD actions (potential overtrading)")

    print("OK")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: reasoning_drift_detector.py <replay.jsonl>")
        sys.exit(1)
    main(sys.argv[1])
