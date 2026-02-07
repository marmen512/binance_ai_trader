#!/usr/bin/env python3
"""
Chaos Test: Worker Storm Simulation

Simulates worker storm scenarios to test:
- Circuit breaker activation
- Retry spike detection
- System degradation handling
- Alert hook triggering

Usage:
    python scripts/chaos/worker_storm_test.py
"""

import sys
import os
import time
import logging
import random
from typing import List, Dict, Any
import redis

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.job_safety.circuit_breaker import CircuitBreaker, CircuitState, AlertHooks
from app.job_safety.retry_hardening_v2 import (
    RetrySpikeDetector,
    RetryAnomalyDetector,
    RetryWindow
)
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerStormSimulator:
    """Simulates worker storm scenarios"""
    
    def __init__(self, redis_url: str):
        """Initialize simulator"""
        self.redis_url = redis_url
        self.redis_client = redis.from_url(redis_url)
        
        # Set up alert hooks
        self.alert_hooks = AlertHooks()
        self.alerts: List[Dict[str, Any]] = []
        
        # Add custom alert hooks
        self.alert_hooks.add_log_hook(self._log_hook)
        self.alert_hooks.add_metric_hook(self._metric_hook)
        
        # Initialize components
        self.circuit_breaker = CircuitBreaker(
            self.redis_client,
            job_type="test_job",
            failure_threshold=5,
            time_window_minutes=1,
            alert_hooks=self.alert_hooks
        )
        
        self.spike_detector = RetrySpikeDetector(
            window_size_seconds=60,
            spike_threshold_multiplier=2.0
        )
        
        self.anomaly_detector = RetryAnomalyDetector(
            high_retry_rate_threshold=0.3,
            long_window_threshold_seconds=300,
            excessive_attempts_threshold=5
        )
    
    def _log_hook(self, event_type: str, message: str, context: Dict[str, Any]) -> None:
        """Custom log hook"""
        logger.info(f"ALERT HOOK [LOG]: {event_type} - {message}")
        self.alerts.append({
            "type": "log",
            "event_type": event_type,
            "message": message,
            "context": context,
            "timestamp": time.time()
        })
    
    def _metric_hook(self, event_type: str, message: str, context: Dict[str, Any]) -> None:
        """Custom metric hook"""
        logger.info(f"ALERT HOOK [METRIC]: {event_type}")
        self.alerts.append({
            "type": "metric",
            "event_type": event_type,
            "message": message,
            "context": context,
            "timestamp": time.time()
        })
    
    def simulate_normal_load(self, duration: int = 10) -> None:
        """Simulate normal load (baseline)"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Normal load ({duration}s)")
        logger.info("="*60)
        
        success_count = 0
        failure_count = 0
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # 90% success rate
            if random.random() < 0.9:
                success_count += 1
                self.circuit_breaker.record_success()
            else:
                failure_count += 1
                self.circuit_breaker.record_failure()
            
            time.sleep(0.5)
        
        logger.info(f"Normal load complete: {success_count} successes, {failure_count} failures")
        logger.info(f"Circuit state: {self.circuit_breaker.get_state()}")
    
    def simulate_failure_storm(self, duration: int = 30, failure_rate: float = 0.8) -> None:
        """Simulate failure storm"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Failure storm ({duration}s, {failure_rate*100}% failure rate)")
        logger.info("="*60)
        
        # Reset circuit breaker
        self.circuit_breaker.reset()
        
        success_count = 0
        failure_count = 0
        circuit_opened = False
        
        end_time = time.time() + duration
        
        while time.time() < end_time:
            # High failure rate
            if random.random() > failure_rate:
                success_count += 1
                self.circuit_breaker.record_success()
            else:
                failure_count += 1
                self.circuit_breaker.record_failure()
            
            # Check if circuit opened
            if not circuit_opened and self.circuit_breaker.is_open():
                logger.warning("⚠ Circuit breaker OPENED!")
                circuit_opened = True
            
            time.sleep(0.2)
        
        logger.info(f"Failure storm complete: {success_count} successes, {failure_count} failures")
        logger.info(f"Circuit state: {self.circuit_breaker.get_state()}")
        logger.info(f"Failure count: {self.circuit_breaker.get_failure_count()}")
        
        if circuit_opened:
            logger.info("✓ Circuit breaker activated as expected")
        else:
            logger.warning("✗ Circuit breaker did not activate")
    
    def simulate_retry_spike(self, spike_size: int = 50) -> None:
        """Simulate sudden retry spike"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Retry spike ({spike_size} retries)")
        logger.info("="*60)
        
        # Normal load first
        logger.info("Establishing baseline...")
        for _ in range(10):
            self.spike_detector.record_retry()
            time.sleep(0.5)
        
        baseline_rate = self.spike_detector.get_current_rate()
        logger.info(f"Baseline rate: {baseline_rate} retries/minute")
        
        # Sudden spike
        logger.info(f"\nGenerating spike of {spike_size} retries...")
        spike_alerts = []
        
        for i in range(spike_size):
            alert = self.spike_detector.record_retry()
            if alert and alert not in spike_alerts:
                logger.warning(f"⚠ SPIKE ALERT: {alert}")
                spike_alerts.append(alert)
            time.sleep(0.05)  # Fast retries
        
        current_rate = self.spike_detector.get_current_rate()
        logger.info(f"\nSpike complete:")
        logger.info(f"  Current rate: {current_rate} retries/minute")
        logger.info(f"  Baseline rate: {baseline_rate} retries/minute")
        logger.info(f"  Spike alerts triggered: {len(spike_alerts)}")
        
        if len(spike_alerts) > 0:
            logger.info("✓ Spike detector activated as expected")
        else:
            logger.warning("✗ Spike detector did not activate")
    
    def simulate_anomalous_retries(self, num_jobs: int = 20) -> None:
        """Simulate anomalous retry patterns"""
        logger.info("\n" + "="*60)
        logger.info(f"TEST: Anomalous retry patterns ({num_jobs} jobs)")
        logger.info("="*60)
        
        anomalies_detected = []
        
        for i in range(num_jobs):
            window = RetryWindow(f"job_{i}", time.time())
            
            # Create different anomaly patterns
            if i % 5 == 0:
                # Long window
                window.attempt_count = 3
                time.sleep(0.1)
                window.close(True)
            elif i % 3 == 0:
                # Excessive attempts
                window.attempt_count = 12
                window.close(False)
            else:
                # Normal
                window.attempt_count = random.randint(1, 3)
                window.close(random.random() > 0.2)
            
            anomalies = self.anomaly_detector.record_window(window)
            
            if anomalies:
                logger.warning(f"Job {i}: Anomalies detected:")
                for anomaly in anomalies:
                    logger.warning(f"  - {anomaly}")
                anomalies_detected.extend(anomalies)
        
        stats = self.anomaly_detector.get_stats()
        logger.info(f"\nAnomaly detection results:")
        logger.info(f"  Total jobs: {stats['total_jobs']}")
        logger.info(f"  Retry rate: {stats['retry_rate']:.2%}")
        logger.info(f"  Long windows: {stats['long_windows']}")
        logger.info(f"  Excessive attempts: {stats['excessive_attempts']}")
        logger.info(f"  Total anomalies: {len(anomalies_detected)}")
    
    def simulate_cascading_failures(self) -> None:
        """Simulate cascading failure scenario"""
        logger.info("\n" + "="*60)
        logger.info("TEST: Cascading failures")
        logger.info("="*60)
        
        # Reset
        self.circuit_breaker.reset()
        self.alerts = []
        
        # Phase 1: Initial failures
        logger.info("\n[Phase 1] Initial failures")
        for i in range(3):
            self.circuit_breaker.record_failure()
            time.sleep(0.5)
        
        # Phase 2: Accelerating failures
        logger.info("\n[Phase 2] Accelerating failures")
        for i in range(5):
            self.circuit_breaker.record_failure()
            self.spike_detector.record_retry()
            time.sleep(0.2)
        
        # Phase 3: Storm
        logger.info("\n[Phase 3] Failure storm")
        for i in range(10):
            self.circuit_breaker.record_failure()
            self.spike_detector.record_retry()
            time.sleep(0.1)
        
        # Check results
        logger.info("\n" + "-"*60)
        logger.info("RESULTS:")
        logger.info("-"*60)
        logger.info(f"Circuit state: {self.circuit_breaker.get_state()}")
        logger.info(f"Failure count: {self.circuit_breaker.get_failure_count()}")
        logger.info(f"Alerts triggered: {len(self.alerts)}")
        logger.info(f"Spike rate: {self.spike_detector.get_current_rate()}")
        
        if self.circuit_breaker.is_open():
            logger.info("\n✓ Circuit breaker protected system from cascading failures")
        else:
            logger.warning("\n✗ Circuit breaker did not activate")
    
    def run_all_tests(self) -> None:
        """Run all worker storm tests"""
        logger.info("\n" + "="*80)
        logger.info("WORKER STORM CHAOS TEST")
        logger.info("="*80)
        
        self.simulate_normal_load(duration=5)
        time.sleep(2)
        
        self.simulate_failure_storm(duration=10, failure_rate=0.8)
        time.sleep(2)
        
        self.simulate_retry_spike(spike_size=30)
        time.sleep(2)
        
        self.simulate_anomalous_retries(num_jobs=20)
        time.sleep(2)
        
        self.simulate_cascading_failures()
        
        logger.info("\n" + "="*80)
        logger.info("CHAOS TEST COMPLETE")
        logger.info("="*80)
        logger.info(f"\nTotal alerts triggered: {len(self.alerts)}")


def main():
    """Main entry point"""
    logger.info("Starting worker storm chaos test...")
    
    try:
        simulator = WorkerStormSimulator(settings.REDIS_URL)
        simulator.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
