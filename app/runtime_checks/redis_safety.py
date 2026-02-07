"""
Redis Safety Runtime Validator

Validates Redis configuration for production safety:
- Persistence mode (AOF everysec or stronger)
- Eviction policy (safe for guards)
- Memory headroom
- Replica read disabled for guards
- Emit warnings + metrics if unsafe
"""

import logging
from typing import Dict, Any, Optional, List
from enum import Enum
import redis

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation severity levels"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationResult:
    """Result of a validation check"""
    
    def __init__(
        self,
        level: ValidationLevel,
        check: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.level = level
        self.check = check
        self.message = message
        self.details = details or {}
    
    def __repr__(self):
        return f"ValidationResult(level={self.level}, check={self.check}, message={self.message})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "check": self.check,
            "message": self.message,
            "details": self.details
        }


class RedisRuntimeValidator:
    """
    Validates Redis configuration at runtime for production safety.
    
    Checks:
    1. Persistence mode (AOF everysec or stronger)
    2. Eviction policy (safe for idempotency guards)
    3. Memory headroom (available memory)
    4. Replica read disabled for guards
    """
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize Redis runtime validator.
        
        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client
        self.results: List[ValidationResult] = []
    
    def validate_persistence(self) -> ValidationResult:
        """
        Validate Redis persistence configuration.
        
        Checks for:
        - AOF enabled with everysec or always
        - RDB backup as fallback
        """
        try:
            info = self.redis.info("persistence")
            
            aof_enabled = info.get("aof_enabled", 0) == 1
            aof_state = info.get("aof_state", "unknown")
            
            if aof_enabled and aof_state == "on":
                # Check AOF sync policy
                config = self.redis.config_get("appendfsync")
                appendfsync = config.get("appendfsync", "unknown")
                
                if appendfsync in ["everysec", "always"]:
                    return ValidationResult(
                        ValidationLevel.OK,
                        "persistence",
                        f"AOF enabled with {appendfsync} sync policy",
                        {"aof_enabled": True, "appendfsync": appendfsync}
                    )
                else:
                    return ValidationResult(
                        ValidationLevel.WARNING,
                        "persistence",
                        f"AOF enabled but sync policy is {appendfsync} (recommend everysec or always)",
                        {"aof_enabled": True, "appendfsync": appendfsync}
                    )
            else:
                # Check RDB as fallback
                rdb_last_save = info.get("rdb_last_save_time", 0)
                if rdb_last_save > 0:
                    return ValidationResult(
                        ValidationLevel.WARNING,
                        "persistence",
                        "AOF disabled, using RDB only (recommend enabling AOF)",
                        {"aof_enabled": False, "rdb_last_save": rdb_last_save}
                    )
                else:
                    return ValidationResult(
                        ValidationLevel.ERROR,
                        "persistence",
                        "No persistence configured! Data will be lost on restart",
                        {"aof_enabled": False, "rdb_enabled": False}
                    )
        except Exception as e:
            logger.error(f"Failed to validate persistence: {e}")
            return ValidationResult(
                ValidationLevel.ERROR,
                "persistence",
                f"Failed to check persistence configuration: {e}",
                {"error": str(e)}
            )
    
    def validate_eviction_policy(self) -> ValidationResult:
        """
        Validate Redis eviction policy.
        
        Safe policies for idempotency guards:
        - noeviction (best)
        - allkeys-lru, allkeys-lfu (acceptable with monitoring)
        
        Unsafe policies:
        - volatile-* (can evict guard keys if no TTL)
        """
        try:
            config = self.redis.config_get("maxmemory-policy")
            policy = config.get("maxmemory-policy", "noeviction")
            
            if policy == "noeviction":
                return ValidationResult(
                    ValidationLevel.OK,
                    "eviction_policy",
                    "Eviction policy is noeviction (safest for guards)",
                    {"policy": policy}
                )
            elif policy in ["allkeys-lru", "allkeys-lfu", "allkeys-random"]:
                return ValidationResult(
                    ValidationLevel.WARNING,
                    "eviction_policy",
                    f"Eviction policy is {policy} (acceptable but monitor memory closely)",
                    {"policy": policy}
                )
            elif policy.startswith("volatile-"):
                return ValidationResult(
                    ValidationLevel.WARNING,
                    "eviction_policy",
                    f"Eviction policy is {policy} (guard keys should have TTL)",
                    {"policy": policy}
                )
            else:
                return ValidationResult(
                    ValidationLevel.WARNING,
                    "eviction_policy",
                    f"Unknown eviction policy: {policy}",
                    {"policy": policy}
                )
        except Exception as e:
            logger.error(f"Failed to validate eviction policy: {e}")
            return ValidationResult(
                ValidationLevel.ERROR,
                "eviction_policy",
                f"Failed to check eviction policy: {e}",
                {"error": str(e)}
            )
    
    def validate_memory_headroom(self, min_free_mb: int = 100) -> ValidationResult:
        """
        Validate available memory headroom.
        
        Args:
            min_free_mb: Minimum free memory in MB (default: 100MB)
        """
        try:
            info = self.redis.info("memory")
            
            used_memory = info.get("used_memory", 0)
            maxmemory = info.get("maxmemory", 0)
            
            if maxmemory == 0:
                # No memory limit set
                return ValidationResult(
                    ValidationLevel.WARNING,
                    "memory_headroom",
                    "No maxmemory limit set (recommend setting a limit)",
                    {"used_memory_mb": used_memory / (1024 * 1024), "maxmemory": 0}
                )
            
            free_memory = maxmemory - used_memory
            free_memory_mb = free_memory / (1024 * 1024)
            used_pct = (used_memory / maxmemory) * 100 if maxmemory > 0 else 0
            
            if free_memory_mb >= min_free_mb:
                return ValidationResult(
                    ValidationLevel.OK,
                    "memory_headroom",
                    f"Sufficient memory headroom: {free_memory_mb:.1f}MB free ({used_pct:.1f}% used)",
                    {
                        "used_memory_mb": used_memory / (1024 * 1024),
                        "free_memory_mb": free_memory_mb,
                        "used_percent": used_pct
                    }
                )
            else:
                return ValidationResult(
                    ValidationLevel.WARNING,
                    "memory_headroom",
                    f"Low memory headroom: {free_memory_mb:.1f}MB free ({used_pct:.1f}% used)",
                    {
                        "used_memory_mb": used_memory / (1024 * 1024),
                        "free_memory_mb": free_memory_mb,
                        "used_percent": used_pct
                    }
                )
        except Exception as e:
            logger.error(f"Failed to validate memory headroom: {e}")
            return ValidationResult(
                ValidationLevel.ERROR,
                "memory_headroom",
                f"Failed to check memory headroom: {e}",
                {"error": str(e)}
            )
    
    def validate_replica_reads(self) -> ValidationResult:
        """
        Validate that replica reads are disabled for consistency.
        
        Reading from replicas can cause stale data reads for guards.
        """
        try:
            info = self.redis.info("replication")
            
            role = info.get("role", "unknown")
            
            if role == "master":
                connected_slaves = info.get("connected_slaves", 0)
                return ValidationResult(
                    ValidationLevel.OK,
                    "replica_reads",
                    f"Connected to master (read consistency guaranteed, {connected_slaves} replicas)",
                    {"role": role, "connected_slaves": connected_slaves}
                )
            elif role == "slave":
                return ValidationResult(
                    ValidationLevel.ERROR,
                    "replica_reads",
                    "Connected to replica! Guards require master connection for consistency",
                    {"role": role}
                )
            else:
                return ValidationResult(
                    ValidationLevel.WARNING,
                    "replica_reads",
                    f"Unknown replication role: {role}",
                    {"role": role}
                )
        except Exception as e:
            logger.error(f"Failed to validate replica reads: {e}")
            return ValidationResult(
                ValidationLevel.ERROR,
                "replica_reads",
                f"Failed to check replication configuration: {e}",
                {"error": str(e)}
            )
    
    def validate_all(self) -> List[ValidationResult]:
        """
        Run all validation checks.
        
        Returns:
            List of validation results
        """
        self.results = [
            self.validate_persistence(),
            self.validate_eviction_policy(),
            self.validate_memory_headroom(),
            self.validate_replica_reads()
        ]
        
        return self.results
    
    def validate_on_startup(self) -> bool:
        """
        Validate Redis configuration on startup.
        
        Logs warnings for issues and returns False if critical errors found.
        
        Returns:
            True if validation passes (no critical errors), False otherwise
        """
        logger.info("Starting Redis runtime validation...")
        
        results = self.validate_all()
        
        has_critical = False
        has_error = False
        has_warning = False
        
        for result in results:
            if result.level == ValidationLevel.CRITICAL:
                logger.critical(f"CRITICAL [{result.check}]: {result.message}")
                has_critical = True
            elif result.level == ValidationLevel.ERROR:
                logger.error(f"ERROR [{result.check}]: {result.message}")
                has_error = True
            elif result.level == ValidationLevel.WARNING:
                logger.warning(f"WARNING [{result.check}]: {result.message}")
                has_warning = True
            else:
                logger.info(f"OK [{result.check}]: {result.message}")
        
        # Summary
        if has_critical or has_error:
            logger.error(
                "Redis validation completed with errors. "
                "Review configuration before production use."
            )
            return False
        elif has_warning:
            logger.warning(
                "Redis validation completed with warnings. "
                "Review configuration for optimal safety."
            )
            return True
        else:
            logger.info("Redis validation passed. Configuration is safe for production.")
            return True
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get validation summary.
        
        Returns:
            Dictionary with validation results summary
        """
        if not self.results:
            self.validate_all()
        
        summary = {
            "total_checks": len(self.results),
            "ok": sum(1 for r in self.results if r.level == ValidationLevel.OK),
            "warning": sum(1 for r in self.results if r.level == ValidationLevel.WARNING),
            "error": sum(1 for r in self.results if r.level == ValidationLevel.ERROR),
            "critical": sum(1 for r in self.results if r.level == ValidationLevel.CRITICAL),
            "checks": [r.to_dict() for r in self.results]
        }
        
        return summary
