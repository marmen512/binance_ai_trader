"""
Failure classifier module for categorizing job failures.

Classifies failures as retryable or non-retryable based on error type.
"""

import logging
from enum import Enum
from typing import Optional
import re

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of job failures."""
    
    # Retryable failures
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    DATABASE_LOCK = "database_lock"
    TEMPORARY_ERROR = "temporary_error"
    
    # Non-retryable failures
    VALIDATION_ERROR = "validation_error"
    LOGIC_ERROR = "logic_error"
    DATA_NOT_FOUND = "data_not_found"
    PERMISSION_ERROR = "permission_error"
    CONFIGURATION_ERROR = "configuration_error"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    EXCHANGE_BAN = "exchange_ban"
    BAD_REQUEST = "bad_request"
    
    # Unknown
    UNKNOWN = "unknown"


class FailureClassifier:
    """
    Classifier for determining if job failures are retryable.
    """
    
    # Pattern matching for error classification
    RETRYABLE_PATTERNS = [
        # Network errors
        (r"ConnectionError|ConnectionRefusedError|ConnectionResetError", FailureType.NETWORK_ERROR),
        (r"TimeoutError|timeout|timed out", FailureType.TIMEOUT),
        (r"HTTPError.*429|Rate limit|Too many requests", FailureType.RATE_LIMIT),
        (r"OperationalError.*locked|database is locked", FailureType.DATABASE_LOCK),
        (r"TemporaryError|ServiceUnavailable|503|502|504", FailureType.TEMPORARY_ERROR),
        (r"ConnectTimeout|ReadTimeout|RequestException", FailureType.NETWORK_ERROR),
        # Binance specific retryable errors
        (r"BinanceAPIException.*-1003", FailureType.RATE_LIMIT),  # TOO_MANY_REQUESTS
        (r"BinanceAPIException.*-1021", FailureType.TIMEOUT),  # Timestamp for this request is outside of the recvWindow
        (r"BinanceAPIException.*-1006", FailureType.TEMPORARY_ERROR),  # An unexpected response was received
        (r"BinanceAPIException.*-2015", FailureType.TEMPORARY_ERROR),  # Invalid API-key, IP, or permissions
    ]
    
    NON_RETRYABLE_PATTERNS = [
        # Validation and logic errors
        (r"ValidationError|Invalid|BadRequest|400", FailureType.VALIDATION_ERROR),
        (r"ValueError|TypeError|AttributeError|KeyError", FailureType.LOGIC_ERROR),
        (r"NotFound|404|DoesNotExist", FailureType.DATA_NOT_FOUND),
        (r"PermissionError|Forbidden|403|Unauthorized|401", FailureType.PERMISSION_ERROR),
        (r"ConfigurationError|ImproperlyConfigured", FailureType.CONFIGURATION_ERROR),
        # Binance specific non-retryable errors
        (r"BinanceAPIException.*-2010", FailureType.INSUFFICIENT_BALANCE),  # NEW_ORDER_REJECTED - Insufficient funds
        (r"BinanceAPIException.*-1013", FailureType.VALIDATION_ERROR),  # INVALID_QUANTITY
        (r"BinanceAPIException.*-1111", FailureType.VALIDATION_ERROR),  # PRECISION is over the maximum defined
        (r"BinanceAPIException.*-1102", FailureType.BAD_REQUEST),  # Mandatory parameter missing
        (r"BinanceAPIException.*-2011", FailureType.VALIDATION_ERROR),  # UNKNOWN_ORDER
        (r"BinanceAPIException.*-1015", FailureType.RATE_LIMIT),  # Too many new orders
        (r"insufficient.*balance|InsufficientFunds", FailureType.INSUFFICIENT_BALANCE),
        (r"banned|suspended|account.*locked", FailureType.EXCHANGE_BAN),
    ]
    
    def __init__(self):
        """Initialize failure classifier."""
        pass
    
    def classify_failure(self, exc_info: str) -> FailureType:
        """
        Classify a failure based on exception information.
        
        Args:
            exc_info: Exception information string from job
            
        Returns:
            FailureType enum value
        """
        if not exc_info:
            return FailureType.UNKNOWN
        
        # Check retryable patterns first
        for pattern, failure_type in self.RETRYABLE_PATTERNS:
            if re.search(pattern, exc_info, re.IGNORECASE):
                logger.info(f"Classified failure as {failure_type.value}: {pattern}")
                return failure_type
        
        # Check non-retryable patterns
        for pattern, failure_type in self.NON_RETRYABLE_PATTERNS:
            if re.search(pattern, exc_info, re.IGNORECASE):
                logger.info(f"Classified failure as {failure_type.value}: {pattern}")
                return failure_type
        
        # Default to unknown
        logger.warning(f"Could not classify failure type from: {exc_info[:200]}")
        return FailureType.UNKNOWN
    
    def is_retryable(self, failure_type: FailureType) -> bool:
        """
        Check if a failure type is retryable.
        
        Args:
            failure_type: FailureType enum value
            
        Returns:
            True if retryable, False otherwise
        """
        retryable_types = {
            FailureType.NETWORK_ERROR,
            FailureType.TIMEOUT,
            FailureType.RATE_LIMIT,
            FailureType.DATABASE_LOCK,
            FailureType.TEMPORARY_ERROR,
        }
        
        is_retryable = failure_type in retryable_types
        
        if is_retryable:
            logger.info(f"Failure type {failure_type.value} is retryable")
        else:
            logger.warning(f"Failure type {failure_type.value} is NOT retryable")
        
        return is_retryable
    
    def should_retry_failure(self, exc_info: str) -> tuple[bool, FailureType]:
        """
        Determine if a failure should be retried.
        
        Args:
            exc_info: Exception information string from job
            
        Returns:
            Tuple of (should_retry: bool, failure_type: FailureType)
        """
        failure_type = self.classify_failure(exc_info)
        should_retry = self.is_retryable(failure_type)
        
        return should_retry, failure_type
    
    def get_failure_description(self, failure_type: FailureType) -> str:
        """
        Get human-readable description of failure type.
        
        Args:
            failure_type: FailureType enum value
            
        Returns:
            Description string
        """
        descriptions = {
            FailureType.NETWORK_ERROR: "Network connection error",
            FailureType.TIMEOUT: "Operation timed out",
            FailureType.RATE_LIMIT: "Rate limit exceeded",
            FailureType.DATABASE_LOCK: "Database lock or contention",
            FailureType.TEMPORARY_ERROR: "Temporary service error",
            FailureType.VALIDATION_ERROR: "Data validation error",
            FailureType.LOGIC_ERROR: "Programming logic error",
            FailureType.DATA_NOT_FOUND: "Required data not found",
            FailureType.PERMISSION_ERROR: "Permission or authorization error",
            FailureType.CONFIGURATION_ERROR: "Configuration error",
            FailureType.UNKNOWN: "Unknown error type",
        }
        
        return descriptions.get(failure_type, "Unknown error")
    
    def add_custom_pattern(
        self, 
        pattern: str, 
        failure_type: FailureType, 
        retryable: bool
    ):
        """
        Add a custom pattern for failure classification.
        
        Args:
            pattern: Regex pattern to match
            failure_type: FailureType to assign
            retryable: Whether this failure type should be retryable
        """
        pattern_tuple = (pattern, failure_type)
        
        if retryable:
            self.RETRYABLE_PATTERNS.append(pattern_tuple)
            logger.info(f"Added custom retryable pattern: {pattern} -> {failure_type.value}")
        else:
            self.NON_RETRYABLE_PATTERNS.append(pattern_tuple)
            logger.info(f"Added custom non-retryable pattern: {pattern} -> {failure_type.value}")
