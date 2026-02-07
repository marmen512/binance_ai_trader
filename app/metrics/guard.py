"""
Metrics Cardinality Guard

Prevents metrics explosion by validating labels against forbidden high-cardinality values.

Forbidden labels:
- job_id (unique per job)
- order_id (unique per order)
- trade_id (unique per trade)
- user_id (potentially high cardinality)
- transaction_id (unique per transaction)
- request_id (unique per request)

These labels can cause unbounded metrics growth in Prometheus/StatsD.
"""

import logging
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CardinalityViolation:
    """Represents a cardinality violation"""
    label_name: str
    label_value: Any
    metric_name: str
    reason: str
    
    def __str__(self):
        return (
            f"Cardinality violation in metric '{self.metric_name}': "
            f"forbidden label '{self.label_name}' with value '{self.label_value}' ({self.reason})"
        )


class MetricsCardinalityGuard:
    """
    Guards against high-cardinality metrics labels.
    
    Validates that metrics labels don't include forbidden high-cardinality values
    that could cause metrics explosion.
    """
    
    # Forbidden label names (exact match)
    FORBIDDEN_LABELS: Set[str] = {
        "job_id",
        "order_id",
        "trade_id",
        "user_id",
        "transaction_id",
        "request_id",
        "task_id",
        "execution_id",
        "session_id",
    }
    
    # Patterns that indicate high cardinality (substring match)
    FORBIDDEN_PATTERNS: Set[str] = {
        "_id",
        "_uuid",
        "_guid",
        "timestamp",
    }
    
    # Maximum allowed cardinality for a single label
    MAX_LABEL_CARDINALITY = 100
    
    def __init__(
        self,
        strict_mode: bool = False,
        custom_forbidden_labels: Optional[Set[str]] = None,
        custom_forbidden_patterns: Optional[Set[str]] = None
    ):
        """
        Initialize metrics cardinality guard.
        
        Args:
            strict_mode: If True, raise exceptions on violations. If False, log warnings.
            custom_forbidden_labels: Additional forbidden label names
            custom_forbidden_patterns: Additional forbidden patterns
        """
        self.strict_mode = strict_mode
        
        # Combine default and custom forbidden labels
        self.forbidden_labels = self.FORBIDDEN_LABELS.copy()
        if custom_forbidden_labels:
            self.forbidden_labels.update(custom_forbidden_labels)
        
        # Combine default and custom forbidden patterns
        self.forbidden_patterns = self.FORBIDDEN_PATTERNS.copy()
        if custom_forbidden_patterns:
            self.forbidden_patterns.update(custom_forbidden_patterns)
        
        # Track observed labels and their cardinality
        self.label_cardinality: Dict[str, Set[str]] = {}
        
        # Track violations
        self.violations: List[CardinalityViolation] = []
    
    def validate_labels(
        self,
        metric_name: str,
        labels: Dict[str, Any]
    ) -> tuple[bool, List[CardinalityViolation]]:
        """
        Validate metric labels for cardinality issues.
        
        Args:
            metric_name: Name of the metric
            labels: Dictionary of label name -> value
            
        Returns:
            Tuple of (is_valid, violations)
            - is_valid: True if no violations, False otherwise
            - violations: List of CardinalityViolation objects
        """
        violations = []
        
        for label_name, label_value in labels.items():
            # Check exact forbidden labels
            if label_name in self.forbidden_labels:
                violation = CardinalityViolation(
                    label_name=label_name,
                    label_value=label_value,
                    metric_name=metric_name,
                    reason=f"'{label_name}' is a forbidden high-cardinality label"
                )
                violations.append(violation)
                self.violations.append(violation)
                logger.warning(str(violation))
                continue
            
            # Check forbidden patterns
            for pattern in self.forbidden_patterns:
                if pattern in label_name.lower():
                    violation = CardinalityViolation(
                        label_name=label_name,
                        label_value=label_value,
                        metric_name=metric_name,
                        reason=f"Label name contains forbidden pattern '{pattern}'"
                    )
                    violations.append(violation)
                    self.violations.append(violation)
                    logger.warning(str(violation))
                    break
            
            # Track cardinality
            label_key = f"{metric_name}:{label_name}"
            if label_key not in self.label_cardinality:
                self.label_cardinality[label_key] = set()
            
            self.label_cardinality[label_key].add(str(label_value))
            
            # Check if cardinality exceeds threshold
            cardinality = len(self.label_cardinality[label_key])
            if cardinality > self.MAX_LABEL_CARDINALITY:
                violation = CardinalityViolation(
                    label_name=label_name,
                    label_value=label_value,
                    metric_name=metric_name,
                    reason=(
                        f"Label cardinality exceeds threshold: "
                        f"{cardinality} > {self.MAX_LABEL_CARDINALITY}"
                    )
                )
                violations.append(violation)
                self.violations.append(violation)
                logger.warning(str(violation))
        
        is_valid = len(violations) == 0
        
        if not is_valid and self.strict_mode:
            raise ValueError(
                f"Metric cardinality validation failed for '{metric_name}': "
                f"{len(violations)} violation(s)"
            )
        
        return is_valid, violations
    
    def validate_label_name(self, label_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate a single label name (without value).
        
        Args:
            label_name: Label name to validate
            
        Returns:
            Tuple of (is_valid, reason)
            - is_valid: True if valid, False otherwise
            - reason: Reason for rejection if invalid
        """
        # Check exact forbidden labels
        if label_name in self.forbidden_labels:
            return False, f"'{label_name}' is a forbidden high-cardinality label"
        
        # Check forbidden patterns
        for pattern in self.forbidden_patterns:
            if pattern in label_name.lower():
                return False, f"Label name contains forbidden pattern '{pattern}'"
        
        return True, None
    
    def get_cardinality_report(self) -> Dict[str, Any]:
        """
        Get cardinality report for all tracked labels.
        
        Returns:
            Dictionary with cardinality statistics
        """
        report = {
            "total_labels": len(self.label_cardinality),
            "labels": {},
            "high_cardinality_labels": [],
            "total_violations": len(self.violations)
        }
        
        for label_key, values in self.label_cardinality.items():
            cardinality = len(values)
            report["labels"][label_key] = cardinality
            
            if cardinality > self.MAX_LABEL_CARDINALITY:
                report["high_cardinality_labels"].append({
                    "label": label_key,
                    "cardinality": cardinality,
                    "threshold": self.MAX_LABEL_CARDINALITY
                })
        
        return report
    
    def get_violations(self) -> List[CardinalityViolation]:
        """Get list of all violations"""
        return self.violations.copy()
    
    def reset_tracking(self) -> None:
        """Reset cardinality tracking (for testing or periodic cleanup)"""
        self.label_cardinality.clear()
        self.violations.clear()
        logger.info("Metrics cardinality tracking reset")


# Global instance for convenience
_global_guard: Optional[MetricsCardinalityGuard] = None


def get_global_guard() -> MetricsCardinalityGuard:
    """Get global metrics cardinality guard instance"""
    global _global_guard
    if _global_guard is None:
        _global_guard = MetricsCardinalityGuard()
    return _global_guard


def validate_metric_labels(metric_name: str, labels: Dict[str, Any]) -> bool:
    """
    Validate metric labels using global guard.
    
    Args:
        metric_name: Name of the metric
        labels: Dictionary of label name -> value
        
    Returns:
        True if valid, False otherwise
    """
    guard = get_global_guard()
    is_valid, _ = guard.validate_labels(metric_name, labels)
    return is_valid
