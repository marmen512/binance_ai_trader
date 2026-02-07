"""Adaptive System CLI Commands

Demonstrates the adaptive learning system without modifying paper trading.
"""

from __future__ import annotations

import json
from pathlib import Path

from adaptive import AdaptiveController, AdaptiveConfig


def adaptive_status(adaptive_dir: str = "ai_data/adaptive") -> dict:
    """
    Get status of adaptive learning system.
    
    Args:
        adaptive_dir: Base directory for adaptive system
    
    Returns:
        Dictionary with adaptive system status
    """
    config = AdaptiveConfig.default(Path(adaptive_dir))
    controller = AdaptiveController(config)
    
    status = controller.get_status()
    
    print(json.dumps(status, indent=2))
    return status


def adaptive_init(
    adaptive_dir: str = "ai_data/adaptive",
    frozen_model_id: str = "m_baseline",
    frozen_artifact_path: str = "model_registry/models/frozen.pkl",
) -> dict:
    """
    Initialize adaptive system with frozen model.
    
    Args:
        adaptive_dir: Base directory for adaptive system
        frozen_model_id: Frozen model identifier
        frozen_artifact_path: Path to frozen model artifact
    
    Returns:
        Dictionary with initialization result
    """
    config = AdaptiveConfig.default(Path(adaptive_dir))
    controller = AdaptiveController(config)
    
    success, msg = controller.initialize_from_frozen_model(
        frozen_model_id=frozen_model_id,
        frozen_artifact_path=Path(frozen_artifact_path),
    )
    
    result = {
        "success": success,
        "message": msg,
        "adaptive_dir": adaptive_dir,
        "frozen_model_id": frozen_model_id,
    }
    
    print(json.dumps(result, indent=2))
    return result


def adaptive_evaluate_promotion(
    adaptive_dir: str = "ai_data/adaptive",
) -> dict:
    """
    Evaluate if shadow should be promoted to frozen.
    
    Args:
        adaptive_dir: Base directory for adaptive system
    
    Returns:
        Dictionary with promotion decision
    """
    config = AdaptiveConfig.default(Path(adaptive_dir))
    controller = AdaptiveController(config)
    
    should_promote, reason, decision = controller.evaluate_promotion()
    
    result = {
        "should_promote": should_promote,
        "reason": reason,
        "decision": decision,
    }
    
    print(json.dumps(result, indent=2))
    return result


def adaptive_promote(
    adaptive_dir: str = "ai_data/adaptive",
) -> dict:
    """
    Promote shadow model to frozen (if approved).
    
    Args:
        adaptive_dir: Base directory for adaptive system
    
    Returns:
        Dictionary with promotion result
    """
    config = AdaptiveConfig.default(Path(adaptive_dir))
    controller = AdaptiveController(config)
    
    # First evaluate
    should_promote, reason, decision = controller.evaluate_promotion()
    
    if not should_promote:
        result = {
            "success": False,
            "message": f"Promotion rejected: {reason}",
            "decision": decision,
        }
        print(json.dumps(result, indent=2))
        return result
    
    # Perform promotion
    success, msg = controller.promote_shadow_to_frozen()
    
    result = {
        "success": success,
        "message": msg,
    }
    
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m adaptive.cli <command>")
        print("Commands: status, init, evaluate, promote")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        adaptive_status()
    elif command == "init":
        adaptive_init()
    elif command == "evaluate":
        adaptive_evaluate_promotion()
    elif command == "promote":
        adaptive_promote()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
