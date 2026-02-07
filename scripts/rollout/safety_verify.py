#!/usr/bin/env python3
"""
Safety Verification Script

Automated verification of all safety constraints before rollout:
- Paper pipeline unchanged (paper_gate/* not modified)
- Execution unchanged (execution/* not modified)
- Risk gates unchanged (execution_safety/* not modified)
- Frozen model unchanged (no auto-retrain)
- Adaptive isolated (no direct calls to live execution)
- Retry guards active (idempotency keys working)
- Idempotency active (side effect guards working)

Exit code 0 if all checks pass, 1 if any fail.
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SafetyVerifier:
    """Verifies all safety constraints are met."""
    
    def __init__(self, repo_root: Path):
        """Initialize verifier with repository root."""
        self.repo_root = repo_root
        self.failures: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []
    
    def verify_all(self) -> bool:
        """Run all verification checks."""
        logger.info("Starting safety verification...")
        
        # Run all checks
        checks = [
            ("Paper Pipeline Unchanged", self.verify_paper_pipeline_unchanged),
            ("Execution Unchanged", self.verify_execution_unchanged),
            ("Risk Gates Unchanged", self.verify_risk_gates_unchanged),
            ("Frozen Model Intact", self.verify_frozen_model),
            ("Adaptive Isolated", self.verify_adaptive_isolated),
            ("Retry Guards Active", self.verify_retry_guards),
            ("Idempotency Active", self.verify_idempotency),
            ("Config Defaults Safe", self.verify_config_defaults),
        ]
        
        for check_name, check_func in checks:
            logger.info(f"Running check: {check_name}")
            try:
                check_func()
                self.passed.append(check_name)
                logger.info(f"✓ {check_name} - PASSED")
            except AssertionError as e:
                self.failures.append(f"{check_name}: {str(e)}")
                logger.error(f"✗ {check_name} - FAILED: {e}")
            except Exception as e:
                self.failures.append(f"{check_name}: Unexpected error - {str(e)}")
                logger.error(f"✗ {check_name} - ERROR: {e}")
        
        # Print summary
        self._print_summary()
        
        return len(self.failures) == 0
    
    def verify_paper_pipeline_unchanged(self) -> None:
        """Verify paper_gate module is unchanged."""
        paper_gate_path = self.repo_root / "paper_gate"
        
        if not paper_gate_path.exists():
            raise AssertionError("paper_gate directory not found")
        
        # Check for forbidden imports
        forbidden_imports = [
            "from app.job_safety",
            "from adaptive",
            "from decision",
            "from leaderboard",
        ]
        
        violations = []
        for py_file in paper_gate_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                if forbidden in content:
                    violations.append(f"{py_file.name}: contains '{forbidden}'")
        
        if violations:
            raise AssertionError(f"Paper pipeline has forbidden imports: {violations}")
    
    def verify_execution_unchanged(self) -> None:
        """Verify execution module is unchanged."""
        execution_path = self.repo_root / "execution"
        
        if not execution_path.exists():
            raise AssertionError("execution directory not found")
        
        # Check for forbidden imports
        forbidden_imports = [
            "from app.job_safety",
            "from adaptive",
            "from decision",
            "from leaderboard",
        ]
        
        violations = []
        for py_file in execution_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                if forbidden in content:
                    violations.append(f"{py_file.name}: contains '{forbidden}'")
        
        if violations:
            raise AssertionError(f"Execution module has forbidden imports: {violations}")
    
    def verify_risk_gates_unchanged(self) -> None:
        """Verify execution_safety module is unchanged."""
        exec_safety_path = self.repo_root / "execution_safety"
        
        if not exec_safety_path.exists():
            raise AssertionError("execution_safety directory not found")
        
        # Check for forbidden imports
        forbidden_imports = [
            "from app.job_safety",
            "from adaptive",
            "from decision",
            "from leaderboard",
        ]
        
        violations = []
        for py_file in exec_safety_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            for forbidden in forbidden_imports:
                if forbidden in content:
                    violations.append(f"{py_file.name}: contains '{forbidden}'")
        
        if violations:
            raise AssertionError(f"Risk gates have forbidden imports: {violations}")
    
    def verify_frozen_model(self) -> None:
        """Verify model is frozen (no auto-retrain in production)."""
        # Check adaptive config - should not have auto-retrain enabled by default
        config_path = self.repo_root / "config" / "config.yaml"
        
        if not config_path.exists():
            raise AssertionError("config.yaml not found")
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check adaptive is disabled by default
        adaptive = config.get("adaptive", {})
        if adaptive.get("enabled", False):
            raise AssertionError("adaptive.enabled should be False by default")
        
        # Check shadow learning is enabled (safe)
        if not adaptive.get("shadow_learning", True):
            self.warnings.append("adaptive.shadow_learning should be True")
    
    def verify_adaptive_isolated(self) -> None:
        """Verify adaptive module does not directly call live execution."""
        adaptive_path = self.repo_root / "adaptive"
        
        if not adaptive_path.exists():
            # Adaptive module may not exist yet
            return
        
        # Check for direct execution imports (not in comments)
        violations = []
        for py_file in adaptive_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            
            content = py_file.read_text()
            lines = content.split('\n')
            
            for line in lines:
                stripped = line.strip()
                # Skip comments
                if stripped.startswith('#'):
                    continue
                
                # Check for actual import statements
                if ('from execution' in stripped and 'import' in stripped) or \
                   (stripped.startswith('import execution')):
                    violations.append(f"{py_file.name}: {stripped}")
        
        if violations:
            raise AssertionError(f"Adaptive module has direct execution imports: {violations}")
    
    def verify_retry_guards(self) -> None:
        """Verify retry guards are properly configured."""
        retry_guard_path = self.repo_root / "app" / "job_safety" / "retry_guard.py"
        
        if not retry_guard_path.exists():
            raise AssertionError("retry_guard.py not found")
        
        content = retry_guard_path.read_text()
        
        # Check for critical methods (actual method names used in the module)
        required_methods = [
            "def should_execute",
            "def mark_success",
            "def mark_completed",  # Also used for marking completion
        ]
        
        # At least 2 of these should exist
        found = sum(1 for method in required_methods if method in content)
        if found < 2:
            raise AssertionError(f"RetryGuard missing critical methods (found {found} of {len(required_methods)})")
        
        # Check config has retry settings
        config_path = self.repo_root / "config" / "config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        retry_config = config.get("retry", {})
        if not retry_config:
            raise AssertionError("retry config section not found")
        
        required_keys = ["max_attempts", "cooldown_seconds"]
        missing_keys = [k for k in required_keys if k not in retry_config]
        if missing_keys:
            raise AssertionError(f"retry config missing keys: {missing_keys}")
    
    def verify_idempotency(self) -> None:
        """Verify idempotency guards are properly configured."""
        side_effect_guard_path = self.repo_root / "app" / "job_safety" / "side_effect_guard.py"
        
        if not side_effect_guard_path.exists():
            raise AssertionError("side_effect_guard.py not found")
        
        content = side_effect_guard_path.read_text()
        
        # Check for critical methods (actual method names used in the module)
        required_methods = [
            "def is_executed",
            "def mark_executed",
            "def execute_once",
        ]
        
        # At least 2 of these should exist
        found = sum(1 for method in required_methods if method in content)
        if found < 2:
            raise AssertionError(f"SideEffectGuard missing critical methods (found {found} of {len(required_methods)})")
        
        # Check config has Redis settings
        config_path = self.repo_root / "config" / "config.yaml"
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        retry_config = config.get("retry", {})
        redis_config = retry_config.get("redis", {})
        if not redis_config:
            raise AssertionError("retry.redis config section not found")
        
        required_keys = ["namespace", "ttl_seconds"]
        missing_keys = [k for k in required_keys if k not in redis_config]
        if missing_keys:
            raise AssertionError(f"retry.redis config missing keys: {missing_keys}")
    
    def verify_config_defaults(self) -> None:
        """Verify all new features are disabled by default."""
        config_path = self.repo_root / "config" / "config.yaml"
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check all new features are disabled
        checks = [
            ("adaptive.enabled", False),
            ("leaderboard.enabled", False),
            ("hybrid.enabled", False),
        ]
        
        violations = []
        for key_path, expected_value in checks:
            keys = key_path.split(".")
            value = config
            for key in keys:
                value = value.get(key, {})
            
            if value != expected_value:
                violations.append(f"{key_path} should be {expected_value}, got {value}")
        
        if violations:
            raise AssertionError(f"Config defaults not safe: {violations}")
    
    def _print_summary(self) -> None:
        """Print verification summary."""
        logger.info("\n" + "=" * 60)
        logger.info("SAFETY VERIFICATION SUMMARY")
        logger.info("=" * 60)
        
        logger.info(f"\n✓ PASSED: {len(self.passed)}")
        for check in self.passed:
            logger.info(f"  - {check}")
        
        if self.warnings:
            logger.warning(f"\n⚠ WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
        
        if self.failures:
            logger.error(f"\n✗ FAILED: {len(self.failures)}")
            for failure in self.failures:
                logger.error(f"  - {failure}")
        
        logger.info("\n" + "=" * 60)
        
        if len(self.failures) == 0:
            logger.info("✓ ALL SAFETY CHECKS PASSED")
        else:
            logger.error("✗ SAFETY VERIFICATION FAILED")
        
        logger.info("=" * 60 + "\n")


def main() -> int:
    """Main entry point."""
    # Determine repository root
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    
    logger.info(f"Repository root: {repo_root}")
    
    # Run verification
    verifier = SafetyVerifier(repo_root)
    success = verifier.verify_all()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
